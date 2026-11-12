import json

from django.test import TestCase

from planner.exceptions import ConflictError, NotFoundError, ValidationError
from planner.models import TeamMembership, User
from team_api import TeamAPI


class TeamAPITests(TestCase):
    def setUp(self):
        self.api = TeamAPI()
        self.admin = User.objects.create(name="asha", display_name="Asha")
        self.other_user = User.objects.create(name="rahul", display_name="Rahul")

    def _create_team(self, name="Platform"):
        return json.loads(
            self.api.create_team(
                json.dumps(
                    {
                        "name": name,
                        "description": "Core team",
                        "admin": str(self.admin.id),
                    }
                )
            )
        )

    def test_create_team_adds_admin_as_member(self):
        created = self._create_team()

        users = json.loads(self.api.list_team_users(json.dumps(created)))

        self.assertEqual(users, [{
            "id": str(self.admin.id),
            "name": "asha",
            "display_name": "Asha",
        }])

    def test_create_rejects_duplicate_name(self):
        self._create_team()

        with self.assertRaises(ConflictError):
            self._create_team()

    def test_list_and_describe_team(self):
        created = self._create_team()

        teams = json.loads(self.api.list_teams())
        details = json.loads(self.api.describe_team(json.dumps(created)))

        self.assertEqual(teams[0]["name"], "Platform")
        self.assertEqual(details["admin"], str(self.admin.id))
        self.assertEqual(details["description"], "Core team")

    def test_update_team(self):
        created = self._create_team()

        result = self.api.update_team(
            json.dumps(
                {
                    "id": created["id"],
                    "team": {
                        "name": "Infrastructure",
                        "description": "Updated team",
                        "admin": str(self.other_user.id),
                    },
                }
            )
        )

        self.assertEqual(json.loads(result), {"success": True})
        details = json.loads(self.api.describe_team(json.dumps(created)))
        self.assertEqual(details["name"], "Infrastructure")
        self.assertEqual(details["admin"], str(self.other_user.id))

    def test_add_and_remove_users(self):
        created = self._create_team()

        self.api.add_users_to_team(
            json.dumps({"id": created["id"], "users": [str(self.other_user.id)]})
        )
        self.assertEqual(TeamMembership.objects.filter(team_id=created["id"]).count(), 2)

        self.api.remove_users_from_team(
            json.dumps({"id": created["id"], "users": [str(self.other_user.id)]})
        )
        self.assertEqual(TeamMembership.objects.filter(team_id=created["id"]).count(), 1)

    def test_membership_requests_are_limited_to_50_users(self):
        created = self._create_team()
        many_users = [str(self.other_user.id)] * 51

        with self.assertRaises(ValidationError):
            self.api.add_users_to_team(json.dumps({"id": created["id"], "users": many_users}))

    def test_missing_user_is_rejected(self):
        created = self._create_team()

        with self.assertRaises(NotFoundError):
            self.api.add_users_to_team(
                json.dumps(
                    {
                        "id": created["id"],
                        "users": ["00000000-0000-0000-0000-000000000000"],
                    }
                )
            )

