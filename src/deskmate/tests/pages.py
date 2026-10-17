"""Reads Deskmate's HTML pages as a browser would, and submits their forms.

Tests use it to check what a page shows, such as its title, headings, text and
the fields of its forms that a `for` attribute labels, and to send a form as a
browser sends it. It reads only what Deskmate's pages use, so it does not
handle checkboxes, radio buttons, image buttons or labels that wrap their
field. It uses only the standard library's HTML parser, so it needs no
dependency.
"""

from html.parser import HTMLParser
from urllib.parse import urlencode, urljoin, urlsplit

from deskmate.tests.helpers import media_type

# The host name Django's test client sends, and the origin of Deskmate's pages
# as a browser sees them in production, where they are served over HTTPS.
SITE = "testserver"
ORIGIN = f"https://{SITE}"
# The name Django gives the hidden field that holds a form's CSRF token.
CSRF_FIELD = "csrfmiddlewaretoken"

_HEADINGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
# Tags whose text runs on into the text around them, as in a browser. Every
# other tag separates the text before it from the text after it.
_INLINE = frozenset(
    {
        "a",
        "abbr",
        "b",
        "bdi",
        "bdo",
        "cite",
        "code",
        "data",
        "dfn",
        "em",
        "i",
        "kbd",
        "mark",
        "q",
        "s",
        "samp",
        "small",
        "span",
        "strong",
        "sub",
        "sup",
        "time",
        "u",
        "var",
        "wbr",
    }
)
# Input types whose value a browser does not send as part of a form's data.
_NOT_SENT = frozenset({"submit", "button", "reset", "image", "file"})


def normalise(text):
    """Return `text` with each run of whitespace made one space, and trimmed."""
    return " ".join(text.split())


class Control:
    """An input or button on a page, with the attributes a browser reads."""

    def __init__(self, tag, attributes, form):
        self.tag = tag
        default_type = "submit" if tag == "button" else "text"
        self.type = (attributes.get("type") or default_type).lower()
        self.name = attributes.get("name")
        self.value = attributes.get("value")
        self.id = attributes.get("id")
        self.form = form
        self.parts = []

    @property
    def caption(self):
        """Return the text a user sees on this control as a button."""
        if self.tag == "button":
            return normalise("".join(self.parts))
        return normalise(self.value or "")

    def is_button(self):
        """Return whether pressing this control submits its form."""
        return self.type == "submit"

    def is_field(self):
        """Return whether this control is a field a user types into."""
        return self.tag == "input" and self.type not in _NOT_SENT | {"hidden"}

    def is_sent(self):
        """Return whether a browser sends this control's value with its form."""
        return self.tag == "input" and bool(self.name) and self.type not in _NOT_SENT


class Form:
    """A form on a page: where and how it is sent, its controls and labels."""

    def __init__(self, page_url, attributes):
        self.page_url = page_url
        self.method = (attributes.get("method") or "get").lower()
        self.action = attributes.get("action") or ""
        self.controls = []
        self.labels = []

    @property
    def url(self):
        """Return the absolute URL the form is sent to, as a browser works it out."""
        return urljoin(self.page_url, self.action)

    @property
    def path(self):
        """Return the path the form is sent to, without its query."""
        return urlsplit(self.url).path

    def field(self, label):
        """Return the one field of this form whose label reads exactly `label`."""
        fields = [
            control
            for text, control in self.labels
            if text == label and control.is_field()
        ]
        labels = [text for text, _ in self.labels]
        assert len(fields) == 1, (
            f"Expected one field labelled {label!r}; the form's labels are {labels}."
        )
        return fields[0]

    def button(self, caption):
        """Return the one button of this form that reads exactly `caption`."""
        buttons = [
            control
            for control in self.controls
            if control.is_button() and control.caption == caption
        ]
        assert len(buttons) == 1, f"Expected one {caption!r} button in the form."
        return buttons[0]

    def submit(
        self,
        client,
        typed=None,
        *,
        button=None,
        changes=None,
        query=None,
        headers=None,
        secure=False,
    ):
        """Send this form from `client` as a browser would; return the response.

        `typed` maps a field's label to what the user typed into it, and
        `button` is the caption of the button they pressed. `changes` maps a
        control's name to a value that replaces the page's, or to None to leave
        the control out, as a forged or tampered request would; names that are
        not on the page are added. `query` is added to the URL's query. The
        request carries `Origin: https://testserver` unless `headers` replaces
        it, and is sent over HTTPS if `secure` is true. Only POST forms are
        supported, because every form the specs name is one.
        """
        assert self.method == "post", f"The form's method is {self.method!r}."
        data = {
            control.name: control.value or ""
            for control in self.controls
            if control.is_sent()
        }
        for label, value in (typed or {}).items():
            data[self.field(label).name] = value
        if button is not None:
            pressed = self.button(button)
            if pressed.name:
                data[pressed.name] = pressed.value or ""
        for name, value in (changes or {}).items():
            if value is None:
                data.pop(name, None)
            else:
                data[name] = value
        url = urlsplit(self.url)
        assert url.netloc == SITE, f"The form is sent to another site: {self.url}"
        query_string = "&".join(
            part for part in (url.query, urlencode(query or {})) if part
        )
        target = url.path + (f"?{query_string}" if query_string else "")
        return client.post(
            target,
            urlencode(data),
            content_type="application/x-www-form-urlencoded",
            secure=secure,
            headers={"Origin": ORIGIN, **(headers or {})},
        )


