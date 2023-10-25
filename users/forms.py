from django import forms
from django.contrib.auth import forms as admin_forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class UserAdminChangeForm(admin_forms.UserChangeForm):
    email = forms.EmailField()

    class Meta(admin_forms.UserChangeForm.Meta):
        model = User
        fields = ("email",)


class UserAdminCreationForm(admin_forms.UserCreationForm):
    """
    Form for User Creation in the Admin Area.
    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    email = forms.EmailField()

    class Meta:
        model = User
        fields = ("email",)
        error_messages = {
            "email": {"unique": _("This email has already been taken.")},
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user
