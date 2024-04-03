from celery import shared_task, Celery
from sendgrid import SendGridAPIClient, Mail
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
from reservations.models import Reservation
from winvillage import settings
import os
import environ

env = environ.Env()
app = Celery("winvillage")
app.conf.update(
    BROKER_URL=env("REDIS_URL", default="redis://127.0.0.1:6379/0"),
    CELERY_RESULT_BACKEND=env("REDIS_URL", default="redis://127.0.0.1:6379/0"),
)


@shared_task
def send_confirmation_email(reservation_id):
    reservation = Reservation.objects.get(id=reservation_id)
    subject_text = _("Winvillage Reservation Confirmation For")
    plain_text_content = render_to_string(
        "../templates/reservations/email/confirmation_email.txt",
        {"reservation": reservation},
    )
    message = Mail(
        from_email="noreply@winvillage.jp",
        to_emails=reservation.email,
        subject=_("Winvillage Reservation Confirmation For %(full_name)s")
        % {"full_name": reservation.get_full_name()},
        plain_text_content=plain_text_content,
    )
    sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
    response = sg.send(message)
    return response
