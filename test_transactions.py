
from database import (
    add_transaction,
    get_transactions,
    get_summary
)

# Add sample income
add_transaction(
    "income",
    "Salary",
    30000,
    "Monthly salary",
    "2026-11-02"
)

# Add sample expense
add_transaction(
    "expense",
    "Food",
    1500,
    "Monthly food expenses",
    "2026-11-02"
)

# Display transactions
print("\nTRANSACTION HISTORY")

transactions = get_transactions()

for transaction in transactions:
    print(
        transaction["category"],
        transaction["type"],
        transaction["amount"]
    )

# Display financial summary
print("\nFINANCIAL SUMMARY")

summary = get_summary()

print("Total Income:", summary["total_income"])
print("Total Expenses:", summary["total_expenses"])
print("Available Balance:", summary["balance"])
