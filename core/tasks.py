import os

import environ
from celery import Celery, shared_task
from django_celery_results.models import TaskResult
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from sendgrid import Mail, SendGridAPIClient
from winvillage import settings

from reservations.models import Reservation

env = environ.Env()
app = Celery("winvillage")


@shared_task()
def run_task():
    print("running task")
    result = TaskResult.objects.create(
        task_id=run_task.request.id,
        status="SUCCESS",
        result="A task was run successfully",
    )
    return result
