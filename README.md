 # Factwise Team Project Planner

This project implements the Factwise team project planner assignment in Django.
The public API will be exposed through concrete Python classes that extend the
provided base classes. Data is stored locally in SQLite under `db/`, and board
exports are written to `out/`.

## Current status

Phase 2 is complete: the project now has persistent User, Team, membership,
Board, and Task models, shared request validation, JSON helpers, planner
exceptions, transaction support, and initial model tests. Concrete API methods
will be added in the next phases.

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
