import os
from flask import Flask, render_template, redirect, url_for, flash, session, request
from config import Config
from models import db, Appointment
from forms import BookingForm, DoctorLoginForm
from flask_mail import Mail, Message
from twilio.rest import Client
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import date, timedelta

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    mail = Mail(app)

    # Twilio client
    twilio_client = None
    if app.config.get("TWILIO_ACCOUNT_SID") and app.config.get("TWILIO_AUTH_TOKEN"):
        twilio_client = Client(app.config["TWILIO_ACCOUNT_SID"], app.config["TWILIO_AUTH_TOKEN"])

    # Create database tables
    with app.app_context():
        db.create_all()

    ##############################
    # ROUTES
    ##############################

    @app.route("/")
    def home():
        return render_template("home.html")

    @app.route("/book", methods=["GET", "POST"])
    def book():
        form = BookingForm()
        if form.validate_on_submit():
            appointment = Appointment(
                patient_name=form.patient_name.data,
                email=form.email.data,
                phone=form.phone.data,
                appointment_date=form.appointment_date.data,
                appointment_time=form.appointment_time.data,
                notes=form.notes.data
            )
            db.session.add(appointment)
            db.session.commit()

            # Email notification
            try:
                msg = Message("Appointment Received", recipients=[appointment.email])
                msg.body = (
                    f"Hi {appointment.patient_name},\n"
                    f"Your appointment for {appointment.appointment_date} at {appointment.appointment_time} has been booked.\n"
                    "Regards, Clinic Team"
                )
                mail.send(msg)
            except Exception as e:
                app.logger.warning("Email send failed: %s", e)

            # SMS notification
            if twilio_client and appointment.phone:
                try:
                    twilio_client.messages.create(
                        body=f"Appointment booked for {appointment.appointment_date} at {appointment.appointment_time}.",
                        from_=app.config["TWILIO_FROM_NUMBER"],
                        to=appointment.phone
                    )
                except Exception as e:
                    app.logger.warning("Twilio SMS failed: %s", e)

            return render_template("booking_success.html", appointment=appointment)
        return render_template("book_appointment.html", form=form)

    ##############################
    # DOCTOR LOGIN & DASHBOARD
    ##############################

    @app.route("/doctor/login", methods=["GET", "POST"])
    def doctor_login():
        form = DoctorLoginForm()
        if form.validate_on_submit():
            if (form.username.data == app.config["DOCTOR_USERNAME"] and
                form.password.data == app.config["DOCTOR_PASSWORD"]):
                session["doctor_logged_in"] = True
                return redirect(url_for("doctor_dashboard"))
            flash("Invalid credentials", "danger")
        return render_template("doctor_login.html", form=form)

    def doctor_required(func):
        from functools import wraps
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not session.get("doctor_logged_in"):
                return redirect(url_for("doctor_login"))
            return func(*args, **kwargs)
        return wrapper

    @app.route("/doctor/logout")
    def doctor_logout():
        session.pop("doctor_logged_in", None)
        return redirect(url_for("doctor_login"))

    @app.route("/doctor/dashboard")
    @doctor_required
    def doctor_dashboard():
        appointments = Appointment.query.order_by(Appointment.appointment_date, Appointment.appointment_time).all()
        return render_template("doctor_dashboard.html", appointments=appointments)

    ##############################
    # REMINDERS
    ##############################

    def send_reminders():
        """Send reminders for tomorrow's appointments automatically."""
        with app.app_context():
            tomorrow = date.today() + timedelta(days=1)
            appointments = Appointment.query.filter_by(appointment_date=tomorrow).all()
            for appt in appointments:
                try:
                    # Email reminder
                    msg = Message(
                        "Reminder: Appointment Tomorrow",
                        recipients=[appt.email]
                    )
                    msg.body = (
                        f"Hi {appt.patient_name},\n\n"
                        f"This is a reminder for your appointment tomorrow at {appt.appointment_time}.\n"
                        "Regards, Clinic Team"
                    )
                    mail.send(msg)
                except Exception as e:
                    app.logger.warning("Reminder email failed: %s", e)

                # SMS reminder
                if twilio_client and appt.phone:
                    try:
                        twilio_client.messages.create(
                            body=f"Reminder: Your appointment is tomorrow at {appt.appointment_time}.",
                            from_=app.config["TWILIO_FROM_NUMBER"],
                            to=appt.phone
                        )
                    except Exception as e:
                        app.logger.warning("Twilio reminder failed: %s", e)

    # Scheduler to send reminders daily
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=send_reminders, trigger="interval", hours=24)
    scheduler.start()

    import atexit
    atexit.register(lambda: scheduler.shutdown())

    # Route to view reminders manually
    @app.route("/doctor/reminders")
    @doctor_required
    def doctor_reminders():
        tomorrow = date.today() + timedelta(days=1)
        appointments = Appointment.query.filter_by(appointment_date=tomorrow).all()
        return render_template("doctor_reminders.html", appointments=appointments)

    return app


##############################
# RUN LOCAL
##############################
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
