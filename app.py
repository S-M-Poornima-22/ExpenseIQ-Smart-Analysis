
from flask import Flask, render_template, request, redirect, Response
import sqlite3
import csv
import io
from datetime import datetime

app = Flask(__name__)


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():

    connection = sqlite3.connect("expense_tracker.db")

    connection.row_factory = sqlite3.Row

    return connection


# =========================================================
# CREATE DATABASE TABLE
# =========================================================

def create_table():

    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS expenses (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            date TEXT NOT NULL,

            category TEXT NOT NULL,

            description TEXT NOT NULL,

            amount REAL NOT NULL,

            payment TEXT NOT NULL

        )
    """)

    connection.commit()

    connection.close()


# =========================================================
# UPDATE CSV FILE AUTOMATICALLY
# =========================================================

def update_csv_file():

    connection = get_db_connection()

    expenses = connection.execute("""
        SELECT
            date,
            category,
            description,
            amount,
            payment

        FROM expenses

        ORDER BY date DESC
    """).fetchall()

    connection.close()

    with open(
        "expenses.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        # CSV Header
        writer.writerow([
            "Date",
            "Category",
            "Description",
            "Amount",
            "Payment"
        ])

        # CSV Data
        for expense in expenses:

            writer.writerow([
                expense["date"],
                expense["category"],
                expense["description"],
                expense["amount"],
                expense["payment"]
            ])


# =========================================================
# HOME / DASHBOARD
# =========================================================

@app.route("/")
def home():

    connection = get_db_connection()

    # -----------------------------------------------------
    # GET SEARCH AND FILTER VALUES
    # -----------------------------------------------------

    search = request.args.get("search", "")

    category = request.args.get("category", "")

    payment = request.args.get("payment", "")


    # -----------------------------------------------------
    # BASE QUERY
    # -----------------------------------------------------

    query = """
        SELECT *
        FROM expenses
        WHERE 1=1
    """

    parameters = []


    # -----------------------------------------------------
    # SEARCH
    # -----------------------------------------------------

    if search:

        query += """
            AND (
                description LIKE ?
                OR category LIKE ?
            )
        """

        search_value = f"%{search}%"

        parameters.append(search_value)

        parameters.append(search_value)


    # -----------------------------------------------------
    # CATEGORY FILTER
    # -----------------------------------------------------

    if category:

        query += """
            AND category = ?
        """

        parameters.append(category)


    # -----------------------------------------------------
    # PAYMENT FILTER
    # -----------------------------------------------------

    if payment:

        query += """
            AND payment = ?
        """

        parameters.append(payment)


    # -----------------------------------------------------
    # LATEST EXPENSES FIRST
    # -----------------------------------------------------

    query += """
        ORDER BY id DESC
    """


    # -----------------------------------------------------
    # GET EXPENSES
    # -----------------------------------------------------

    expenses = connection.execute(
        query,
        parameters
    ).fetchall()


    # =====================================================
    # DASHBOARD STATISTICS
    # =====================================================

    # Total spending

    total_spent = connection.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
    """).fetchone()[0]


    # -----------------------------------------------------
    # CURRENT MONTH
    # -----------------------------------------------------

    current_month = datetime.now().strftime("%Y-%m")


    # -----------------------------------------------------
    # CURRENT MONTH SPENDING
    # -----------------------------------------------------

    monthly_spent = connection.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
        WHERE date LIKE ?
    """, (
        current_month + "%",
    )).fetchone()[0]


    # -----------------------------------------------------
    # TRANSACTION COUNT
    # -----------------------------------------------------

    transaction_count = connection.execute("""
        SELECT COUNT(*)
        FROM expenses
    """).fetchone()[0]


    # =====================================================
    # CATEGORY-WISE DATA
    # =====================================================

    category_data = connection.execute("""
        SELECT
            category,
            SUM(amount) AS total

        FROM expenses

        GROUP BY category

        ORDER BY total DESC
    """).fetchall()


    category_labels = []

    category_amounts = []


    for row in category_data:

        category_labels.append(row["category"])

        category_amounts.append(row["total"])


    # =====================================================
    # MONTHLY SPENDING DATA
    # =====================================================

    monthly_data = connection.execute("""
        SELECT
            substr(date, 1, 7) AS month,
            SUM(amount) AS total

        FROM expenses

        GROUP BY month

        ORDER BY month
    """).fetchall()


    monthly_labels = []

    monthly_amounts = []


    for row in monthly_data:

        monthly_labels.append(row["month"])

        monthly_amounts.append(row["total"])


    connection.close()


    # =====================================================
    # SEND DATA TO HTML
    # =====================================================

    return render_template(

        "index.html",

        expenses=expenses,

        total_spent=total_spent,

        monthly_spent=monthly_spent,

        transaction_count=transaction_count,

        search=search,

        selected_category=category,

        selected_payment=payment,

        category_labels=category_labels,

        category_amounts=category_amounts,

        monthly_labels=monthly_labels,

        monthly_amounts=monthly_amounts
    )


# =========================================================
# ADD EXPENSE
# =========================================================

@app.route("/add", methods=["POST"])
def add_expense():

    date = request.form["date"]

    category = request.form["category"]

    description = request.form["description"]

    amount = request.form["amount"]

    payment = request.form["payment"]


    connection = get_db_connection()


    connection.execute("""
        INSERT INTO expenses
        (
            date,
            category,
            description,
            amount,
            payment
        )

        VALUES (?, ?, ?, ?, ?)
    """, (
        date,
        category,
        description,
        amount,
        payment
    ))


    connection.commit()

    connection.close()


    # Automatically update CSV
    update_csv_file()


    return redirect("/")


# =========================================================
# EDIT EXPENSE
# =========================================================

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_expense(id):

    connection = get_db_connection()


    # Get selected expense

    expense = connection.execute(
        """
        SELECT *
        FROM expenses
        WHERE id = ?
        """,
        (id,)
    ).fetchone()


    # If expense doesn't exist

    if expense is None:

        connection.close()

        return "Expense not found", 404


    # Update expense

    if request.method == "POST":

        date = request.form["date"]

        category = request.form["category"]

        description = request.form["description"]

        amount = request.form["amount"]

        payment = request.form["payment"]


        connection.execute("""
            UPDATE expenses

            SET
                date = ?,
                category = ?,
                description = ?,
                amount = ?,
                payment = ?

            WHERE id = ?

        """, (
            date,
            category,
            description,
            amount,
            payment,
            id
        ))


        connection.commit()

        connection.close()


        # Automatically update CSV
        update_csv_file()


        return redirect("/")


    connection.close()


    return render_template(
        "edit.html",
        expense=expense
    )


# =========================================================
# DELETE EXPENSE
# =========================================================

@app.route("/delete/<int:id>", methods=["POST"])
def delete_expense(id):

    connection = get_db_connection()


    connection.execute(
        """
        DELETE FROM expenses
        WHERE id = ?
        """,
        (id,)
    )


    connection.commit()

    connection.close()


    # Automatically update CSV
    update_csv_file()


    return redirect("/")


# =========================================================
# EXPORT EXPENSES TO CSV
# =========================================================

@app.route("/export")
def export_expenses():

    connection = get_db_connection()


    # Get all expenses

    expenses = connection.execute("""
        SELECT
            date,
            category,
            description,
            amount,
            payment

        FROM expenses

        ORDER BY date DESC
    """).fetchall()


    connection.close()


    # Create CSV in memory

    output = io.StringIO()

    writer = csv.writer(output)


    # CSV header

    writer.writerow([
        "Date",
        "Category",
        "Description",
        "Amount",
        "Payment"
    ])


    # Add expense rows

    for expense in expenses:

        writer.writerow([
            expense["date"],
            expense["category"],
            expense["description"],
            expense["amount"],
            expense["payment"]
        ])


    # Get CSV content

    csv_data = output.getvalue()

    output.close()


    # Send CSV file to browser

    return Response(

        csv_data,

        mimetype="text/csv",

        headers={
            "Content-Disposition":
            "attachment; filename=expenses.csv"
        }
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    create_table()

    # Create/update CSV when application starts
    update_csv_file()

    app.run(debug=True)
