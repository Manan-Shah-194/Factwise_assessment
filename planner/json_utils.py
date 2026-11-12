"""Small JSON helpers shared by the concrete API classes."""

import json

from .exceptions import InvalidRequestError


def parse_request(request):
    """Parse a JSON object request and reject anything else."""
    if not isinstance(request, str):
        raise InvalidRequestError("request must be a JSON string")

    try:
        payload = json.loads(request)
    except (TypeError, json.JSONDecodeError) as exc:
        raise InvalidRequestError("request must contain valid JSON") from exc

    if not isinstance(payload, dict):
        raise InvalidRequestError("request JSON must contain an object")

    return payload


def response(data):
    """Serialize an API response using stable, readable JSON."""
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)

