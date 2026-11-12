import json
from uuid import UUID

from django.db import IntegrityError
from django.test import TestCase

from .exceptions import InvalidRequestError, ValidationError
from .json_utils import parse_request, response
from .models import Board, Task, Team, TeamMembership, User
from .validators import optional_string, required_list, required_string


class JsonHelperTests(TestCase):
    def test_parse_request_accepts_json_object(self):
        self.assertEqual(parse_request('{"name": "Asha"}'), {"name": "Asha"})

    def test_parse_request_rejects_invalid_json(self):
        with self.assertRaises(InvalidRequestError):
            parse_request("not-json")

    def test_parse_request_rejects_json_arrays(self):
        with self.assertRaises(InvalidRequestError):
            parse_request("[]")

    def test_response_returns_json(self):
        self.assertEqual(json.loads(response({"ok": True})), {"ok": True})


class ValidationHelperTests(TestCase):
    def test_required_string_trims_values(self):
        self.assertEqual(required_string({"name": " Asha "}, "name", 64), "Asha")

    def test_required_string_rejects_empty_values(self):
        with self.assertRaises(ValidationError):
            required_string({"name": "   "}, "name", 64)

    def test_optional_string_defaults_to_empty(self):
        self.assertEqual(optional_string({}, "description", 128), "")

    def test_required_list_enforces_maximum(self):
        with self.assertRaises(ValidationError):
            required_list({"users": ["a", "b"]}, "users", 1)


class ModelConstraintTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(name="asha", display_name="Asha")
        self.team = Team.objects.create(
            name="Platform",
            description="Platform team",
            admin=self.user,
        )
        self.board = Board.objects.create(
            name="Launch",
            description="Launch board",
            team=self.team,
        )

    def test_ids_are_uuids(self):
        self.assertIsInstance(UUID(str(self.user.id)), UUID)
        self.assertIsInstance(UUID(str(self.team.id)), UUID)
        self.assertIsInstance(UUID(str(self.board.id)), UUID)

    def test_team_membership_is_unique(self):
        TeamMembership.objects.create(team=self.team, user=self.user)
        with self.assertRaises(IntegrityError):
            TeamMembership.objects.create(team=self.team, user=self.user)

    def test_board_names_are_unique_per_team(self):
        with self.assertRaises(IntegrityError):
            Board.objects.create(name="Launch", team=self.team)

    def test_task_titles_are_unique_per_board(self):
        Task.objects.create(board=self.board, title="Prepare", user=self.user)
        with self.assertRaises(IntegrityError):
            Task.objects.create(board=self.board, title="Prepare", user=self.user)