class Page:
    """An HTML page from a test client's response, read as a browser reads it."""

    def __init__(self, response):
        assert media_type(response) == "text/html", (
            f"Expected an HTML page, got {response['Content-Type']!r}."
        )
        self.url = response.wsgi_request.build_absolute_uri()
        parser = _Parser(self.url)
        parser.feed(response.content.decode(response.charset or "utf-8"))
        parser.close()
        self.title = normalise("".join(parser.titles[0])) if parser.titles else None
        self.headings = [
            (tag, normalise("".join(parts))) for tag, parts in parser.headings
        ]
        self.text = normalise("".join(parser.text))
        self.forms = parser.forms
        self.controls = parser.controls

    @property
    def h1s(self):
        """Return the text of each top-level heading, in order."""
        return [text for tag, text in self.headings if tag == "h1"]

    @property
    def heading_texts(self):
        """Return the text of each heading of any level, in order."""
        return [text for _, text in self.headings]

    def form_with_button(self, caption):
        """Return the one form on the page with a button reading `caption`."""
        forms = [
            form
            for form in self.forms
            if any(
                control.is_button() and control.caption == caption
                for control in form.controls
            )
        ]
        assert len(forms) == 1, f"Expected one form with a {caption!r} button."
        return forms[0]

    def csrf_tokens(self):
        """Return the CSRF token of every form on the page that has one."""
        return [
            control.value
            for control in self.controls
            if control.name == CSRF_FIELD and control.value
        ]

    def csrf_token(self):
        """Return the CSRF token of the page's first form that has one."""
        tokens = self.csrf_tokens()
        assert tokens, f"The page at {self.url} has no form with a CSRF token."
        return tokens[0]


class _Label:
    def __init__(self, for_id):
        self.for_id = for_id
        self.parts = []


class _Parser(HTMLParser):
    """Collects a page's text, title, headings, forms, controls and labels."""

    def __init__(self, url):
        super().__init__(convert_charrefs=True)
        self.url = url
        self.text = []
        self.titles = []
        self.headings = []
        self.forms = []
        self.controls = []
        self.labels = []
        self._open = []
        self._form = None

    def handle_starttag(self, tag, attrs):
        """Record an element as it opens; a browser uses an attribute's first value."""
        attributes = {}
        for name, value in attrs:
            attributes.setdefault(name, "" if value is None else value)
        if tag not in _INLINE:
            self.handle_data(" ")
        if tag == "form":
            self._form = Form(self.url, attributes)
            self.forms.append(self._form)
        elif tag in ("input", "button"):
            self._add_control(tag, attributes)
        elif tag == "label":
            label = _Label(attributes.get("for"))
            self.labels.append(label)
            self._open.append((tag, label.parts))
        elif tag == "title":
            self.titles.append([])
            self._open.append((tag, self.titles[-1]))
        elif tag in _HEADINGS:
            self.headings.append((tag, []))
            self._open.append((tag, self.headings[-1][1]))

    def _add_control(self, tag, attributes):
        control = Control(tag, attributes, self._form)
        self.controls.append(control)
        if self._form is not None:
            self._form.controls.append(control)
        if tag == "button":
            self._open.append((tag, control.parts))

    def handle_endtag(self, tag):
        """Record an element as it closes."""
        if tag not in _INLINE:
            self.handle_data(" ")
        if tag == "form":
            self._form = None
        for index in range(len(self._open) - 1, -1, -1):
            if self._open[index][0] == tag:
                del self._open[index]
                break

    def handle_data(self, data):
        """Add text to the page and to every open element whose text is kept."""
        self.text.append(data)
        for _, parts in self._open:
            parts.append(data)

    def close(self):
        """Finish the page, then give each label the control its `for` names."""
        super().close()
        by_id = {}
        for control in self.controls:
            if control.id:
                by_id.setdefault(control.id, control)
        for label in self.labels:
            control = by_id.get(label.for_id)
            if control is not None and control.form is not None:
                control.form.labels.append((normalise("".join(label.parts)), control))
