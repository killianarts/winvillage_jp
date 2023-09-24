from django import forms
from django import template


register = template.Library()


@register.filter
def is_select(field):
    return isinstance(field.field.widget, forms.Select)


@register.filter
def is_required(field):
    return field.field.required


@register.filter
def is_multiple_select(field):
    return isinstance(field.field.widget, forms.SelectMultiple)


@register.filter
def is_textarea(field):
    return isinstance(field.field.widget, forms.Textarea)


@register.filter
def is_input(field):
    return isinstance(
        field.field.widget,
        (
            forms.TextInput,
            forms.NumberInput,
            forms.EmailInput,
            forms.PasswordInput,
            forms.URLInput,
        ),
    )


@register.filter
def is_checkbox(field):
    return isinstance(field.field.widget, forms.CheckboxInput)


@register.filter
def is_multiple_checkbox(field):
    return isinstance(field.field.widget, forms.CheckboxSelectMultiple)


@register.filter
def is_radio(field):
    return isinstance(field.field.widget, forms.RadioSelect)


@register.filter
def is_file(field):
    return isinstance(field.field.widget, forms.FileInput)


@register.filter
def is_date(field):
    return isinstance(field.field.widget, forms.DateInput)
