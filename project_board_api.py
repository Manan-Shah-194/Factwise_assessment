"""Concrete implementation of the project board and task API."""

from uuid import UUID

from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from planner.exceptions import ConflictError, NotFoundError, ValidationError
from planner.json_utils import parse_request, response
from planner.models import Board, Task, Team, TeamMembership, User
from planner.transactions import atomic_write
from planner.validators import optional_string, required_field, required_string
from project_board_base import ProjectBoardBase


class ProjectBoardAPI(ProjectBoardBase):
    """Manage project boards and tasks through JSON requests."""

    def create_board(self, request: str) -> str:
        payload = parse_request(request)
        name = required_string(payload, "name", 64)
        description = optional_string(payload, "description", 128)
        team = _get_team(required_field(payload, "team_id"))
        creation_time = _request_time(payload, "creation_time")

        if Board.objects.filter(team=team, name=name).exists():
            raise ConflictError("a board with this name already exists for this team")

        try:
            with atomic_write():
                board = Board.objects.create(
                    name=name,
                    description=description,
                    team=team,
                    creation_time=creation_time,
                )
        except IntegrityError as exc:
            raise ConflictError("a board with this name already exists for this team") from exc

        return response({"id": str(board.id)})

    def close_board(self, request: str) -> str:
        payload = parse_request(request)
        board = _get_board(required_field(payload, "id"))

        if board.status == Board.Status.CLOSED:
            raise ConflictError("board is already closed")
        if board.tasks.exclude(status=Task.Status.COMPLETE).exists():
            raise ValidationError("a board can only be closed when all tasks are complete")

        with atomic_write():
            board.status = Board.Status.CLOSED
            board.end_time = timezone.now()
            board.save(update_fields=["status", "end_time"])

        return response({"success": True})

    def add_task(self, request: str) -> str:
        payload = parse_request(request)
        title = required_string(payload, "title", 64)
        description = optional_string(payload, "description", 128)
        board = _get_board(required_field(payload, "board_id"))
        user = _get_user(required_field(payload, "user_id"))
        creation_time = _request_time(payload, "creation_time")

        if board.status != Board.Status.OPEN:
            raise ConflictError("tasks can only be added to open boards")
        if not TeamMembership.objects.filter(team=board.team, user=user).exists():
            raise ConflictError("task user must be a member of the board team")
        if Task.objects.filter(board=board, title=title).exists():
            raise ConflictError("a task with this title already exists for this board")

        try:
            with atomic_write():
                task = Task.objects.create(
                    board=board,
                    title=title,
                    description=description,
                    user=user,
                    creation_time=creation_time,
                )
        except IntegrityError as exc:
            raise ConflictError("a task with this title already exists for this board") from exc

        return response({"id": str(task.id)})

    def update_task_status(self, request: str):
        payload = parse_request(request)
        task = _get_task(required_field(payload, "id"))
        status = required_string(payload, "status", 11)

        if status not in Task.Status.values:
            raise ValidationError("status must be OPEN, IN_PROGRESS, or COMPLETE")
        if task.board.status != Board.Status.OPEN:
            raise ConflictError("tasks on closed boards cannot be updated")

        task.status = status
        task.save(update_fields=["status"])
        return response({"success": True})

    def list_boards(self, request: str) -> str:
        payload = parse_request(request)
        team = _get_team(required_field(payload, "id"))
        boards = [
            {"id": str(board.id), "name": board.name}
            for board in team.boards.filter(status=Board.Status.OPEN)
        ]
        return response(boards)

    def export_board(self, request: str) -> str:
        payload = parse_request(request)
        board = _get_board(required_field(payload, "id"))
        board = Board.objects.select_related("team").prefetch_related(
            "tasks__user"
        ).get(pk=board.pk)

        file_name = f"board_{board.id}.txt"
        output_directory = settings.OUT_DIR
        output_directory.mkdir(parents=True, exist_ok=True)
        output_path = output_directory / file_name
        output_path.write_text(_render_board(board), encoding="utf-8")

        return response({"out_file": file_name})


BoardAPI = ProjectBoardAPI


def _render_board(board):
    tasks = list(board.tasks.all())
    lines = [
        "=" * 64,
        f"PROJECT BOARD: {board.name}",
        "=" * 64,
        f"Team: {board.team.name}",
        f"Status: {board.status}",
        f"Created: {_format_time(board.creation_time)}",
    ]

    if board.end_time is not None:
        lines.append(f"Closed: {_format_time(board.end_time)}")

    lines.extend(
        [
            "",
            "DESCRIPTION",
            "-----------",
            board.description or "No description provided.",
            "",
            f"TASKS ({len(tasks)})",
            "---------",
        ]
    )

    if not tasks:
        lines.append("No tasks on this board.")
    else:
        for number, task in enumerate(tasks, start=1):
            lines.extend(
                [
                    "",
                    f"{number}. [{task.status}] {task.title}",
                    f"   Assigned to: {task.user.display_name} ({task.user.name})",
                    f"   Created: {_format_time(task.creation_time)}",
                    f"   Description: {task.description or 'No description provided.'}",
                ]
            )

    lines.extend(["", "=" * 64, ""])
    return "\n".join(lines)


def _get_team(raw_id):
    try:
        team_id = UUID(str(raw_id))
    except (AttributeError, TypeError, ValueError) as exc:
        raise NotFoundError("team was not found") from exc

    try:
        return Team.objects.get(pk=team_id)
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


def _get_board(raw_id):
    try:
        board_id = UUID(str(raw_id))
    except (AttributeError, TypeError, ValueError) as exc:
        raise NotFoundError("board was not found") from exc

    try:
        return Board.objects.select_related("team").get(pk=board_id)
    except Board.DoesNotExist as exc:
        raise NotFoundError("board was not found") from exc


def _get_task(raw_id):
    try:
        task_id = UUID(str(raw_id))
    except (AttributeError, TypeError, ValueError) as exc:
        raise NotFoundError("task was not found") from exc

    try:
        return Task.objects.select_related("board").get(pk=task_id)
    except Task.DoesNotExist as exc:
        raise NotFoundError("task was not found") from exc


def _request_time(payload, field):
    raw_value = payload.get(field)
    if raw_value is None:
        return timezone.now()
    if not isinstance(raw_value, str):
        raise ValidationError(f"{field} must be an ISO 8601 timestamp")

    parsed = parse_datetime(raw_value)
    if parsed is None:
        raise ValidationError(f"{field} must be an ISO 8601 timestamp")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _format_time(value):
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    return value.isoformat()

