
import sqlite3
from pathlib import Path


# =====================================
# DATABASE CONFIGURATION
# =====================================

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "finance.db"


# =====================================
# DATABASE CONNECTION
# =====================================

def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# =====================================
# CREATE TABLES AND MIGRATE DATABASE
# =====================================

def create_tables():
    connection = get_db_connection()

    # Users table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Transactions table
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

    # Budgets table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category TEXT NOT NULL,
            monthly_limit REAL NOT NULL CHECK(monthly_limit > 0),
            month TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(category, month, user_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # Financial goals table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS financial_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_name TEXT NOT NULL,
            target_amount REAL NOT NULL CHECK(target_amount > 0),
            saved_amount REAL DEFAULT 0 CHECK(saved_amount >= 0),
            target_date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # ---------------------------------
    # MIGRATE EXISTING TRANSACTIONS
    # ---------------------------------

    transaction_columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(transactions)"
        ).fetchall()
    }

    if "user_id" not in transaction_columns:
        connection.execute("""
            ALTER TABLE transactions
            ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
        """)

    # ---------------------------------
    # MIGRATE EXISTING BUDGETS
    # ---------------------------------

    budget_columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(budgets)"
        ).fetchall()
    }

    if "user_id" not in budget_columns:

        connection.execute("""
            CREATE TABLE budgets_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                category TEXT NOT NULL,
                monthly_limit REAL NOT NULL CHECK(monthly_limit > 0),
                month TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, month, user_id),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        connection.execute("""
            INSERT INTO budgets_new
                (id, category, monthly_limit, month, created_at)
            SELECT id, category, monthly_limit, month, created_at
            FROM budgets
        """)

        connection.execute("DROP TABLE budgets")

        connection.execute("""
            ALTER TABLE budgets_new RENAME TO budgets
        """)

    # ---------------------------------
    # MIGRATE EXISTING FINANCIAL GOALS
    # ---------------------------------

    goal_columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(financial_goals)"
        ).fetchall()
    }

    if "user_id" not in goal_columns:
        connection.execute("""
            ALTER TABLE financial_goals
            ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
        """)

    # ---------------------------------
    # DATABASE INDEXES
    # ---------------------------------

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_transactions_user
        ON transactions(user_id)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_budgets_user
        ON budgets(user_id)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_goals_user
        ON financial_goals(user_id)
    """)

    connection.commit()
    connection.close()


# =====================================
# USER ACCOUNT FUNCTIONS
# =====================================

def create_user(username, email, password_hash):
    connection = get_db_connection()

    try:
        cursor = connection.execute("""
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
        """, (username, email, password_hash))

        user_id = cursor.lastrowid

        # Transfer old demo data to the first registered user
        user_count = connection.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

        if user_count == 1:

            connection.execute("""
                UPDATE transactions
                SET user_id = ?
                WHERE user_id IS NULL
            """, (user_id,))

            connection.execute("""
                UPDATE budgets
                SET user_id = ?
                WHERE user_id IS NULL
            """, (user_id,))

            connection.execute("""
                UPDATE financial_goals
                SET user_id = ?
                WHERE user_id IS NULL
            """, (user_id,))

        connection.commit()
        return user_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_user_by_email(email):
    connection = get_db_connection()

    user = connection.execute("""
        SELECT *
        FROM users
        WHERE email = ?
    """, (email,)).fetchone()

    connection.close()
    return user


def get_user_by_id(user_id):
    connection = get_db_connection()

    user = connection.execute("""
        SELECT id, username, email
        FROM users
        WHERE id = ?
    """, (user_id,)).fetchone()

    connection.close()
    return user


# =====================================
# TRANSACTION FUNCTIONS
# =====================================

def add_transaction(user_id, transaction_type, category,
                    amount, description, date):

    connection = get_db_connection()

    connection.execute("""
        INSERT INTO transactions
            (user_id, type, category, amount, description, date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        transaction_type,
        category,
        amount,
        description,
        date
    ))

    connection.commit()
    connection.close()


def get_transactions(user_id):
    connection = get_db_connection()

    transactions = connection.execute("""
        SELECT *
        FROM transactions
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
    """, (user_id,)).fetchall()

    connection.close()
    return transactions


def get_summary(user_id):
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
        WHERE user_id = ?
    """, (user_id,)).fetchone()

    connection.close()

    total_income = summary["total_income"]
    total_expenses = summary["total_expenses"]

    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "balance": total_income - total_expenses
    }


def delete_transaction(user_id, transaction_id):
    connection = get_db_connection()

    connection.execute("""
        DELETE FROM transactions
        WHERE id = ? AND user_id = ?
    """, (transaction_id, user_id))

    connection.commit()
    connection.close()


def get_expense_by_category(user_id):
    connection = get_db_connection()

    expenses = connection.execute("""
        SELECT
            category,
            SUM(amount) AS total
        FROM transactions
        WHERE type = 'expense'
        AND user_id = ?
        GROUP BY category
        ORDER BY total DESC
    """, (user_id,)).fetchall()

    connection.close()
    return expenses


# =====================================
# MONTHLY BUDGET FUNCTIONS
# =====================================

def set_budget(user_id, category, monthly_limit, month):
    connection = get_db_connection()

    connection.execute("""
        INSERT INTO budgets
            (user_id, category, monthly_limit, month)
        VALUES (?, ?, ?, ?)

        ON CONFLICT(category, month, user_id)
        DO UPDATE SET monthly_limit = excluded.monthly_limit
    """, (user_id, category, monthly_limit, month))

    connection.commit()
    connection.close()


def get_budgets(user_id, month):
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
            AND t.user_id = b.user_id
            AND substr(t.date, 1, 7) = b.month

        WHERE b.user_id = ?
        AND b.month = ?

        GROUP BY b.id
        ORDER BY b.category
    """, (user_id, month)).fetchall()

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


# =====================================
# FINANCIAL GOALS FUNCTIONS
# =====================================

def add_financial_goal(user_id, goal_name,
                       target_amount, target_date):

    connection = get_db_connection()

    connection.execute("""
        INSERT INTO financial_goals
            (user_id, goal_name, target_amount,
             saved_amount, target_date)
        VALUES (?, ?, ?, 0, ?)
    """, (
        user_id,
        goal_name,
        target_amount,
        target_date
    ))

    connection.commit()
    connection.close()


def get_financial_goals(user_id):
    connection = get_db_connection()

    goals = connection.execute("""
        SELECT *
        FROM financial_goals
        WHERE user_id = ?
        ORDER BY target_date ASC, id DESC
    """, (user_id,)).fetchall()

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


def update_goal_savings(user_id, goal_id, new_saved_amount):
    connection = get_db_connection()

    connection.execute("""
        UPDATE financial_goals
        SET saved_amount = ?
        WHERE id = ? AND user_id = ?
    """, (new_saved_amount, goal_id, user_id))

    connection.commit()
    connection.close()


def delete_financial_goal(user_id, goal_id):
    connection = get_db_connection()

    connection.execute("""
        DELETE FROM financial_goals
        WHERE id = ? AND user_id = ?
    """, (goal_id, user_id))

    connection.commit()
    connection.close()
