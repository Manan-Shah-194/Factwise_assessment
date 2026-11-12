 # Factwise Team Project Planner

This project implements the Factwise team project planner assignment in Django.
The public API will be exposed through concrete Python classes that extend the
provided base classes. Data is stored locally in SQLite under `db/`, and board
exports are written to `out/`.

## Current status

Phase 4 is complete: the project now has concrete user and team APIs. The team
API supports team CRUD, admin validation, membership management, the 50-user
request limit, and team-user listing. Team admins are automatically added as
members when a team is created, so the admin is also visible through the team
membership API.

## Setup

```text
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python manage.py check
python manage.py migrate
python manage.py test
```

The SQLite database is created at `db/factwise.sqlite3`. Runtime database files
and generated exports are intentionally ignored by Git.
