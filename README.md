# Factwise Team Project Planner

This is a Django implementation of the Factwise team project planner
assessment. It exposes the supplied Python base classes through concrete JSON
APIs for users, teams, project boards, and tasks.

The application uses a local SQLite database for persistence. The database is
created under `db/`, and board reports are written as readable text files under
`out/`.

## Project structure

```text
config/                 Django project settings
planner/                Models, migrations, validation, and tests
user_base.py            Supplied user API interface
user_api.py             Concrete user API
team_base.py            Supplied team API interface
team_api.py             Concrete team API
project_board_base.py   Supplied board/task API interface
project_board_api.py    Concrete board/task API and export
db/                     Runtime SQLite database (not submitted)
out/                    Generated board exports (not submitted)
```

## Setup

Python 3.11 or newer is recommended.

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
python manage.py check
python manage.py migrate
```

## Running the tests

```powershell
python manage.py test
```

The test suite covers all API groups, validation rules, database constraints,
cross-API workflows, persistence, and board export. The current suite contains
43 tests.

## API usage

The APIs receive JSON strings and return JSON strings.

```python
import json

from user_api import UserAPI
from team_api import TeamAPI
from project_board_api import ProjectBoardAPI

users = UserAPI()
teams = TeamAPI()
boards = ProjectBoardAPI()

user = json.loads(
    users.create_user(json.dumps({
        "name": "asha",
        "display_name": "Asha Rao",
    }))
)

team = json.loads(
    teams.create_team(json.dumps({
        "name": "Platform",
        "description": "Core platform team",
        "admin": user["id"],
    }))
)

board = json.loads(
    boards.create_board(json.dumps({
        "name": "Release",
        "description": "Release checklist",
        "team_id": team["id"],
    }))
)

task = json.loads(
    boards.add_task(json.dumps({
        "board_id": board["id"],
        "title": "Prepare release notes",
        "description": "Write the final notes",
        "user_id": user["id"],
    }))
)
```

`add_task` includes `board_id`. The original brief omitted that field, but a
task needs an explicit board relationship.

## Design decisions

- UUID strings are used for public IDs.
- Timestamps are stored and returned as ISO 8601 values.
- User and team names are trimmed and validated before saving.
- User names and team names are globally unique.
- Board names are unique within a team.
- Task titles are unique within a board.
- A team admin is automatically added as a team member.
- A task assignee must be a member of the board's team.
- Adding or removing users is limited to 50 IDs per request.
- Adding an existing membership and removing a missing membership are safe,
  repeatable operations.
- Invalid requests raise planner-specific exceptions instead of exposing
  database exceptions to callers.
- Boards can only be closed after all their tasks are complete.
- The documented response shapes are followed, including list responses that
  do not expose IDs unless the supplied interface explicitly asks for them.

## Board exports

Calling `export_board` creates a file like this:

```text
out/board_<board_id>.txt
```

The report contains the board name, team, description, status, timestamps, and
all task details including status, assignee, and description.

## Submission

The final ZIP should include the source code, migrations, tests, README, and
`requirements.txt`. It should not include:

- `.git/`
- `.venv/` or `venv/`
- `__pycache__/`
- SQLite files under `db/`
- Generated exports under `out/`
- Installed third-party libraries

The application creates the runtime directories and database when set up on a
new machine.
