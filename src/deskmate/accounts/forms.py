"""The sign-in form (ACC-1.1, ACC-1.3, ACC-1.7)."""

import unicodedata

from django import forms
from django.contrib.auth.forms import AuthenticationForm


class SignInForm(AuthenticationForm):
    """Django's sign-in form, matching usernames as ACC-1.7 says.

    The username is trimmed of Unicode whitespace, then normalised to NFKC
    whatever its length, so its length is measured after both (ACC-1.3).
    Every submission reaches the server, so the browser is told neither to
    require a field nor to limit the username's length.
    """

    username = forms.CharField()
    use_required_attribute = False

    def __init__(self, *args, **kwargs):
        """Make the form, without the length limit Django puts on the input."""
        super().__init__(*args, **kwargs)
        del self.fields["username"].widget.attrs["maxlength"]

    def clean_username(self):
        """Return the trimmed username in NFKC normal form."""
        return unicodedata.normalize("NFKC", self.cleaned_data["username"])
