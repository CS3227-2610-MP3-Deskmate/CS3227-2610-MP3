"""The sign-in form (ACC-1.1, ACC-1.3, ACC-1.7)."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.validators import ASCIIUsernameValidator
from django.core.validators import MaxLengthValidator


class SignInForm(AuthenticationForm):
    """Django's sign-in form with trimmed ASCII usernames (ACC-1.7).

    A plain CharField trims whitespace without Unicode normalisation.
    Every submission reaches the server, so the browser is told neither to
    require a field nor to limit the username's length.
    """

    username = forms.CharField(
        validators=[ASCIIUsernameValidator()],
        widget=forms.TextInput(
            attrs={
                "autofocus": True,
                "autocapitalize": "none",
                "autocomplete": "username",
            }
        ),
    )

    # The id of the sign-in page's error, which describes both fields.
    error_id = "sign-in-error"
    use_required_attribute = False

    def __init__(self, *args, **kwargs):
        """Apply the model's username length limit only on the server."""
        super().__init__(*args, **kwargs)
        username = self.fields["username"]
        username.validators.append(MaxLengthValidator(username.max_length))
        del username.widget.attrs["maxlength"]

    def full_clean(self):
        """Validate the form, then point both fields at its error, if it has one.

        Without this, Django points a field with an error at an element that
        the sign-in page does not have.
        """
        super().full_clean()
        if self.errors:
            for field in self.fields.values():
                field.widget.attrs["aria-describedby"] = self.error_id
