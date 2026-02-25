# Farm-Inventory-Manager

This project is a Farm Inventory Manager application, part of the Senior Design Project 2025/26.

## Project Structure
- **backend/**: Django server and application logic.
- **frontend/**: HTML templates (`templates`) and CSS/JS files (`static`).

## How to Run

1.  Open your terminal and navigate to the `backend` directory:
    ```bash
    cd backend
    ```
2.  Start the development server:
    ```bash
    python3 manage.py runserver
    ```
3.  Open your browser and go to: [http://127.0.0.1:8000/dashboard/]

## Initial Setup & Development

Because the project uses a local `db.sqlite3` database which is excluded from version control (`.gitignore`), **your database will be empty** after cloning or pulling the project from GitHub. 

To ensure the application functions correctly and all form dropdowns (Animals, Seeds, Tools, Expenses) are populated, you must run migrations and seed the database.

1.  Apply database migrations:
    ```bash
    python3 manage.py migrate
    ```

2.  Seed the default categories and items:
    ```bash
    python3 manage.py seed_all
    ```

## Creating a User Account

Since the database is local, you will need to create your own user account to access the dashboard:

```bash
python3 manage.py createsuperuser
```
Follow the prompts to set your username and password. Then, use these credentials to log in at [http://127.0.0.1:8000/login/].
