import json
from pathlib import Path

from django.conf import settings
from django.test import TestCase

from planner.exceptions import InvalidRequestError, ValidationError
from project_board_api import ProjectBoardAPI
from team_api import TeamAPI
from user_api import UserAPI


class PlannerWorkflowTests(TestCase):
    def setUp(self):
        self.users = UserAPI()
        self.teams = TeamAPI()
        self.boards = ProjectBoardAPI()
        self.created_files = []

    def tearDown(self):
        for file_name in self.created_files:
            path = Path(settings.OUT_DIR) / file_name
            if path.exists():
                path.unlink()

    def test_complete_workflow_across_fresh_api_instances(self):
        user = json.loads(
            self.users.create_user(
                json.dumps({"name": "asha", "display_name": "Asha Rao"})
            )
        )
        team = json.loads(
            self.teams.create_team(
                json.dumps(
                    {
                        "name": "Platform",
                        "description": "Core platform team",
                        "admin": user["id"],
                    }
                )
            )
        )

        # New service objects represent a later process/API call while using
        # the same local database.
        fresh_users = UserAPI()
        fresh_teams = TeamAPI()
        fresh_boards = ProjectBoardAPI()

        self.assertEqual(
            json.loads(fresh_users.get_user_teams(json.dumps({"id": user["id"]}))),
            [
                {
                    "name": "Platform",
                    "description": "Core platform team",
                    "creation_time": json.loads(
                        fresh_teams.describe_team(json.dumps(team))
                    )["creation_time"],
                }
            ],
        )

        board = json.loads(
            fresh_boards.create_board(
                json.dumps(
                    {
                        "name": "Release",
                        "description": "Release checklist",
                        "team_id": team["id"],
                    }
                )
            )
        )
        task = json.loads(
            fresh_boards.add_task(
                json.dumps(
                    {
                        "board_id": board["id"],
                        "title": "Publish notes",
                        "description": "Prepare the release notes",
                        "user_id": user["id"],
                    }
                )
            )
        )
        fresh_boards.update_task_status(
            json.dumps({"id": task["id"], "status": "COMPLETE"})
        )
        fresh_boards.close_board(json.dumps(board))

        export = json.loads(fresh_boards.export_board(json.dumps(board)))
        self.created_files.append(export["out_file"])
        exported_content = (Path(settings.OUT_DIR) / export["out_file"]).read_text(
            encoding="utf-8"
        )
        self.assertIn("Status: CLOSED", exported_content)
        self.assertIn("[COMPLETE] Publish notes", exported_content)

    def test_all_json_apis_reject_malformed_requests(self):
        with self.assertRaises(InvalidRequestError):
            self.users.create_user("not-json")
        with self.assertRaises(InvalidRequestError):
            self.teams.create_team("not-json")
        with self.assertRaises(InvalidRequestError):
            self.boards.create_board("not-json")

    def test_board_timestamp_must_be_valid_iso8601(self):
        user = json.loads(
            self.users.create_user(json.dumps({"name": "asha", "display_name": "Asha"}))
        )
        team = json.loads(
            self.teams.create_team(
                json.dumps({"name": "Platform", "admin": user["id"]})
            )
        )

        with self.assertRaises(ValidationError):
            self.boards.create_board(
                json.dumps(
                    {
                        "name": "Release",
                        "team_id": team["id"],
                        "creation_time": "tomorrow morning",
                    }
                )
            )

    def test_empty_membership_request_is_rejected(self):
        user = json.loads(
            self.users.create_user(json.dumps({"name": "asha", "display_name": "Asha"}))
        )
        team = json.loads(
            self.teams.create_team(
                json.dumps({"name": "Platform", "admin": user["id"]})
            )
        )

        with self.assertRaises(ValidationError):
            self.teams.add_users_to_team(json.dumps({"id": team["id"], "users": []}))

