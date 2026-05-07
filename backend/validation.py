"""Small request validation helpers for the Flask API."""

from __future__ import annotations

from typing import Any, Dict, Iterable


class ValidationError(ValueError):
    """Raised when request payload validation fails."""


def require_json_object(data: Any) -> Dict:
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValidationError("request body must be a JSON object")
    return data


def require_string(data: Dict, key: str, *, allow_empty: bool = False, default: str | None = None) -> str | None:
    if key not in data:
        return default
    value = data.get(key)
    if not isinstance(value, str):
        raise ValidationError(f"{key} must be a string")
    if not allow_empty and not value.strip():
        raise ValidationError(f"{key} must be a non-empty string")
    return value


def require_bool(data: Dict, key: str, default: bool = False) -> bool:
    value = data.get(key, default)
    if isinstance(value, bool):
        return value
    raise ValidationError(f"{key} must be a boolean")


def require_list_of_strings(data: Dict, key: str, *, allow_missing: bool = False) -> list[str] | None:
    if key not in data:
        if allow_missing:
            return None
        raise ValidationError(f"missing {key}")
    value = data.get(key)
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        raise ValidationError(f"{key} must be a list of strings")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValidationError(f"all {key} entries must be non-empty strings")
    return value


def require_number(data: Dict, key: str, *, minimum: float | None = None, default: float | None = None) -> float | None:
    if key not in data:
        return default
    value = data.get(key)
    if not isinstance(value, (int, float)):
        raise ValidationError(f"{key} must be numeric")
    if minimum is not None and value < minimum:
        raise ValidationError(f"{key} must be >= {minimum}")
    return float(value)


def require_list_of_objects(data: Dict, key: str, *, allow_missing: bool = False) -> list[dict] | None:
    if key not in data:
        if allow_missing:
            return None
        raise ValidationError(f"missing {key}")
    value = data.get(key)
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValidationError(f"{key} must be a list of objects")
    return value


def ensure_allowed_keys(data: Dict, allowed: Iterable[str]) -> Dict:
    unknown = sorted(set(data) - set(allowed))
    if unknown:
        raise ValidationError(f"unknown keys: {', '.join(unknown)}")
    return data