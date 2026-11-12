"""Concrete implementation of the team management API."""

from uuid import UUID

from django.db import IntegrityError
from django.utils import timezone

from planner.exceptions import ConflictError, NotFoundError, ValidationError
from planner.json_utils import parse_request, response
from planner.models import Team, TeamMembership, User
from planner.transactions import atomic_write
from planner.validators import optional_string, required_field, required_list, required_string
from team_base import TeamBase


class TeamAPI(TeamBase):
    """Manage teams and their user memberships through JSON requests."""

    def create_team(self, request: str) -> str:
        payload = parse_request(request)
        name = required_string(payload, "name", 64)
        description = optional_string(payload, "description", 128)
        admin = _get_user(required_field(payload, "admin"))

        if Team.objects.filter(name=name).exists():
            raise ConflictError("a team with this name already exists")

        try:
            with atomic_write():
                team = Team.objects.create(
                    name=name,
                    description=description,
                    admin=admin,
                )
                TeamMembership.objects.create(team=team, user=admin)
        except IntegrityError as exc:
            raise ConflictError("a team with this name already exists") from exc

        return response({"id": str(team.id)})

    def list_teams(self) -> str:
        teams = [self._team_details(team) for team in Team.objects.select_related("admin")]
        return response(teams)

    def describe_team(self, request: str) -> str:
        payload = parse_request(request)
        team = _get_team(required_field(payload, "id"))
        return response(self._team_details(team))

    def update_team(self, request: str) -> str:
        payload = parse_request(request)
        team = _get_team(required_field(payload, "id"))
        changes = payload.get("team")

        if not isinstance(changes, dict):
            raise ValidationError("team must be an object")

        name = (
            required_string(changes, "name", 64)
            if "name" in changes
            else team.name
        )
        description = (
            optional_string(changes, "description", 128)
            if "description" in changes
            else team.description
        )
        admin = (
            _get_user(required_field(changes, "admin"))
            if "admin" in changes
            else team.admin
        )

        duplicate = Team.objects.filter(name=name).exclude(pk=team.pk).exists()
        if duplicate:
            raise ConflictError("a team with this name already exists")

        try:
            with atomic_write():
                team.name = name
                team.description = description
                team.admin = admin
                team.save(update_fields=["name", "description", "admin"])
                TeamMembership.objects.get_or_create(team=team, user=admin)
        except IntegrityError as exc:
            raise ConflictError("a team with this name already exists") from exc

        return response({"success": True})

    def add_users_to_team(self, request: str):
        payload = parse_request(request)
        team = _get_team(required_field(payload, "id"))
        user_ids = _user_id_values(required_list(payload, "users", maximum_length=50))
        users = _get_users(user_ids)

        with atomic_write():
            for user in users:
                TeamMembership.objects.get_or_create(team=team, user=user)

        return response({"success": True})

    def remove_users_from_team(self, request: str):
        payload = parse_request(request)
        team = _get_team(required_field(payload, "id"))
        user_ids = _user_id_values(required_list(payload, "users", maximum_length=50))
        _get_users(user_ids)

        with atomic_write():
            TeamMembership.objects.filter(team=team, user_id__in=user_ids).delete()

        return response({"success": True})

    def list_team_users(self, request: str):
        payload = parse_request(request)
        team = _get_team(required_field(payload, "id"))
        users = [
            {
                "id": str(membership.user.id),
                "name": membership.user.name,
                "display_name": membership.user.display_name,
            }
            for membership in team.memberships.select_related("user").order_by("user__name")
        ]
        return response(users)

    @staticmethod
    def _team_details(team):
        return {
            "name": team.name,
            "description": team.description,
            "creation_time": _format_time(team.creation_time),
            "admin": str(team.admin_id),
        }


def _get_team(raw_id):
    try:
        team_id = UUID(str(raw_id))
    except (AttributeError, TypeError, ValueError) as exc:
        raise NotFoundError("team was not found") from exc

    try:
        return Team.objects.select_related("admin").get(pk=team_id)
    except Team.DoesNotExist as exc:
        raise NotFoundError("team was not found") from exc


def _get_user(raw_id):
    try:
        user_id = UUID(str(raw_id))
    except (AttributeError, TypeError, ValueError) as exc:
        raise NotFoundError("user was not found") from exc

    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist as exc:
        raise NotFoundError("user was not found") from exc


def _user_id_values(raw_ids):
    if not raw_ids:
        raise ValidationError("users cannot be empty")

    values = []
    seen = set()
    for raw_id in raw_ids:
        try:
            user_id = UUID(str(raw_id))
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValidationError("users must contain valid user IDs") from exc
        if user_id not in seen:
            values.append(user_id)
            seen.add(user_id)
    return values


def _get_users(user_ids):
    users = list(User.objects.filter(id__in=user_ids))
    users_by_id = {user.id: user for user in users}
    missing = [user_id for user_id in user_ids if user_id not in users_by_id]
    if missing:
        raise NotFoundError("one or more users were not found")
    return [users_by_id[user_id] for user_id in user_ids]


def _format_time(value):
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    return value.isoformat()

