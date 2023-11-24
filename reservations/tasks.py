from celery import shared_task
from sendgrid import SendGridAPIClient, Mail
from django.utils.translation import gettext_lazy as _
from reservations.models import Reservation
from winvillage import settings


@shared_task
def send_confirmation_email(reservation_id):
    reservation = Reservation.objects.get(id=reservation_id)
    subject_text = _("Winvillage Reservation Confirmation For")
    message = Mail(
        from_email="noreply@winvillage.jp",
        to_emails=reservation.email,
        subject=f"{subject_text}, {reservation.last_name} {reservation.first_name}",
        html_content="This is some placeholder text",
    )
    sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
    response = sg.send(message)
    return response
