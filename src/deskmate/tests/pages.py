"""Reads Deskmate's HTML pages as a browser would, and submits their forms.

Tests use it to check what a page shows, such as its title, headings, text,
tables, links and the fields of its forms that a `for` attribute labels, and to
send a form as a browser sends it. It reads only what Deskmate's pages use, so
it does not handle checkboxes, radio buttons, image buttons, labels that wrap
their field or tables inside tables. It uses only the standard library's HTML
parser, so it needs no dependency.
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
# Input types that a browser shows as a button.
_BUTTON_TYPES = frozenset({"submit", "button", "reset", "image"})
# The cells of a table row.
_CELLS = frozenset({"th", "td"})


def normalise(text):
    """Return `text` with each run of whitespace made one space, and trimmed."""
    return " ".join(text.split())


class Control:
    """An input, textarea or button, with the attributes a browser reads."""

    def __init__(self, tag, attributes, form):
        self.tag = tag
        default_type = "submit" if tag == "button" else "text"
        self.type = (attributes.get("type") or default_type).lower()
        self.name = attributes.get("name")
        self.value = attributes.get("value", "")
        self.formaction = attributes.get("formaction")
        self.id = attributes.get("id")
        # Whether the browser refuses to send the form while the control is
        # empty, and the most characters it lets a user type, or None.
        self.required = "required" in attributes
        self.maxlength = attributes.get("maxlength")
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

    def looks_like_button(self):
        """Return whether a browser shows this control as a button of any kind."""
        return self.tag == "button" or self.type in _BUTTON_TYPES

    def is_field(self):
        """Return whether this control is a field a user types into."""
        return self.tag == "textarea" or (
            self.tag == "input" and self.type not in _NOT_SENT | {"hidden"}
        )

    def is_sent(self):
        """Return whether a browser sends this control's value with its form."""
        return (
            self.tag in ("input", "textarea")
            and bool(self.name)
            and self.type not in _NOT_SENT
        )


class Form:
    """A form on a page: where and how it is sent, its controls and labels.

    `text_after` is the page's text after the form ends, with whitespace
    normalised.
    """

    def __init__(self, page_url, attributes):
        self.page_url = page_url
        self.method = (attributes.get("method") or "get").lower()
        self.action = attributes.get("action") or ""
        self.controls = []
        self.labels = []
        self.text_after = ""
        # Where the form's text ends among the parser's text parts.
        self.text_end = None

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

    def data(self, typed=None, *, button=None, changes=None):
        """Return the fields a browser sends with this form, by name.

        `typed` maps a field's label to what the user typed into it, and
        `button` is the caption of the button they pressed. `changes` maps a
        control's name to a value that replaces the page's, or to None to leave
        the control out, as a forged or tampered request would; names that are
        not on the page are added.
        """
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
        return data

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
        environ=None,
    ):
        """Send this form from `client` as a browser would; return the response.

        `typed`, `button` and `changes` are those of `data`. `query` is added
        to the URL's query. The request carries `Origin: https://testserver`
        unless `headers` replaces it, and is sent over HTTPS if `secure` is
        true. `environ` sets WSGI variables that are not headers, such as
        REMOTE_ADDR, the address the connection came from. Only POST forms are
        supported, because every form the specs name is one.
        """
        assert self.method == "post", f"The form's method is {self.method!r}."
        data = self.data(typed, button=button, changes=changes)
        pressed = self.button(button) if button is not None else None
        action = (
            urljoin(self.page_url, pressed.formaction)
            if pressed is not None and pressed.formaction
            else self.url
        )
        url = urlsplit(action)
        assert url.netloc == SITE, f"The form is sent to another site: {action}"
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
            **(environ or {}),
        )


class Page:
    """An HTML page from a test client's response, read as a browser reads it.

    `tables` holds each table as a list of rows, and each row as a list of
    `(tag, text)` cells, where the tag is `th` or `td`. `links` holds each link
    as `(text, url)`, with the URL made absolute as a browser makes it.
    """

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
        self.tables = [
            [[(tag, normalise("".join(parts))) for tag, parts in row] for row in rows]
            for rows in parser.tables
        ]
        self.links = [
            (normalise("".join(parts)), urljoin(self.url, href))
            for href, parts in parser.links
        ]

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
    """Collects a page's text, title, headings, forms, controls, labels, tables
    and links."""

    def __init__(self, url):
        super().__init__(convert_charrefs=True)
        self.url = url
        self.text = []
        self.titles = []
        self.headings = []
        self.forms = []
        self.controls = []
        self.labels = []
        self.tables = []
        self.links = []
        self._open = []
        self._form = None
        # Elements whose contents a browser does not show as page text.
        self._hidden = 0

    def handle_starttag(self, tag, attrs):
        """Record an element as it opens; a browser uses an attribute's first value."""
        attributes = {}
        for name, value in attrs:
            attributes.setdefault(name, "" if value is None else value)
        if tag in ("style", "script", "template"):
            self._hidden += 1
            return
        if self._hidden:
            return
        if tag not in _INLINE:
            self.handle_data(" ")
        if tag == "form":
            self._form = Form(self.url, attributes)
            self.forms.append(self._form)
        elif tag == "table":
            self.tables.append([])
        elif tag == "tr" and self.tables:
            # A new row ends the cell before it, even if its end tag is left out.
            self._close(_CELLS)
            self.tables[-1].append([])
        elif tag in _CELLS and self.tables and self.tables[-1]:
            self._close(_CELLS)
            cell = (tag, [])
            self.tables[-1][-1].append(cell)
            self._open.append((tag, cell[1]))
        elif tag == "a" and "href" in attributes:
            link = (attributes["href"], [])
            self.links.append(link)
            self._open.append((tag, link[1]))
        elif tag in ("input", "button", "textarea"):
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
        if tag in ("button", "textarea"):
            self._open.append((tag, control.parts))

    def handle_endtag(self, tag):
        """Record an element as it closes."""
        if tag in ("style", "script", "template"):
            self._hidden = max(0, self._hidden - 1)
            return
        if self._hidden:
            return
        if tag == "textarea":
            control = self.controls[-1]
            control.value = (
                "".join(control.parts)
                .replace("\r\n", "\n")
                .replace("\r", "\n")
                .removeprefix("\n")
            )
        if tag not in _INLINE:
            self.handle_data(" ")
        if tag == "form" and self._form is not None:
            self._form.text_end = len(self.text)
            self._form = None
        if tag in ("tr", "table"):
            self._close(_CELLS)
        for index in range(len(self._open) - 1, -1, -1):
            if self._open[index][0] == tag:
                del self._open[index]
                break

    def _close(self, tags):
        """Stop collecting text for every open element whose tag is in `tags`."""
        self._open = [(tag, parts) for tag, parts in self._open if tag not in tags]

    def handle_data(self, data):
        """Add text to the page and to every open element whose text is kept."""
        if self._hidden:
            return
        self.text.append(data)
        for _, parts in self._open:
            parts.append(data)

    def close(self):
        """Finish the page, then give each label the control its `for` names
        and each form the text after it."""
        super().close()
        for form in self.forms:
            end = len(self.text) if form.text_end is None else form.text_end
            form.text_after = normalise("".join(self.text[end:]))
        by_id = {}
        for control in self.controls:
            if control.id:
                by_id.setdefault(control.id, control)
        for label in self.labels:
            control = by_id.get(label.for_id)
            if control is not None and control.form is not None:
                control.form.labels.append((normalise("".join(label.parts)), control))
