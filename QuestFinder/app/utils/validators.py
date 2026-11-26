"""Reusable WTForms validators."""
import re
from datetime import date

from flask import current_app
from wtforms.validators import ValidationError

from app.models.user import age_on

PH_MOBILE = re.compile(r"^09\d{9}$")


def adult_birthdate(form, field):
    """Strict 18+ rule. Also rejects dates in the future or absurdly old dates."""
    value: date | None = field.data
    if value is None:
        return
    today = date.today()
    if value > today:
        raise ValidationError("Birthdate cannot be in the future.")
    age = age_on(value, today)
    if age > 120:
        raise ValidationError("Enter a valid birthdate.")
    minimum = current_app.config["MINIMUM_AGE"]
    if age < minimum:
        raise ValidationError(f"QuestFinder is for users {minimum} years old and above only.")


def ph_mobile(form, field):
    if field.data:
        digits = re.sub(r"[\s-]", "", field.data)
        if digits.startswith("+63"):
            digits = "0" + digits[3:]
        if not PH_MOBILE.match(digits):
            raise ValidationError("Enter a valid mobile number, e.g. 09171234567.")
        field.data = digits


def strong_password(form, field):
    pw = field.data or ""
    if len(pw) < 8:
        raise ValidationError("Use at least 8 characters.")
    if not (re.search(r"[A-Za-z]", pw) and re.search(r"\d", pw)):
        raise ValidationError("Use both letters and numbers.")


def person_name(form, field):
    value = (field.data or "").strip()
    if not re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿÑñ .'-]{1,60}", value):
        raise ValidationError("Use letters, spaces, apostrophes or hyphens only.")
    field.data = " ".join(value.split())


def valid_email(form, field):
    """Email format check. `test_environment=True` accepts the demo @questfinder.test addresses."""
    from email_validator import EmailNotValidError, validate_email
    try:
        result = validate_email((field.data or "").strip(), check_deliverability=False, test_environment=True)
    except EmailNotValidError:
        raise ValidationError("Enter a valid email address.")
    field.data = result.normalized.lower()
