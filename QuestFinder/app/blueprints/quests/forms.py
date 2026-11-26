from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import DecimalField, HiddenField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

DURATIONS = [(30, "30 mins"), (45, "45 mins"), (60, "1 hr"), (90, "1 hr 30 mins"), (120, "2 hrs"),
             (180, "3 hrs"), (240, "4 hrs"), (360, "6 hrs"), (480, "8 hrs (whole day)")]


class QuestForm(FlaskForm):
    # Prototype "Post (Client)" fields: Location, Work Description, Qualification, Offered Pay, Upload Photo.
    # Title and Duration are shown on the quest card / details screens, so they are asked here too.
    latitude = HiddenField(validators=[DataRequired(message="Set the quest location on the map.")])
    longitude = HiddenField(validators=[DataRequired(message="Set the quest location on the map.")])
    location_label = StringField("Location (landmark or street)",
                                 validators=[DataRequired(message="Describe where the quest is."), Length(max=255)])
    title = StringField("Quest title", validators=[DataRequired(), Length(min=3, max=80)])
    description = TextAreaField("Work description", validators=[DataRequired(), Length(min=10, max=2000)])
    qualification = TextAreaField("Qualification", validators=[DataRequired(), Length(min=3, max=1000)])
    pay = DecimalField("Offered pay", places=2,
                       validators=[DataRequired(message="Enter the pay in pesos."), NumberRange(min=1)])
    duration_minutes = SelectField("Estimated duration", coerce=int, choices=DURATIONS, default=60)
    photo = FileField("Upload photo", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"], "Images only.")])


class ApplyForm(FlaskForm):
    message = StringField("Message to the client (optional)", validators=[Optional(), Length(max=300)])
