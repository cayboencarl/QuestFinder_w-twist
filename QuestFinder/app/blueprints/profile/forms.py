from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import PasswordField, SelectMultipleField, StringField, TextAreaField
from wtforms.validators import DataRequired, EqualTo, Length, Optional, ValidationError

from app.utils import skills as skill_list
from app.utils.validators import person_name, ph_mobile, strong_password


def _skill_limit(form, field):
    if len(field.data or []) > skill_list.MAX_SKILLS:
        raise ValidationError(f"Choose up to {skill_list.MAX_SKILLS} skills.")
    if len(skill_list.join(field.data or []) or "") > 255:
        raise ValidationError("Too many skills selected. Remove one or two.")


class ProfileForm(FlaskForm):
    first_name = StringField("First name", validators=[DataRequired(), Length(max=60), person_name])
    last_name = StringField("Last name", validators=[DataRequired(), Length(max=60), person_name])
    phone = StringField("Mobile number", validators=[Optional(), ph_mobile])
    skills = SelectMultipleField("Skills", choices=[(s, s) for s in skill_list.ALL_SKILLS],
                                 validators=[Optional(), _skill_limit])
    bio = TextAreaField("About me", validators=[Optional(), Length(max=500)])
    avatar = FileField("Profile photo", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"], "Images only.")])


class PasswordForm(FlaskForm):
    current = PasswordField("Current password", validators=[DataRequired()])
    new = PasswordField("New password", validators=[DataRequired(), strong_password])
    confirm = PasswordField("Confirm new password",
                            validators=[DataRequired(), EqualTo("new", message="Passwords do not match.")])
