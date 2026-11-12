import json
from pathlib import Path

from django.conf import settings
from django.test import TestCase

from planner.models import Team, TeamMembership, User
from project_board_api import ProjectBoardAPI


class BoardExportTests(TestCase):
    def setUp(self):
        self.api = ProjectBoardAPI()
        self.user = User.objects.create(name="asha", display_name="Asha Rao")
        self.team = Team.objects.create(name="Platform", admin=self.user)
        TeamMembership.objects.create(team=self.team, user=self.user)
        self.created_files = []

    def tearDown(self):
        for file_name in self.created_files:
            path = Path(settings.OUT_DIR) / file_name
            if path.exists():
                path.unlink()

    def _create_board(self):
        return json.loads(
            self.api.create_board(
                json.dumps(
                    {
                        "name": "Website Launch",
                        "description": "Release checklist",
                        "team_id": str(self.team.id),
                    }
                )
            )
        )

    def test_export_contains_board_and_task_details(self):
        board = self._create_board()
        task = json.loads(
            self.api.add_task(
                json.dumps(
                    {
                        "board_id": board["id"],
                        "title": "Prepare homepage",
                        "description": "Check final copy",
                        "user_id": str(self.user.id),
                    }
                )
            )
        )
        self.api.update_task_status(
            json.dumps({"id": task["id"], "status": "IN_PROGRESS"})
        )

        result = json.loads(self.api.export_board(json.dumps(board)))
        self.created_files.append(result["out_file"])
        content = (Path(settings.OUT_DIR) / result["out_file"]).read_text(encoding="utf-8")

        self.assertIn("PROJECT BOARD: Website Launch", content)
        self.assertIn("Team: Platform", content)
        self.assertIn("Status: OPEN", content)
        self.assertIn("[IN_PROGRESS] Prepare homepage", content)
        self.assertIn("Assigned to: Asha Rao (asha)", content)
        self.assertIn("Check final copy", content)

    def test_export_handles_empty_board(self):
        board = self._create_board()

        result = json.loads(self.api.export_board(json.dumps(board)))
        self.created_files.append(result["out_file"])
        content = (Path(settings.OUT_DIR) / result["out_file"]).read_text(encoding="utf-8")

        self.assertIn("TASKS (0)", content)
        self.assertIn("No tasks on this board.", content)

