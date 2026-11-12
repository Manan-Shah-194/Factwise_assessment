 # Factwise Team Project Planner

This project implements the Factwise team project planner assignment in Django.
The public API will be exposed through concrete Python classes that extend the
provided base classes. Data is stored locally in SQLite under `db/`, and board
exports are written to `out/`.

## Current status

Phase 6 is complete: the project now has concrete user, team, board, and task
APIs, plus readable board exports. `export_board` writes a text report to
`out/` containing the board, team, status, timestamps, and task details.
`add_task` accepts the required `board_id` field in addition to the fields shown
in the original brief.

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
