"""Persistent domain models for the team project planner."""

import uuid

from django.db import models
from django.utils import timezone


class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=128)
    creation_time = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.display_name or self.name


class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=64, unique=True)
    description = models.CharField(max_length=128, blank=True)
    admin = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="administered_teams",
    )
    creation_time = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class TeamMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="team_memberships")
    added_time = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("team", "user"),
                name="unique_team_membership",
            )
        ]


class Board(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=64)
    description = models.CharField(max_length=128, blank=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="boards")
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.OPEN)
    creation_time = models.DateTimeField(default=timezone.now, editable=False)
    end_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=("team", "name"),
                name="unique_board_name_per_team",
            )
        ]

    def __str__(self):
        return self.name


class Task(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETE = "COMPLETE", "Complete"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=64)
    description = models.CharField(max_length=128, blank=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="tasks")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    creation_time = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ("creation_time", "title")
        constraints = [
            models.UniqueConstraint(
                fields=("board", "title"),
                name="unique_task_title_per_board",
            )
        ]

    def __str__(self):
        return self.title

