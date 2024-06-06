import os

import environ
from celery import Celery, shared_task
from django_celery_results.models import TaskResult
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from sendgrid import Mail, SendGridAPIClient
from winvillage import settings
import json
from reservations.models import Reservation

env = environ.Env()
app = Celery("winvillage")


@shared_task()
def send_confirmation_email(reservation_id):
    reservation = Reservation.objects.get(id=reservation_id)
    subject_text = _("Winvillage Reservation Confirmation For")
    plain_text_content = render_to_string(
        "../templates/reservations/email/confirmation_email.txt",
        {"reservation": reservation},
    )
    message = Mail(
        from_email="noreply@winvillage.jp",
        to_emails=reservation.customer.email,
        subject=_("Winvillage Reservation Confirmation For %(first_name)s")
        % {"first_name": reservation.customer.first_name},
        plain_text_content=plain_text_content,
    )
    sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
    response = sg.send(message)
    if 200 <= response.status_code < 300:
        task_result = TaskResult.objects.create(
            task_id=send_confirmation_email.request.id,
            status="SUCCESS",
            result="Email sent successfully.",
        )
        task_result.save()
    else:
        task_result = TaskResult.objects.create(
            task_id=send_confirmation_email.request.id,
            status="FAILURE",
            result=f"Failed to send email, status code: {response.status_code}",
        )
        task_result.save()
    return task_result
