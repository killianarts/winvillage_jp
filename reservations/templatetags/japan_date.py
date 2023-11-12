from django import template
from django.utils import formats, translation

register = template.Library()


@register.filter
def japan_date(value):
    with translation.override("ja"):
        return formats.date_format(value, "Y年F")
