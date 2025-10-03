from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateField, SelectField, TextAreaField, PasswordField
from wtforms.validators import DataRequired, Email

class BookingForm(FlaskForm):
    patient_name = StringField("Full Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    phone = StringField("Phone Number")
    appointment_date = DateField("Date", validators=[DataRequired()])
    appointment_time = SelectField("Time Slot", choices=[
        ("09:00 AM", "09:00 AM"), ("10:00 AM", "10:00 AM"), ("11:00 AM", "11:00 AM"),
        ("02:00 PM", "02:00 PM"), ("03:00 PM", "03:00 PM"), ("04:00 PM", "04:00 PM")
    ], validators=[DataRequired()])
    notes = TextAreaField("Notes (Optional)")
    submit = SubmitField("Book Appointment")

class DoctorLoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")
