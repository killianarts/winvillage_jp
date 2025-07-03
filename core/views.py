from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.views.decorators.http import require_GET
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import check_for_language

from django.urls import translate_url
from django.conf import settings
from urllib.parse import urlsplit

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


# def flush_session(request):
#     try:
#         del request.session["reservation_id"]
#     except KeyError:
#         pass
#     return HttpResponse("Reservation ID Deleted")


def test(request):
    return TemplateResponse(request, "core/svg_test.html")

LANGUAGE_QUERY_PARAMETER = "language"
def set_language(request):
    """
    Modified version of Django's set_language built-in.

    Redirect to a given URL while setting the chosen language in the session
    (if enabled) and in a cookie. The URL and the language code need to be
    specified in the request parameters.

    Since this view changes how the user will see the rest of the site, it must
    only be accessed as a POST request. If called as a GET request, it will
    redirect to the page in the request (the 'next' parameter) without changing
    any state.
    """
    next_url = request.POST.get("next", request.GET.get("next"))

    if (
            next_url or request.accepts("text/html")
    ) and not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = request.META.get("HTTP_REFERER")
        if not url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
        ):
            next_url = "/"

    # If next_url is set to the HTTP_REFERER, it will include the url scheme and host.
    # Let's grab the path so we can strip the language prefix.
    next_url = urlsplit(next_url).path
    # Strip out the language code from the url before translating the url.
    for lang_code, lang_name in settings.LANGUAGES:
        prefix = '/' + lang_code
        if next_url.startswith(prefix):
            next_url = next_url[len(prefix):]
            break

    response = HttpResponseRedirect(next_url) if next_url else HttpResponse(status=204)
    if request.method == "POST":
        lang_code = request.POST.get(LANGUAGE_QUERY_PARAMETER)
        if lang_code and check_for_language(lang_code):
            if next_url:
                next_trans = translate_url(next_url, lang_code)
                if next_trans != next_url:
                    response = HttpResponseRedirect(next_trans)
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME,
                lang_code,
                max_age=settings.LANGUAGE_COOKIE_AGE,
                path=settings.LANGUAGE_COOKIE_PATH,
                domain=settings.LANGUAGE_COOKIE_DOMAIN,
                secure=settings.LANGUAGE_COOKIE_SECURE,
                httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
                samesite=settings.LANGUAGE_COOKIE_SAMESITE,
            )
    return response


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
