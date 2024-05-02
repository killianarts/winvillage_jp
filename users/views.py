from django.contrib import messages
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, RedirectView, UpdateView
from django_htmx.http import HttpResponseClientRedirect

from core.utils import htmx_form_validate, HtmxHttpRequest
from winadmin.forms import LoginForm

User = get_user_model()


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

    def get_success_url(self):
        assert self.request.user.is_authenticated  # for mypy to know that the user is authenticated
        return self.request.user.get_absolute_url()

    def get_object(self):
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse("users:detail", kwargs={"username": self.request.user.username})


user_redirect_view = UserRedirectView.as_view()


# def login_page(request: HtmxHttpRequest) -> HttpResponse:
#     if request.method != "POST":
#         form = LoginForm()
#         context = {"form": form}
#         return TemplateResponse(request, "winadmin/login_page.html", context)
#
#     form = LoginForm(request.POST)
#     if not form.is_valid():
#         context = {"form": form}
#         return TemplateResponse(request, "winadmin/login_page.html", context)
#
#     username = form.cleaned_data["username"]
#     password = form.cleaned_data["password"]
#     user = authenticate(request, username=username, password=password)
#     if user is None:
#         messages.error(request=request, message=_("There was an error logging in."))
#         context = {"form": form}
#         return TemplateResponse(request, "winadmin/login_page.html", context)
#
#     login(request, user)
#     return redirect("winadmin:index")


@htmx_form_validate(form_class=LoginForm)
def login_page(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                next_url = request.POST.get(
                    "next", reverse("winadmin:index")
                )  # Use 'dashboard' as the default next URL
                return HttpResponseClientRedirect(next_url)
            else:
                form.add_error(None, "Your username and password didn't match. Please try again.")
    else:
        form = LoginForm()
    return TemplateResponse(request, "winadmin/login_page.html", {"form": form})


@login_required()
def _logout(request: HtmxHttpRequest) -> HttpResponse:
    logout(request)
    return HttpResponseRedirect(reverse("winadmin:index"))
