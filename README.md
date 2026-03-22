# Farm-Inventory-Manager

This project is a Farm Inventory Manager application, part of the Senior Design Project 2025/26.

## Project Structure
- **backend/**: Django server and application logic.
- **frontend/**: Django templates (`templates`) and shared CSS/JS assets (`static`).
- **docs/**: project notes and planning documents.
- **scripts/**: utility scripts for testing and responsive checks.

## Features
- Dashboard with quick income and quick expense flows
- Inventory tracking
- Animals, seeds, farm products, and tools management
- Expenses and incomes tracking
- Reports and notifications
- Sidebar settings/help/profile pages
- Sync page for offline/online data flow

## How to Run

1. Open your terminal and navigate to the `backend` directory:
    ```bash
    cd backend
    ```
2. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3. Configure environment variables in the project root `.env` file.
   Required database variables:
    ```env
    SECRET_KEY=your-secret-key
    DEBUG=True
    PGDATABASE=your_database_name
    PGUSER=your_database_user
    PGPASSWORD=your_database_password
    PGHOST=your_database_host
    PGPORT=5432
    ```
4. Apply database migrations:
    ```bash
    python manage.py migrate
    ```
5. Seed the default data:
    ```bash
    python manage.py seed_all
    ```
6. Start the development server:
    ```bash
    python manage.py runserver
    ```
7. Open your browser and go to: [http://127.0.0.1:8000/dashboard/](http://127.0.0.1:8000/dashboard/)

## Initial Setup & Development

The app is configured to use PostgreSQL in normal development/runtime, and SQLite only during automated tests. After cloning or pulling, make sure your PostgreSQL database is available and your `.env` values are set correctly before running migrations.

`python manage.py seed_all` runs the built-in seed commands for:
- Animals
- Expenses
- Seeds
- Farm Products
- Tools

## Creating a User Account

Create an account for dashboard access with either command:

```bash
python manage.py createsuperuser
```

or:

```bash
python create_admin.py
```

The helper script creates or resets a default admin user:
- username: `admin`
- password: `admin123`

Login page: [http://127.0.0.1:8000/login/](http://127.0.0.1:8000/login/)
