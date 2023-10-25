from django.forms.renderers import TemplatesSetting


class TailwindFormRenderer(TemplatesSetting):
    form_template_name = "core/forms/tailwind/div.html"
    single_field_row_template = "core/forms/tailwind/field_row.html"


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
