# Farm Inventory Manager

Farm Inventory Manager is a Django-based farm operations app for tracking stock, expenses, income, suppliers, reminders, and basic sync activity.

## Project Structure

- `backend/`: Django project, apps, migrations, and management commands
- `frontend/`: Django templates and shared static assets
- `scripts/`: utility scripts for responsive/manual checks

## Main Modules

- Dashboard with weekly summary, quick expense, and quick income flows
- Inventory pages for stock overview, add-product flow, barcode generation, and scan lookup
- Animals, seeds, farm products, and tools management
- Expenses and incomes tracking
- Supplier management
- Notifications and stock alert rules
- Expense reports and printable report view
- User login/signup/profile/settings/help pages
- Sync page with push/status endpoints for offline-first flows
- Azerbaijani, English, and Russian interface support

## Tech Stack

- Python 3.11 or 3.12
- Django 5.2
- PostgreSQL for normal development/runtime
- SQLite only during automated tests
- Django templates for UI
- `faster-whisper` + `av` for voice transcription in add-product

`Python 3.14` is not recommended here because `faster-whisper` can fail there.

## Setup

1. Create and activate a virtual environment:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a root-level `.env` file in the project directory:

```env
SECRET_KEY=37e9cd5c610d129ac2995aea4c91d865
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

PGHOST=ep-little-pine-agthlvz0-pooler.c-2.eu-central-1.aws.neon.tech
PGDATABASE=neondb
PGUSER=neondb_owner
PGPASSWORD=npg_n7yoqzbECJF8
PGPORT=5432
```

Notes:

- The app loads `.env` from the repository root, not from `backend/`.
- Normal runtime uses PostgreSQL with `sslmode=require`.
- If `DEBUG=True`, Django allows all hosts.

4. Apply migrations:

```bash
python manage.py migrate
```

5. Seed default catalog data:

```bash
python manage.py seed_all
```

This seeds:

- Animals
- Expenses
- Seeds
- Farm Products
- Tools

6. Start the development server:

```bash
python manage.py runserver
```

7. Open the app:

- Dashboard: [http://127.0.0.1:8000/dashboard/](http://127.0.0.1:8000/dashboard/)
- Login: [http://127.0.0.1:8000/login/](http://127.0.0.1:8000/login/)

## User Creation

Create an admin account with either command:

```bash
python manage.py createsuperuser
```

or:

```bash
python create_admin.py
```

`create_admin.py` creates or resets this default account:

- username: `admin`
- password: `admin123`

## Voice Input

The add-product page includes server-side voice transcription.

- Browser audio is uploaded from the add-product form
- Backend transcription runs through `faster-whisper`
- Supported UI/voice language flow is Azerbaijani, English, and Russian

## Testing

Run tests with:

```bash
python manage.py test
```

During tests, settings automatically switch the database to SQLite.
