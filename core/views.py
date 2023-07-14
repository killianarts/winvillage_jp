from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.views.decorators.http import require_GET


def index(request):
    return TemplateResponse(request, 'core/index.html')


@require_GET
def robots_txt(request):
    lines = [
        "User-Agent: *",
        "Disallow: /",
    ]
    return HttpResponse("\n".join(lines), content_type = "text/plain")
