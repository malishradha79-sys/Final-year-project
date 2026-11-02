
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
import math

from database import (
    create_tables,
    get_transactions,
    get_summary,
    add_transaction,
    get_expense_by_category,
    set_budget,
    get_budgets,
    add_financial_goal,
    get_financial_goals,
    update_goal_savings,
    delete_financial_goal
)

from ai_assistant import get_ai_response


app = Flask(__name__)
app.secret_key = "fintrack-development-key"

# Create database tables
create_tables()


# -----------------------------------
# HOME / DASHBOARD
# -----------------------------------

@app.route("/")
def home():
    transactions = get_transactions()
    summary = get_summary()

    current_month = datetime.now().strftime("%Y-%m")

    budgets = get_budgets(current_month)
    goals = get_financial_goals()

    return render_template(
        "index.html",
        transactions=transactions,
        summary=summary,
        budgets=budgets,
        current_month=current_month,
        goals=goals
    )


# -----------------------------------
# ADD TRANSACTION
# -----------------------------------

@app.route("/add-transaction", methods=["POST"])
def add_transaction_route():
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
        transaction_type,
        category,
        amount,
        description,
        date
    )

    flash("Transaction added successfully!", "success")
    return redirect(url_for("home"))


# -----------------------------------
# EXPENSE ANALYTICS API
# -----------------------------------

@app.route("/api/expense-summary")
def expense_summary():
    expenses = get_expense_by_category()

    result = []

    for expense in expenses:
        result.append({
            "category": expense["category"],
            "total": expense["total"]
        })

    return jsonify(result)


# -----------------------------------
# ADD MONTHLY BUDGET
# -----------------------------------

@app.route("/add-budget", methods=["POST"])
def add_budget_route():
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

    set_budget(category, monthly_limit, current_month)

    flash("Monthly budget saved successfully!", "success")
    return redirect(url_for("home"))


# -----------------------------------
# AI CHAT ASSISTANT
# -----------------------------------

@app.route("/ai-chat", methods=["POST"])
def ai_chat():
    data = request.get_json(silent=True) or {}

    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({
            "reply": "Please enter a question."
        }), 400

    if len(user_message) > 1000:
        return jsonify({
            "reply": "Please keep your question within 1000 characters."
        }), 400

    summary = get_summary()

    current_month = datetime.now().strftime("%Y-%m")

    budgets = get_budgets(current_month)
    expenses = get_expense_by_category()

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

    answer = get_ai_response(user_message, financial_context)

    return jsonify({"reply": answer})


# -----------------------------------
# SMART SPENDING INSIGHTS
# -----------------------------------

@app.route("/api/smart-insights", methods=["GET"])
def smart_insights():
    summary = get_summary()

    current_month = datetime.now().strftime("%Y-%m")

    budgets = get_budgets(current_month)
    expenses = get_expense_by_category()

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


# -----------------------------------
# ADD FINANCIAL GOAL
# -----------------------------------

@app.route("/add-goal", methods=["POST"])
def add_goal():
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
        goal_name,
        target_amount,
        target_date
    )

    flash("Financial goal added successfully!", "success")

    return redirect(url_for("home"))


# -----------------------------------
# UPDATE GOAL SAVINGS
# -----------------------------------

@app.route("/update-goal-savings", methods=["POST"])
def update_goal_savings_route():
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

    goals = get_financial_goals()

    goal_exists = any(
        goal["id"] == goal_id for goal in goals
    )

    if not goal_exists:
        flash("Financial goal not found.", "error")
        return redirect(url_for("home"))

    update_goal_savings(goal_id, saved_amount)

    flash("Savings updated successfully!", "success")

    return redirect(url_for("home"))


# -----------------------------------
# DELETE FINANCIAL GOAL
# -----------------------------------

@app.route("/delete-goal", methods=["POST"])
def delete_goal():
    goal_id = request.form.get("goal_id", "").strip()

    try:
        goal_id = int(goal_id)

        if goal_id <= 0:
            raise ValueError

    except (ValueError, TypeError):
        flash("Invalid financial goal.", "error")
        return redirect(url_for("home"))

    goals = get_financial_goals()

    goal_exists = any(
        goal["id"] == goal_id for goal in goals
    )

    if not goal_exists:
        flash("Financial goal not found.", "error")
        return redirect(url_for("home"))

    delete_financial_goal(goal_id)

    flash("Financial goal deleted successfully!", "success")

    return redirect(url_for("home"))


# -----------------------------------
# RUN APPLICATION
# -----------------------------------

if __name__ == "__main__":
    app.run(debug=True)
