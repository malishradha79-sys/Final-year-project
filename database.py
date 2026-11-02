
import sqlite3
from pathlib import Path

# Database configuration
BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "finance.db"


# Database connection
def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# Create database tables
def create_tables():
    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            category TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount > 0),
            description TEXT,
            date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            monthly_limit REAL NOT NULL CHECK(monthly_limit > 0),
            month TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(category, month)
        )
    """)

    # Financial Goals Table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS financial_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_name TEXT NOT NULL,
            target_amount REAL NOT NULL CHECK(target_amount > 0),
            saved_amount REAL DEFAULT 0 CHECK(saved_amount >= 0),
            target_date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()


# Add transaction
def add_transaction(transaction_type, category, amount, description, date):
    connection = get_db_connection()

    connection.execute("""
        INSERT INTO transactions
        (user_id, type, category, amount, description, date)
        VALUES (NULL, ?, ?, ?, ?, ?)
    """, (transaction_type, category, amount, description, date))

    connection.commit()
    connection.close()


# Get all transactions
def get_transactions():
    connection = get_db_connection()

    transactions = connection.execute("""
        SELECT *
        FROM transactions
        WHERE user_id IS NULL
        ORDER BY date DESC, id DESC
    """).fetchall()

    connection.close()
    return transactions


# Get financial summary
def get_summary():
    connection = get_db_connection()

    summary = connection.execute("""
        SELECT
            COALESCE(SUM(
                CASE WHEN type = 'income' THEN amount ELSE 0 END
            ), 0) AS total_income,

            COALESCE(SUM(
                CASE WHEN type = 'expense' THEN amount ELSE 0 END
            ), 0) AS total_expenses

        FROM transactions
        WHERE user_id IS NULL
    """).fetchone()

    connection.close()

    total_income = summary["total_income"]
    total_expenses = summary["total_expenses"]

    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "balance": total_income - total_expenses
    }


# Delete transaction
def delete_transaction(transaction_id):
    connection = get_db_connection()

    connection.execute("""
        DELETE FROM transactions
        WHERE id = ? AND user_id IS NULL
    """, (transaction_id,))

    connection.commit()
    connection.close()


# Get expenses by category
def get_expense_by_category():
    connection = get_db_connection()

    expenses = connection.execute("""
        SELECT
            category,
            SUM(amount) AS total
        FROM transactions
        WHERE type = 'expense'
        AND user_id IS NULL
        GROUP BY category
        ORDER BY total DESC
    """).fetchall()

    connection.close()
    return expenses


# Add or update monthly budget
def set_budget(category, monthly_limit, month):
    connection = get_db_connection()

    connection.execute("""
        INSERT INTO budgets (category, monthly_limit, month)
        VALUES (?, ?, ?)
        ON CONFLICT(category, month)
        DO UPDATE SET monthly_limit = excluded.monthly_limit
    """, (category, monthly_limit, month))

    connection.commit()
    connection.close()


# Get monthly budgets with spending information
def get_budgets(month):
    connection = get_db_connection()

    budgets = connection.execute("""
        SELECT
            b.id,
            b.category,
            b.monthly_limit,
            b.month,
            COALESCE(SUM(t.amount), 0) AS spent

        FROM budgets b

        LEFT JOIN transactions t
            ON b.category = t.category
            AND t.type = 'expense'
            AND t.user_id IS NULL
            AND substr(t.date, 1, 7) = b.month

        WHERE b.month = ?

        GROUP BY b.id
        ORDER BY b.category
    """, (month,)).fetchall()

    connection.close()

    budget_list = []

    for budget in budgets:
        monthly_limit = budget["monthly_limit"]
        spent = budget["spent"]

        remaining = monthly_limit - spent
        percentage = (spent / monthly_limit) * 100

        budget_list.append({
            "id": budget["id"],
            "category": budget["category"],
            "monthly_limit": monthly_limit,
            "spent": spent,
            "remaining": remaining,
            "percentage": percentage,
            "progress_width": min(percentage, 100),
            "month": budget["month"]
        })

    return budget_list


# Add a new financial goal
def add_financial_goal(goal_name, target_amount, target_date):
    connection = get_db_connection()

    connection.execute("""
        INSERT INTO financial_goals
        (goal_name, target_amount, saved_amount, target_date)
        VALUES (?, ?, 0, ?)
    """, (goal_name, target_amount, target_date))

    connection.commit()
    connection.close()


# Get all financial goals with progress
def get_financial_goals():
    connection = get_db_connection()

    goals = connection.execute("""
        SELECT *
        FROM financial_goals
        ORDER BY target_date ASC, id DESC
    """).fetchall()

    connection.close()

    goal_list = []

    for goal in goals:
        target_amount = goal["target_amount"]
        saved_amount = goal["saved_amount"]

        percentage = (saved_amount / target_amount) * 100
        remaining = max(target_amount - saved_amount, 0)

        goal_list.append({
            "id": goal["id"],
            "goal_name": goal["goal_name"],
            "target_amount": target_amount,
            "saved_amount": saved_amount,
            "target_date": goal["target_date"],
            "remaining": remaining,
            "percentage": percentage,
            "progress_width": min(percentage, 100),
            "is_completed": saved_amount >= target_amount
        })

    return goal_list


# Update saved amount for a financial goal
def update_goal_savings(goal_id, new_saved_amount):
    connection = get_db_connection()

    connection.execute("""
        UPDATE financial_goals
        SET saved_amount = ?
        WHERE id = ?
    """, (new_saved_amount, goal_id))

    connection.commit()
    connection.close()


# Delete a financial goal
def delete_financial_goal(goal_id):
    connection = get_db_connection()

    connection.execute("""
        DELETE FROM financial_goals
        WHERE id = ?
    """, (goal_id,))

    connection.commit()
    connection.close()
