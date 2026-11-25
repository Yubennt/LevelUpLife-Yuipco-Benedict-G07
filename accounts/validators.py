import re
import zoneinfo
from functools import lru_cache

from django.core.exceptions import ValidationError


class LetterAndNumberValidator:
    """BR-02: a password must contain at least one letter and one number."""

    def validate(self, password, user=None):
        if not re.search(r"[^\W\d_]", password) or not re.search(r"\d", password):
            raise ValidationError(
                "This password must contain at least one letter and one number.",
                code="password_no_letter_and_number",
            )

    def get_help_text(self):
        return "Your password must contain at least one letter and one number."


@lru_cache(maxsize=1)
def time_zone_names():
    return tuple(sorted(zoneinfo.available_timezones()))


def validate_time_zone(value):
    if value not in time_zone_names():
        raise ValidationError("Choose a valid time zone.", code="invalid_time_zone")
