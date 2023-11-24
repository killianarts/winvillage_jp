from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.views.decorators.http import require_GET
from django.contrib import messages
from django_htmx.http import HttpResponseClientRedirect

from core.utils import HtmxHttpRequest, for_htmx


def index(request):
    return TemplateResponse(request, "core/index.html")


@for_htmx(use_block="messages")
def get_messages(request: HtmxHttpRequest) -> HttpResponse:
    return TemplateResponse(
        request, "winadmin/base.html", {"messages": messages.get_messages(request)}
    )


def flush_session(request):
    url = request.path_info
    request.session.flush()
    return HttpResponse("Flushed")


@require_GET
def robots_txt(request):
    lines = [
        "User-Agent: *",
        "Disallow: /",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
