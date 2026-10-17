"""The sign-in form (ACC-1.1, ACC-1.3, ACC-1.7)."""

from django.contrib.auth.forms import AuthenticationForm
from django.core.validators import MaxLengthValidator

# NFKC turns at most 4 characters into 1, so a username more than 4 times as
# long as an account's longest possible username cannot match any account.
_NFKC_LARGEST_SHRINK = 4


class SignInForm(AuthenticationForm):
    """Django's sign-in form, matching usernames as ACC-1.7 says.

    Django's username field trims Unicode whitespace, then applies NFKC, but
    only to input no longer than its `max_length`, because NFKC is slow on
    Windows for huge input (CVE-2023-46695). Here that limit is 4 times the
    longest username, so every username that could match is normalised and
    its length measured after NFKC (ACC-1.3). A longer one fails validation
    without being normalised, so it gets the same error as any other
    submission that matches no account.

    Every submission reaches the server, so the browser is told neither to
    require a field nor to limit the username's length.
    """

    # The id of the sign-in page's error, which describes both fields.
    error_id = "sign-in-error"
    use_required_attribute = False

    def __init__(self, *args, **kwargs):
        """Make the form, with the username limit above and none in the browser."""
        super().__init__(*args, **kwargs)
        username = self.fields["username"]
        username.max_length = _NFKC_LARGEST_SHRINK * self.username_field.max_length
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
