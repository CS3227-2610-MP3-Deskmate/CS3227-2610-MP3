"""Ticket validation and safe redisplay of rejected input (RQ-1.4)."""

from django import forms

from deskmate.tickets.models import Ticket

TITLE_ERROR = "Enter a valid title (1 to 200 characters)."
DESCRIPTION_ERROR = "Enter a valid description (1 to 10000 characters)."


def _errors(message):
    """Use one field error for missing, excessive or null-containing input."""
    return dict.fromkeys(
        ("required", "max_length", "null_characters_not_allowed"), message
    )


class _DescriptionField(forms.CharField):
    def to_python(self, value):
        """Normalise line endings before trimming and measuring the description."""
        if value is not None:
            value = value.replace("\r\n", "\n").replace("\r", "\n")
        return super().to_python(value)


class TicketForm(forms.ModelForm):
    """Validate both fields before creating a ticket in the current workspace."""

    title = forms.CharField(max_length=200, error_messages=_errors(TITLE_ERROR))
    description = _DescriptionField(
        max_length=10000,
        widget=forms.Textarea,
        error_messages=_errors(DESCRIPTION_ERROR),
    )

    class Meta:
        model = Ticket
        fields = ["title", "description"]

    def __init__(self, *args, **kwargs):
        """Leave Unicode code-point limits to the server, not UTF-16 widgets."""
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.pop("maxlength", None)

    def clean_title(self):
        """Refuse line breaks remaining after the title's surrounding whitespace."""
        title = self.cleaned_data["title"]
        if "\r" in title or "\n" in title:
            raise forms.ValidationError(TITLE_ERROR)
        return title

    def redisplay(self):
        """Make rejected values displayable without changing validation or storage."""
        if self.is_bound:
            self.data = self.data.copy()
            for name in ("title", "description"):
                value = self.data.get(name, "").replace("\x00", "\ufffd")
                value = value.replace("\r\n", "\n").replace("\r", "\n")
                self.data[name] = value.replace("\n", " ") if name == "title" else value
        return self
