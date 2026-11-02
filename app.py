
import os
import math
import sqlite3
from functools import wraps
from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    session
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from database import (
    create_tables,
    create_user,
    get_user_by_email,
    get_transactions,
    get_summary,
    add_transaction,
    get_expense_by_category,
    set_budget,
    get_budgets,
    add_financial_goal,
    get_financial_goals,
    update_goal_savings,
    delete_financial_goal,
    delete_transaction
)

from ai_assistant import get_ai_response


# =====================================
# FLASK CONFIGURATION
# =====================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    "temporary-development-key-change-before-deployment"
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = (
    os.getenv("FLASK_ENV") == "production"
)

app.config["PERMANENT_SESSION_LIFETIME"] = 3600 * 24 * 7

# Create database tables
create_tables()


# =====================================
# LOGIN REQUIRED DECORATOR
# =====================================

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            flash("Please login to access your dashboard.", "error")
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


# =====================================
# SIGNUP
# =====================================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or len(username) < 3 or len(username) > 30:
            flash("Username must contain 3 to 30 characters.", "error")
            return redirect(url_for("signup"))

        if not email or len(email) > 254 or "@" not in email:
            flash("Please enter a valid email address.", "error")
            return redirect(url_for("signup"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
            return redirect(url_for("signup"))

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("signup"))

        password_hash = generate_password_hash(password)

        try:
            user_id = create_user(
                username,
                email,
                password_hash
            )

            session.clear()
            session["user_id"] = user_id
            session["username"] = username
            session.permanent = True

            flash("Account created successfully!", "success")

            return redirect(url_for("home"))

        except sqlite3.IntegrityError:
            flash("Username or email already exists.", "error")
            return redirect(url_for("signup"))

    return render_template("signup.html")


# =====================================
# LOGIN
# =====================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = get_user_by_email(email)

        if user and check_password_hash(
            user["password_hash"],
            password
        ):

            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session.permanent = True

            flash("Login successful! Welcome back.", "success")

            return redirect(url_for("home"))

        flash("Invalid email or password.", "error")
        return redirect(url_for("login"))

    return render_template("login.html")


# =====================================
# LOGOUT
# =====================================

@app.route("/logout", methods=["POST"])
@login_required
def logout():

    session.clear()

    flash("You have been logged out successfully.", "success")

    return redirect(url_for("login"))


# =====================================
# HOME / DASHBOARD
# =====================================

@app.route("/")
@login_required
def home():

    user_id = session["user_id"]

    transactions = get_transactions(user_id)
    summary = get_summary(user_id)

    current_month = datetime.now().strftime("%Y-%m")

    budgets = get_budgets(user_id, current_month)
    goals = get_financial_goals(user_id)

    return render_template(
        "index.html",
        transactions=transactions,
        summary=summary,
        budgets=budgets,
        current_month=current_month,
        goals=goals,
        username=session.get("username")
    )


# =====================================
# ADD TRANSACTION
# =====================================

@app.route("/add-transaction", methods=["POST"])
@login_required
def add_transaction_route():

    user_id = session["user_id"]

    transaction_type = request.form.get("type", "").strip()
    category = request.form.get("category", "").strip()
    amount = request.form.get("amount", "").strip()
    description = request.form.get("description", "").strip()
    date = request.form.get("date", "").strip()

    if transaction_type not in ["income", "expense"]:
        flash("Please select a valid transaction type.", "error")
        return redirect(url_for("home"))

    if not category or len(category) > 50:
        flash("Please enter a valid category.", "error")
        return redirect(url_for("home"))

    try:
        amount = float(amount)

        if not math.isfinite(amount) or amount <= 0:
            raise ValueError

        datetime.strptime(date, "%Y-%m-%d")

    except (ValueError, TypeError):
        flash("Please enter a valid amount and date.", "error")
        return redirect(url_for("home"))

    add_transaction(
        user_id,
        transaction_type,
        category,
        amount,
        description,
        date
    )

    flash("Transaction added successfully!", "success")

    return redirect(url_for("home"))


# =====================================
# DELETE TRANSACTION
# =====================================

@app.route("/delete-transaction", methods=["POST"])
@login_required
def delete_transaction_route():

    user_id = session["user_id"]

    try:
        transaction_id = int(
            request.form.get("transaction_id", "")
        )

        if transaction_id <= 0:
            raise ValueError

    except (ValueError, TypeError):
        flash("Invalid transaction.", "error")
        return redirect(url_for("home"))

    delete_transaction(user_id, transaction_id)

    flash("Transaction deleted successfully!", "success")

    return redirect(url_for("home"))


# =====================================
# EXPENSE ANALYTICS API
# =====================================

@app.route("/api/expense-summary")
@login_required
def expense_summary():

    user_id = session["user_id"]

    expenses = get_expense_by_category(user_id)

    result = []

    for expense in expenses:
        result.append({
            "category": expense["category"],
            "total": expense["total"]
        })

    return jsonify(result)


# =====================================
# ADD MONTHLY BUDGET
# =====================================

@app.route("/add-budget", methods=["POST"])
@login_required
def add_budget_route():

    user_id = session["user_id"]

    category = request.form.get("category", "").strip()
    monthly_limit = request.form.get("monthly_limit", "").strip()

    if not category or len(category) > 50:
        flash("Please enter a valid budget category.", "error")
        return redirect(url_for("home"))

    try:
        monthly_limit = float(monthly_limit)

        if not math.isfinite(monthly_limit) or monthly_limit <= 0:
            raise ValueError

    except (ValueError, TypeError):
        flash("Please enter a valid budget amount.", "error")
        return redirect(url_for("home"))

    current_month = datetime.now().strftime("%Y-%m")

    set_budget(
        user_id,
        category,
        monthly_limit,
        current_month
    )

    flash("Monthly budget saved successfully!", "success")

    return redirect(url_for("home"))


# =====================================
# AI CHAT ASSISTANT
# =====================================

@app.route("/ai-chat", methods=["POST"])
@login_required
def ai_chat():

    user_id = session["user_id"]

    data = request.get_json(silent=True) or {}

    user_message = data.get("message", "")

    if not isinstance(user_message, str):
        return jsonify({"reply": "Invalid message."}), 400

    user_message = user_message.strip()

    if not user_message:
        return jsonify({"reply": "Please enter a question."}), 400

    if len(user_message) > 1000:
        return jsonify({
            "reply": "Please keep your question within 1000 characters."
        }), 400

    summary = get_summary(user_id)

    current_month = datetime.now().strftime("%Y-%m")

    budgets = get_budgets(user_id, current_month)
    expenses = get_expense_by_category(user_id)

    financial_context = f"""
    Current Month: {current_month}

    Total Income: Rs. {summary['total_income']}
    Total Expenses: Rs. {summary['total_expenses']}
    Available Balance: Rs. {summary['balance']}

    Expense Categories:
    """

    for expense in expenses:
        financial_context += (
            f"\n{expense['category']}: Rs. {expense['total']}"
        )

    financial_context += "\n\nMonthly Budgets:\n"

    for budget in budgets:
        financial_context += (
            f"\nCategory: {budget['category']}"
            f"\nBudget Limit: Rs. {budget['monthly_limit']}"
            f"\nSpent: Rs. {budget['spent']}"
            f"\nRemaining: Rs. {budget['remaining']}\n"
        )

    answer = get_ai_response(
        user_message,
        financial_context
    )

    return jsonify({"reply": answer})


# =====================================
# SMART SPENDING INSIGHTS
# =====================================

@app.route("/api/smart-insights")
@login_required
def smart_insights():

    user_id = session["user_id"]

    summary = get_summary(user_id)

    current_month = datetime.now().strftime("%Y-%m")

    budgets = get_budgets(user_id, current_month)
    expenses = get_expense_by_category(user_id)

    financial_context = f"""
    Current Month: {current_month}

    Total Income: Rs. {summary['total_income']}
    Total Expenses: Rs. {summary['total_expenses']}
    Available Balance: Rs. {summary['balance']}

    Expense Categories:
    """

    if expenses:
        for expense in expenses:
            financial_context += (
                f"\n{expense['category']}: Rs. {expense['total']}"
            )
    else:
        financial_context += "\nNo expense records available."

    financial_context += "\n\nMonthly Budgets:\n"

    if budgets:
        for budget in budgets:
            financial_context += (
                f"\nCategory: {budget['category']}"
                f"\nBudget Limit: Rs. {budget['monthly_limit']}"
                f"\nSpent: Rs. {budget['spent']}"
                f"\nRemaining: Rs. {budget['remaining']}"
                f"\nUsed: {budget['percentage']}%\n"
            )
    else:
        financial_context += "\nNo monthly budgets have been set."

    prompt = """
    Analyse the user's financial information.

    Give 4 short and useful spending insights.
    Focus on high spending categories, budget warnings,
    available balance, and practical saving suggestions.

    Use only the supplied financial information.
    Do not invent numbers or assume missing information.
    Use simple English and bullet points.
    """

    answer = get_ai_response(prompt, financial_context)

    return jsonify({"insights": answer})


# =====================================
# ADD FINANCIAL GOAL
# =====================================

@app.route("/add-goal", methods=["POST"])
@login_required
def add_goal():

    user_id = session["user_id"]

    goal_name = request.form.get("goal_name", "").strip()
    target_amount = request.form.get("target_amount", "").strip()
    target_date = request.form.get("target_date", "").strip()

    if not goal_name or len(goal_name) > 80:
        flash("Please enter a valid goal name.", "error")
        return redirect(url_for("home"))

    try:
        target_amount = float(target_amount)

        if not math.isfinite(target_amount) or target_amount <= 0:
            raise ValueError

        datetime.strptime(target_date, "%Y-%m-%d")

    except (ValueError, TypeError):
        flash("Please enter a valid target amount and date.", "error")
        return redirect(url_for("home"))

    add_financial_goal(
        user_id,
        goal_name,
        target_amount,
        target_date
    )

    flash("Financial goal added successfully!", "success")

    return redirect(url_for("home"))


# =====================================
# UPDATE GOAL SAVINGS
# =====================================

@app.route("/update-goal-savings", methods=["POST"])
@login_required
def update_goal_savings_route():

    user_id = session["user_id"]

    goal_id = request.form.get("goal_id", "").strip()
    saved_amount = request.form.get("saved_amount", "").strip()

    try:
        goal_id = int(goal_id)
        saved_amount = float(saved_amount)

        if (
            goal_id <= 0
            or not math.isfinite(saved_amount)
            or saved_amount < 0
        ):
            raise ValueError

    except (ValueError, TypeError):
        flash("Please enter a valid saved amount.", "error")
        return redirect(url_for("home"))

    goals = get_financial_goals(user_id)

    goal_exists = any(
        goal["id"] == goal_id for goal in goals
    )

    if not goal_exists:
        flash("Financial goal not found.", "error")
        return redirect(url_for("home"))

    update_goal_savings(
        user_id,
        goal_id,
        saved_amount
    )

    flash("Savings updated successfully!", "success")

    return redirect(url_for("home"))


# =====================================
# DELETE FINANCIAL GOAL
# =====================================

@app.route("/delete-goal", methods=["POST"])
@login_required
def delete_goal():

    user_id = session["user_id"]

    goal_id = request.form.get("goal_id", "").strip()

    try:
        goal_id = int(goal_id)

        if goal_id <= 0:
            raise ValueError

    except (ValueError, TypeError):
        flash("Invalid financial goal.", "error")
        return redirect(url_for("home"))

    goals = get_financial_goals(user_id)

    goal_exists = any(
        goal["id"] == goal_id for goal in goals
    )

    if not goal_exists:
        flash("Financial goal not found.", "error")
        return redirect(url_for("home"))

    delete_financial_goal(user_id, goal_id)

    flash("Financial goal deleted successfully!", "success")

    return redirect(url_for("home"))


# =====================================
# RUN APPLICATION
# =====================================

if __name__ == "__main__":
    app.run(debug=True)
