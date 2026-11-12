"""Concrete implementation of the user management API."""

from uuid import UUID

from django.db import IntegrityError
from django.utils import timezone

from planner.exceptions import ConflictError, NotFoundError, ValidationError
from planner.json_utils import parse_request, response
from planner.models import User
from planner.transactions import atomic_write
from planner.validators import required_field, required_string
from user_base import UserBase


class UserAPI(UserBase):
    """Manage planner users through the JSON-based base interface."""

    def create_user(self, request: str) -> str:
        payload = parse_request(request)
        name = required_string(payload, "name", 64)
        display_name = required_string(payload, "display_name", 64)

        if User.objects.filter(name=name).exists():
            raise ConflictError("a user with this name already exists")

        try:
            with atomic_write():
                user = User.objects.create(name=name, display_name=display_name)
        except IntegrityError as exc:
            raise ConflictError("a user with this name already exists") from exc

        return response({"id": str(user.id)})

    def list_users(self) -> str:
        users = [
            {
                "name": user.name,
                "display_name": user.display_name,
                "creation_time": _format_time(user.creation_time),
            }
            for user in User.objects.all()
        ]
        return response(users)

    def describe_user(self, request: str) -> str:
        payload = parse_request(request)
        user = _get_user(required_field(payload, "id"))

        return response(
            {
                "name": user.name,
                "display_name": user.display_name,
                "creation_time": _format_time(user.creation_time),
            }
        )

    def update_user(self, request: str) -> str:
        payload = parse_request(request)
        user = _get_user(required_field(payload, "id"))
        changes = payload.get("user")

        if not isinstance(changes, dict):
            raise ValidationError("user must be an object")

        if "name" in changes:
            requested_name = required_string(changes, "name", 64)
            if requested_name != user.name:
                raise ValidationError("user name cannot be updated")

        display_name = required_string(changes, "display_name", 128)
        user.display_name = display_name
        user.save(update_fields=["display_name"])

        return response({"success": True})

    def get_user_teams(self, request: str) -> str:
        payload = parse_request(request)
        user = _get_user(required_field(payload, "id"))

        teams = [
            {
                "name": membership.team.name,
                "description": membership.team.description,
                "creation_time": _format_time(membership.team.creation_time),
            }
            for membership in user.team_memberships.select_related("team").all()
        ]
        return response(teams)


def _get_user(raw_id):
    """Return a user or raise a stable planner-level not-found error."""
    try:
        user_id = UUID(str(raw_id))
    except (AttributeError, TypeError, ValueError) as exc:
        raise NotFoundError("user was not found") from exc

    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist as exc:
        raise NotFoundError("user was not found") from exc


def _format_time(value):
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    return value.isoformat()

