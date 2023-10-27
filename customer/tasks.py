from django.contrib.sites.models import Site
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Bcc, From, To, Subject, Content
from winvillage.settings import SENDGRID_API_KEY, DEFAULT_FROM_EMAIL
from celery import shared_task


@shared_task
def send_marketing_email_to_mailing_list():
    message = Mail()
    message.from_email = From(
        email=DEFAULT_FROM_EMAIL, name=str(Site.objects.get_current().name)
    )
    message.to = To("micah@killianarts.online", name="Micah Killian")
    message.bcc = Bcc("mijokijo@gmail.com", name="This other Micah")
    message.subject = Subject("This is a test email from Winvillage.jp")
    message.content = Content(mime_type="text/html", content="This is test content")
    try:
        sendgrid_client = SendGridAPIClient(SENDGRID_API_KEY)
        response = sendgrid_client.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e.message)


@shared_task
def add(x, y):
    return x + y


@shared_task
def test_email():
    to_emails = [
        ("mijokijo@gmail.com", "Micah Killian"),
    ]
    message = Mail(
        from_email=(DEFAULT_FROM_EMAIL, "Winvillage.jp"),
        to_emails=to_emails,
        subject="Sending with Twilio SendGrid is Fun",
        html_content="<strong>and easy to do anywhere, even with Python</strong>",
    )
    try:
        sendgrid_client = SendGridAPIClient(SENDGRID_API_KEY)
        response = sendgrid_client.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e.message)
