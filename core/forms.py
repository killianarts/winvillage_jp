from django.forms.renderers import TemplatesSetting
from django.forms import DateTimeField
from django.utils import timezone
import pendulum
from pendulum.parsing.exceptions import ParserError
from django.core import exceptions
import datetime


class PendulumField(DateTimeField):
    def prepare_value(self, value):
        return value.to_datetime_string()

    #
    # def to_python(self, value):
    #     if value is None:
    #         return value
    #     if isinstance(value, pendulum.DateTime):
    #         return value
    #     if isinstance(value, datetime.datetime):
    #         return pendulum.instance(value)
    #     if isinstance(value, datetime.date):
    #         return pendulum.instance(datetime.datetime.combine(value, datetime.datetime.min.time()))
    #     try:
    #         return pendulum.parse(value, tz=timezone.get_current_timezone())
    #     except ParserError:
    #         raise exceptions.ValidationError(
    #             self.error_messages["invalid_datetime"],
    #             code="invalid_datetime",
    #             params={"value": value},
    #         )
    #
    # def strptime(self, value, format):
    #     return pendulum.from_format(value, format, timezone.get_current_timezone())


class TailwindFormRenderer(TemplatesSetting):
    form_template_name = "core/forms/tailwind/div.html"
    single_field_row_template = "core/forms/tailwind/field_row.html"


class ReadOnlyFormRenderer(TemplatesSetting):
    form_template_name = "core/forms/tailwind/div.html"
    formset_template_name = "core/forms/formsets/div.html"
    single_field_row_template = "core/forms/tailwind/field_row_read_only.html"
    field_template_name = "core/forms/tailwind/field_row_read_only.html"


class TailwindFormMixin:
    default_renderer = TailwindFormRenderer()
    do_htmx_validation = False

    # def __init__(self, *args, **kwargs) -> None:
    # We don’t want ':' as a label suffix:
    # return super().__init__(*args, label_suffix="", **kwargs)

    def get_context(self, *args, **kwargs):
        return super().get_context(*args, **kwargs) | {
            "do_htmx_validation": self.do_htmx_validation,
            "single_field_row_template": self.renderer.single_field_row_template,
        }


class ReadOnlyFormMixin:
    default_renderer = ReadOnlyFormRenderer()

    # def __init__(self, *args, **kwargs) -> None:
    # We don’t want ':' as a label suffix:
    # return super().__init__(*args, label_suffix="", **kwargs)

    def get_context(self, *args, **kwargs):
        return super().get_context(*args, **kwargs) | {
            "single_field_row_template": self.renderer.single_field_row_template,
        }


class ReservationsContactInformationFormRenderer(TemplatesSetting):
    form_template_name = "core/forms/tailwind/div.html"
    single_field_row_template = "core/forms/reservations/field_row.html"


class ReservationsContactInformationFormMixin:
    default_renderer = ReservationsContactInformationFormRenderer()
    do_htmx_validation = False

    # def __init__(self, *args, **kwargs) -> None:
    # We don’t want ':' as a label suffix:
    # return super().__init__(*args, label_suffix="", **kwargs)

    def get_context(self, *args, **kwargs):
        return super().get_context(*args, **kwargs) | {
            "do_htmx_validation": self.do_htmx_validation,
            "single_field_row_template": self.renderer.single_field_row_template,
        }
