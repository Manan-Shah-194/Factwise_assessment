import json

from django.test import TestCase

from planner.exceptions import ConflictError, NotFoundError, ValidationError
from planner.models import Team, TeamMembership, User
from user_api import UserAPI


class UserAPITests(TestCase):
    def setUp(self):
        self.api = UserAPI()

    def test_create_and_describe_user(self):
        created = json.loads(
            self.api.create_user(
                json.dumps({"name": "asha", "display_name": "Asha Rao"})
            )
        )

        details = json.loads(self.api.describe_user(json.dumps(created)))

        self.assertEqual(details["name"], "asha")
        self.assertEqual(details["display_name"], "Asha Rao")
        self.assertIn("creation_time", details)

    def test_create_rejects_duplicate_name(self):
        self.api.create_user(json.dumps({"name": "asha", "display_name": "Asha"}))

        with self.assertRaises(ConflictError):
            self.api.create_user(json.dumps({"name": "asha", "display_name": "Another"}))

    def test_list_users_returns_documented_fields(self):
        self.api.create_user(json.dumps({"name": "zoya", "display_name": "Zoya"}))
        self.api.create_user(json.dumps({"name": "asha", "display_name": "Asha"}))

        users = json.loads(self.api.list_users())

        self.assertEqual([user["name"] for user in users], ["asha", "zoya"])
        self.assertNotIn("id", users[0])

    def test_update_changes_display_name_but_not_name(self):
        created = json.loads(
            self.api.create_user(json.dumps({"name": "asha", "display_name": "Asha"}))
        )

        result = self.api.update_user(
            json.dumps(
                {
                    "id": created["id"],
                    "user": {"name": "asha", "display_name": "Asha Rao"},
                }
            )
        )

        self.assertEqual(json.loads(result), {"success": True})
        self.assertEqual(User.objects.get(pk=created["id"]).display_name, "Asha Rao")

    def test_update_rejects_name_change(self):
        created = json.loads(
            self.api.create_user(json.dumps({"name": "asha", "display_name": "Asha"}))
        )

        with self.assertRaises(ValidationError):
            self.api.update_user(
                json.dumps(
                    {
                        "id": created["id"],
                        "user": {"name": "new-name", "display_name": "Asha"},
                    }
                )
            )

    def test_update_allows_longer_display_name(self):
        created = json.loads(
            self.api.create_user(json.dumps({"name": "asha", "display_name": "Asha"}))
        )
        long_display_name = "A" * 100

        self.api.update_user(
            json.dumps(
                {
                    "id": created["id"],
                    "user": {"display_name": long_display_name},
                }
            )
        )

        self.assertEqual(User.objects.get(pk=created["id"]).display_name, long_display_name)

    def test_unknown_user_raises_not_found(self):
        with self.assertRaises(NotFoundError):
            self.api.describe_user(json.dumps({"id": "00000000-0000-0000-0000-000000000000"}))

    def test_get_user_teams_returns_memberships(self):
        user = User.objects.create(name="asha", display_name="Asha")
        team = Team.objects.create(name="Platform", description="Core team", admin=user)
        TeamMembership.objects.create(team=team, user=user)

        teams = json.loads(self.api.get_user_teams(json.dumps({"id": str(user.id)})))

        self.assertEqual(teams, [{
            "name": "Platform",
            "description": "Core team",
            "creation_time": team.creation_time.isoformat(),
        }])

