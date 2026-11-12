"""Exceptions raised by the planner API."""


class PlannerError(Exception):
    """Base class for expected planner errors."""


class InvalidRequestError(PlannerError):
    """Raised when a request is not valid JSON or has the wrong shape."""


class ValidationError(PlannerError):
    """Raised when a request contains invalid field values."""


class NotFoundError(PlannerError):
    """Raised when a requested planner object does not exist."""


class ConflictError(PlannerError):
    """Raised when a request conflicts with existing planner data."""

