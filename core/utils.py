import copy
from dataclasses import dataclass

from django.http.request import HttpRequest, QueryDict
from django.http.response import HttpResponse
from django_htmx.middleware import HtmxDetails

# from django.utils.functional import wraps
from render_block import render_block_to_string
from functools import wraps

from django.forms import Form
from reservations.models import Stay, Reservation, Order


# Taken from JustDjango's ecommerce project
# https://github.com/justdjango/django-simple-ecommerce/blob/22-fixes/cart/utils.py
def make_new_order(request):
    order = Order()
    order.save()
    request.session["order_id"] = order.id
    return order


def get_user_order(request):
    try:
        order = Order.objects.get(account=request.user, ordered=False)
    except Order.DoesNotExist:
        order = Order(account=request.user, ordered=False)
        order.save()
        request.session["order_id"] = order.id
    return order


def get_or_set_order_session(request):
    order_id = request.session.get("order_id", None)

    if not request.user.is_authenticated and order_id is None:
        order = make_new_order(request)
        return order
    elif not request.user.is_authenticated and order_id:
        order = Order.objects.get(id=order_id)
        return order

    if request.user.is_authenticated:
        order = get_user_order(request)
        return order


def make_new_reservation(request):
    stay = Stay.objects.create()
    reservation = Reservation.objects.create(stay=stay)
    request.session["reservation_id"] = reservation.id
    return reservation


def get_user_reservation(request):
    try:
        reservation = Reservation.objects.get(
            user=request.user, stay__status="not_reserved"
        )
    except Reservation.DoesNotExist:
        stay = Stay.objects.create(status="not_reserved")
        reservation = Reservation.objects.create(user=request.user, stay=stay)
        request.session["reservation_id"] = reservation.id
    return reservation


def get_or_set_reservation_session(request):
    reservation_id = request.session.get("reservation_id", None)

    if not request.user.is_authenticated and reservation_id is None:
        reservation = make_new_reservation(request)
        return reservation
    elif not request.user.is_authenticated and reservation_id:
        reservation = Reservation.objects.get(id=reservation_id)
        return reservation

    if request.user.is_authenticated:
        reservation = get_user_reservation(request)
        return reservation


# HTMX utilities


# Frpm django-htmx
@dataclass
class HtmxHttpRequest(HttpRequest):
    htmx: HtmxDetails


## Taken from Luke Plant's HTMX Patterns page: https://github.com/spookylukey/django-htmx-patterns/blob/master/code/htmx_patterns/utils.py
# This decorator combines a bunch of functionality, which you might not need all of!

# The names of parameters are chosen to make usage sound close to natural language:

# for htmx, if hx-target = "foo", then use block "bar"
# @for_htmx(if_hx_target="foo", use_block="bar")

# Future work for this decorator:

# - typing. You could use type hints and static typing checks to ensure that is only used
#   on view functions that return TemplateResponse


# - different ways of matching htmx requests, if needed.


def is_htmx(request: HttpRequest):
    return request.headers.get("Hx-Request", False)


def for_htmx(
    *,
    if_hx_target: str | None = None,
    use_template: str | None = None,
    use_block: str | list[str] | None = None,
    use_block_from_params: bool = False,
):
    """
    If the request is from htmx, then render a partial page, using either:
    - the template specified in `use_template` param
    - the block/blocks specified in `use_block` param
    - the block/blocks specified in GET/POST parameter "use_block", if `use_block_from_params=True` is passed
    If the optional `if_hx_target` parameter is supplied, the
    hx-target header must match the supplied value as well in order
    for this decorator to be applied.
    """
    if len([p for p in [use_block, use_template, use_block_from_params] if p]) != 1:
        raise ValueError(
            "You must pass exactly one of 'use_template', 'use_block' or 'use_block_from_params=True'"
        )

    def decorator(view):
        @wraps(view)
        def _view(request, *args, **kwargs):
            resp = view(request, *args, **kwargs)
            if is_htmx(request):
                if (
                    if_hx_target is None
                    or request.headers.get("Hx-Target", None) == if_hx_target
                ):
                    blocks_to_use = use_block
                    if not hasattr(resp, "render"):
                        raise ValueError(
                            "Cannot modify a response that isn't a TemplateResponse"
                        )
                    if resp.is_rendered:
                        raise ValueError(
                            "Cannot modify a response that has already been rendered"
                        )

                    if use_block_from_params:
                        use_block_from_params_val = _get_param_from_request(
                            request, "use_block"
                        )
                        if use_block_from_params_val is None:
                            return HttpResponse(
                                "No `use_block` in request params", status="400"
                            )

                        blocks_to_use = use_block_from_params_val

                    if use_template is not None:
                        resp.template_name = use_template
                    elif blocks_to_use is not None:
                        if not isinstance(blocks_to_use, list):
                            blocks_to_use = [blocks_to_use]

                        rendered_blocks = [
                            render_block_to_string(
                                resp.template_name,
                                b,
                                context=resp.context_data,
                                request=request,
                            )
                            for b in blocks_to_use
                        ]
                        # Create new simple HttpResponse as replacement
                        resp = HttpResponse(
                            content="".join(rendered_blocks),
                            status=resp.status_code,
                            headers=resp.headers,
                        )

            return resp

        return _view

    return decorator


def htmx_form_validate(*, form_class: type):
    """
    Instead of a normal view, just do htmx validation using the given form class,
    for a single field and return the single div that needs to be replaced.
    Normally the form class will be the same class used in the view body.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if (
                request.method == "GET"
                and "Hx-Request" in request.headers
                and (htmx_validation_field := request.GET.get("_validate_field", None))
            ):
                form = form_class(request.GET)
                form.is_valid()  # trigger validation
                return HttpResponse(
                    render_single_field_row(form, htmx_validation_field)
                )
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def render_single_field_row(form: Form, field_name: str):
    # Assumes form has renderer with `single_field_row_template` defined
    bound_field = form[field_name]
    return form.render(
        context={
            "field": bound_field,
            "errors": form.error_class(bound_field.errors, renderer=form.renderer),
            "do_htmx_validation": form.do_htmx_validation,
        },
        template_name=form.renderer.single_field_row_template,
    )


def _get_param_from_request(request, param):
    """
    Checks GET then POST params for specified param
    """
    if param in request.GET:
        return request.GET.getlist(param)
    elif request.method == "POST" and param in request.POST:
        return request.POST.getlist(param)
    return None


def make_get_request(request: HtmxHttpRequest) -> HtmxHttpRequest:
    """
    Returns a new GET request based on passed in request.
    :rtype: object
    """
    new_request = copy.copy(request)
    new_request.POST = QueryDict()
    new_request.method = "GET"
    return new_request
