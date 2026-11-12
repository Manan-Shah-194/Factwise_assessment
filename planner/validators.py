"""Validation helpers used by the planner API implementations."""

from .exceptions import ValidationError


def required_string(payload, field, maximum_length):
    value = payload.get(field)
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string")

    value = value.strip()
    if not value:
        raise ValidationError(f"{field} cannot be empty")
    if len(value) > maximum_length:
        raise ValidationError(f"{field} cannot be longer than {maximum_length} characters")
    return value


def optional_string(payload, field, maximum_length):
    value = payload.get(field, "")
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string")

    value = value.strip()
    if len(value) > maximum_length:
        raise ValidationError(f"{field} cannot be longer than {maximum_length} characters")
    return value


def required_field(payload, field):
    if field not in payload or payload[field] in (None, ""):
        raise ValidationError(f"{field} is required")
    return payload[field]


def required_list(payload, field, maximum_length=None):
    value = required_field(payload, field)
    if not isinstance(value, list):
        raise ValidationError(f"{field} must be a list")
    if maximum_length is not None and len(value) > maximum_length:
        raise ValidationError(f"{field} cannot contain more than {maximum_length} items")
    return value

