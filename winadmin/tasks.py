import json
import os

import environ
import pendulum
from celery import Celery, shared_task
from core.models import Procurement, Vendor
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_celery_results.models import TaskResult
from reservations.models import Reservation
from sendgrid import Mail, SendGridAPIClient, plain_text_content
from winvillage import settings

env = environ.Env()
app = Celery("winvillage")


@shared_task
def create_invoices_task():
    current_timezone = timezone.get_current_timezone()
    vendors = Vendor.objects.all()
    today = pendulum.today(tz=current_timezone)
    responses = []
    for vendor in vendors:
        this_month_cutoff_date = vendor.get_cutoff_date(today.year, today.month)
        last_month_cutoff_date = this_month_cutoff_date.subtract(months=1)
        if this_month_cutoff_date.date() == today.date():
            # TODO: Add procedure for vendors with a cutoff day but no procurements (and therefor nothing to invoice)
            procurements = Procurement.objects.filter(
                vendor=vendor,
                procured_on__range=(last_month_cutoff_date, this_month_cutoff_date),
            )
            invoice = vendor.create_invoice(this_month_cutoff_date, procurements)
            # TODO: Make email message with direct link to invoice.
            plain_text_content = render_to_string(
                "../templates/winadmin/email/invoice_report.txt",
                {
                    "invoice": invoice,
                    "invoice_period": {
                        "start": last_month_cutoff_date,
                        "end": this_month_cutoff_date,
                    },
                    "procurements": procurements,
                },
            )
            message = Mail(
                from_email="invoices@winvillage.jp",
                to_emails=settings.ADMINISTRATOR_EMAILS,
                subject=_("Invoice for %(vendor_name)s is ready")
                % {"vendor_name": vendor.name},
                plain_text_content=plain_text_content,
            )
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = sg.send(message)
            responses.append(response)
    return responses


@shared_task
def send_email():
    plain_text_content = render_to_string(
        "../templates/winadmin/email/invoice_report.txt", {}
    )
    message = Mail(
        from_email="invoices@winvillage.jp",
        to_emails=settings.ADMINISTRATOR_EMAILS,
        subject=_("Invoice for %(vendor_name)s is ready") % {"vendor_name": "Micah"},
        plain_text_content=plain_text_content,
    )
    sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
    response = sg.send(message)
