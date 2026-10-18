"""Article validation and safe redisplay of rejected input (KB-1.4, KB-1.5)."""

from django import forms

from deskmate.knowledge.models import Article

TITLE_ERROR = "Enter a valid title (1 to 200 characters)."
BODY_ERROR = "Enter a valid body (1 to 10000 characters)."
DUPLICATE = "An article with this title already exists."


def _errors(message):
    """Use one field error for missing, excessive or null-containing input."""
    return dict.fromkeys(
        ("required", "max_length", "null_characters_not_allowed"), message
    )


class _BodyField(forms.CharField):
    def to_python(self, value):
        """Normalise line endings before trimming and measuring the body."""
        if value is not None:
            value = value.replace("\r\n", "\n").replace("\r", "\n")
        return super().to_python(value)


class ArticleForm(forms.ModelForm):
    """Validate both fields before checking the current workspace's titles."""

    title = forms.CharField(max_length=200, error_messages=_errors(TITLE_ERROR))
    body = _BodyField(
        max_length=10000, widget=forms.Textarea, error_messages=_errors(BODY_ERROR)
    )

    class Meta:
        model = Article
        fields = ["title", "body"]

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

    def clean(self):
        """Exclude this article when checking otherwise valid title/body pairs."""
        cleaned = super().clean()
        if not self.errors:
            duplicates = Article.objects.filter(
                workspace_id=self.instance.workspace_id,
                title_key=cleaned["title"].casefold(),
            ).exclude(pk=self.instance.pk)
            if duplicates.exists():
                self.add_error("title", DUPLICATE)
        return cleaned

    def redisplay(self):
        """Make rejected values displayable without changing validation or storage."""
        if self.is_bound:
            self.data = self.data.copy()
            for name in ("title", "body"):
                value = self.data.get(name, "").replace("\x00", "\ufffd")
                value = value.replace("\r\n", "\n").replace("\r", "\n")
                self.data[name] = value.replace("\n", " ") if name == "title" else value
        return self
