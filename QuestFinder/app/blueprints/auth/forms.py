from flask_wtf import FlaskForm
from wtforms import BooleanField, DateField, EmailField, PasswordField, StringField
from wtforms.validators import DataRequired, EqualTo, Length, Optional

from app.utils.validators import adult_birthdate, person_name, ph_mobile, strong_password, valid_email


class RegisterForm(FlaskForm):
    first_name = StringField("First name", validators=[DataRequired(), Length(max=60), person_name])
    last_name = StringField("Last name", validators=[DataRequired(), Length(max=60), person_name])
    email = EmailField("Email", validators=[DataRequired(), Length(max=255), valid_email])
    phone = StringField("Mobile number", validators=[Optional(), ph_mobile])
    birthdate = DateField("Birthdate", validators=[DataRequired(message="Enter your birthdate."), adult_birthdate])
    password = PasswordField("Password", validators=[DataRequired(), strong_password])
    confirm = PasswordField("Confirm password",
                            validators=[DataRequired(), EqualTo("password", message="Passwords do not match.")])
    agree = BooleanField("I am 18 years old or above and I agree to verify my identity with a valid ID.",
                         validators=[DataRequired(message="You must confirm this to continue.")])


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), valid_email])
    password = PasswordField("Password", validators=[DataRequired()])
