import json

from django.test import TestCase

from planner.exceptions import ConflictError, NotFoundError, ValidationError
from planner.models import Board, Task, Team, TeamMembership, User
from project_board_api import ProjectBoardAPI


class ProjectBoardAPITests(TestCase):
    def setUp(self):
        self.api = ProjectBoardAPI()
        self.admin = User.objects.create(name="asha", display_name="Asha")
        self.member = User.objects.create(name="rahul", display_name="Rahul")
        self.team = Team.objects.create(name="Platform", admin=self.admin)
        TeamMembership.objects.create(team=self.team, user=self.admin)
        TeamMembership.objects.create(team=self.team, user=self.member)

    def _create_board(self, name="Launch"):
        return json.loads(
            self.api.create_board(
                json.dumps(
                    {
                        "name": name,
                        "description": "Release work",
                        "team_id": str(self.team.id),
                        "creation_time": "2026-01-01T10:00:00+05:30",
                    }
                )
            )
        )

    def _add_task(self, board_id, title="Prepare"):
        return json.loads(
            self.api.add_task(
                json.dumps(
                    {
                        "board_id": board_id,
                        "title": title,
                        "description": "Task details",
                        "user_id": str(self.member.id),
                        "creation_time": "2026-01-01T11:00:00+05:30",
                    }
                )
            )
        )

    def test_create_board_and_list_open_boards(self):
        created = self._create_board()

        boards = json.loads(self.api.list_boards(json.dumps({"id": str(self.team.id)})))

        self.assertEqual(boards, [{"id": created["id"], "name": "Launch"}])

    def test_board_names_are_unique_per_team(self):
        self._create_board()

        with self.assertRaises(ConflictError):
            self._create_board()

    def test_add_task_requires_team_membership(self):
        outsider = User.objects.create(name="zoya", display_name="Zoya")
        board = self._create_board()

        with self.assertRaises(ConflictError):
            self.api.add_task(
                json.dumps(
                    {
                        "board_id": board["id"],
                        "title": "Prepare",
                        "user_id": str(outsider.id),
                    }
                )
            )

    def test_add_task_and_update_status(self):
        board = self._create_board()
        task = self._add_task(board["id"])

        result = self.api.update_task_status(
            json.dumps({"id": task["id"], "status": "IN_PROGRESS"})
        )

        self.assertEqual(json.loads(result), {"success": True})
        self.assertEqual(Task.objects.get(pk=task["id"]).status, Task.Status.IN_PROGRESS)

    def test_task_titles_are_unique_per_board(self):
        board = self._create_board()
        self._add_task(board["id"])

        with self.assertRaises(ConflictError):
            self._add_task(board["id"])

    def test_invalid_task_status_is_rejected(self):
        board = self._create_board()
        task = self._add_task(board["id"])

        with self.assertRaises(ValidationError):
            self.api.update_task_status(
                json.dumps({"id": task["id"], "status": "DONE"})
            )

    def test_board_cannot_close_with_incomplete_tasks(self):
        board = self._create_board()
        self._add_task(board["id"])

        with self.assertRaises(ValidationError):
            self.api.close_board(json.dumps(board))

    def test_completed_board_can_close_and_disappears_from_open_list(self):
        board = self._create_board()
        task = self._add_task(board["id"])
        self.api.update_task_status(
            json.dumps({"id": task["id"], "status": "COMPLETE"})
        )

        result = self.api.close_board(json.dumps(board))
        open_boards = json.loads(
            self.api.list_boards(json.dumps({"id": str(self.team.id)}))
        )

        self.assertEqual(json.loads(result), {"success": True})
        self.assertEqual(open_boards, [])
        closed_board = Board.objects.get(pk=board["id"])
        self.assertEqual(closed_board.status, Board.Status.CLOSED)
        self.assertIsNotNone(closed_board.end_time)

    def test_closed_board_rejects_new_tasks(self):
        board = self._create_board()
        self.api.close_board(json.dumps(board))

        with self.assertRaises(ConflictError):
            self._add_task(board["id"])

    def test_unknown_board_raises_not_found(self):
        with self.assertRaises(NotFoundError):
            self.api.close_board(
                json.dumps({"id": "00000000-0000-0000-0000-000000000000"})
            )

