from celery import shared_task, Celery
from sendgrid import SendGridAPIClient, Mail
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
from reservations.models import Reservation
from winvillage import settings
import os

app = Celery("winvillage")
app.conf.update(
    BROKER_URL=os.environ["REDIS_URL"], CELERY_RESULT_BACKEND=os.environ["REDIS_URL"]
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
