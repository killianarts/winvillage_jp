from django.contrib import messages
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.views.decorators.http import require_GET

from core.utils import HtmxHttpRequest, for_htmx
from core.tasks import run_task


def index(request):
    return TemplateResponse(request, "core/index.html")


def room_details(request: HtmxHttpRequest) -> HttpResponse:
    return TemplateResponse(request, "core/room_details.html")


@for_htmx(use_block="messages")
def get_messages(request: HtmxHttpRequest) -> HttpResponse:
    return TemplateResponse(
        request, "winadmin/base.html", {"messages": messages.get_messages(request)}
    )


def flush_session(request):
    url = request.path_info
    request.session.flush()
    return HttpResponse("Flushed")


def test(request):
    response = run_task.delay()
    return HttpResponse(response)


def components(request):
    return TemplateResponse(request, "core/components.html")


# If you want to completely block search engines,
# you need to set the <meta name="robots" content="noindex, nofollow" /> tag in your base.html file.
# See: https://support.google.com/webmasters/answer/7489871?hl=en#zippy=%2Cthis-is-my-site%2Cthe-page-is-blocked-by-robotstxt

# @require_GET
# def robots_txt(request):
#     lines = [
#         "User-Agent: *",
#         "Disallow: /",
#     ]
#     return HttpResponse("\n".join(lines), content_type="text/plain")
