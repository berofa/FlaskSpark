"""ui-input, ui-select, ui-textarea (Bootstrap 6 form controls, input group, floating labels, adornments, validation)."""

from __future__ import annotations

from .common import lines

SEARCH = (
    '<svg slot="{slot}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor">'
    '<path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001q.044.06.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1 1 '
    '0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0"/></svg>'
)
ENVELOPE = (
    '<svg slot="{slot}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor">'
    '<path d="M0 4a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2zm2-1a1 1 0 0 0-1 1v.217l7 4.2 7-4.2V4a1 1 0 '
    '0 0-1-1zm13 2.383-4.708 2.825L15 11.105zm-.034 6.876-5.64-3.471L8 9.583l-1.326-.795-5.64 3.47A1 1 0 0 0 2 13h12a1 1 0 0 '
    '0 .966-.741M1 11.105l4.708-2.897L1 5.383z"/></svg>'
)
OPTIONS = lines(
    '  <option value="">Choose one…</option>',
    '  <option value="1">One</option>',
    '  <option value="2">Two</option>',
    '  <option value="3">Three</option>',
)
CITIES = lines(
    "  <datalist>",
    *(f'    <option value="{city}"></option>' for city in ("San Francisco", "New York", "Seattle", "Los Angeles", "Chicago")),
    "  </datalist>",
)


def select(attributes: str) -> str:
    return lines(f"<ui-select{attributes}>", OPTIONS, "</ui-select>")


PAGE = {
    "title": "ui-input / ui-select / ui-textarea",
    "summary": "Text fields with Bootstrap 6's form control, form field, input group, floating label, adornment and "
    "validation styles. Form-associated: they submit, reset and validate inside a normal <form>.",
    "submodule": "ui-input",
    "entry": "modules/bootstrap/ui-input/ui-input.js",
    "sections": [
        {
            "id": "example",
            "title": "Example",
            "intro": "<code>label</code> and <code>help</code> build Bootstrap's <code>.form-field</code>: label, "
            "field and help text in a column, the help text linked with <code>aria-describedby</code>.",
            "html": lines(
                '<ui-input type="email" label="Email address" placeholder="name@example.com" '
                'help="We’ll never share your email with anyone else."></ui-input>',
                '<ui-textarea label="Example textarea"></ui-textarea>',
                '<ui-textarea label="Taller textarea" rows="4"></ui-textarea>',
                select(' label="Example select"'),
            ),
            "preview_class": "d-grid gap-3",
        },
        {
            "id": "select",
            "title": "Select",
            "intro": "Options are <code>&lt;option&gt;</code> / <code>&lt;optgroup&gt;</code> children. "
            "<code>multiple</code> submits every selected value, <code>rows</code> shows a list box.",
            "html": lines(
                lines('<ui-select label="Multiple select" name="multiple" multiple>', OPTIONS.replace('value="1"', 'value="1" selected'), "</ui-select>"),
                select(' label="Size 3 select" rows="3"'),
                lines('<ui-select label="With groups">', '  <optgroup label="Group A"><option>A1</option><option>A2</option></optgroup>',
                      '  <optgroup label="Group B"><option>B1</option></optgroup>', "</ui-select>"),
            ),
            "preview_class": "d-grid gap-3",
        },
        {
            "id": "sizes",
            "title": "Sizes",
            "intro": "<code>size</code>: <code>sm</code> or <code>lg</code> (height, padding, font size, radius).",
            "html": lines(
                *(f'<ui-input{f" size={chr(34)}{s}{chr(34)}" if s else ""} label="{title} input" placeholder="{title} input"></ui-input>'
                  for s, title in (("sm", "Small"), ("", "Default"), ("lg", "Large"))),
                '<ui-textarea size="sm" label="Small textarea" placeholder="Small textarea"></ui-textarea>',
                select(' size="lg" label="Large select"'),
            ),
            "preview_class": "d-grid gap-3",
        },
        {
            "id": "states",
            "title": "Disabled, readonly, plain text",
            "intro": "<code>disabled</code> (also from a disabled <code>&lt;fieldset&gt;</code>), "
            "<code>readonly</code>, and <code>plaintext</code>: a readonly value shown as plain text.",
            "html": lines(
                '<ui-input placeholder="Disabled input" aria-label="Disabled input" disabled></ui-input>',
                '<ui-input value="Disabled readonly input" aria-label="Disabled readonly input" disabled readonly></ui-input>',
                select(' aria-label="Disabled select" disabled'),
                '<ui-textarea placeholder="Disabled textarea" aria-label="Disabled textarea" disabled></ui-textarea>',
                '<ui-input value="Readonly input here..." aria-label="Readonly input" readonly></ui-input>',
                '<ui-input plaintext label="Email" value="email@example.com"></ui-input>',
            ),
            "preview_class": "d-grid gap-3",
        },
        {
            "id": "types",
            "title": "Types",
            "intro": "Date and time types, <code>color</code>, <code>file</code> (submits the files; "
            "<code>accept</code>, <code>multiple</code>), and suggestions from a <code>&lt;datalist&gt;</code> child "
            "(<code>caret</code> adds the select arrow).",
            "html": lines(
                '<ui-input type="datetime-local" aria-label="Date and time" value="2026-02-24T13:00"></ui-input>',
                '<ui-input type="date" aria-label="Date" value="2026-02-24"></ui-input>',
                '<ui-input type="time" aria-label="Time" value="13:00"></ui-input>',
                '<ui-input type="month" aria-label="Month" value="2026-02"></ui-input>',
                '<ui-input type="week" aria-label="Week" value="2026-W09"></ui-input>',
                '<ui-input type="color" label="Color picker" value="#631aff"></ui-input>',
                '<ui-input type="color" size="lg" label="Large color picker" value="#631aff"></ui-input>',
                '<ui-input type="file" label="Default file input"></ui-input>',
                '<ui-input type="file" label="Multiple files input" multiple accept="image/*"></ui-input>',
                lines('<ui-input label="Datalist example" placeholder="Type to search...">', CITIES, "</ui-input>"),
                lines('<ui-input label="Datalist with caret" placeholder="Type to search..." caret>', CITIES, "</ui-input>"),
            ),
            "preview_class": "d-grid gap-3",
        },
        {
            "id": "ghost",
            "title": "Ghost",
            "intro": "<code>ghost</code>: no field styling at all, e.g. inside your own container.",
            "html": '<ui-input ghost placeholder="Ghost input" aria-label="Ghost input"></ui-input>',
        },
        {
            "id": "input-group",
            "title": "Input group",
            "intro": "<code>prefix</code> and <code>suffix</code> add texts; the slots of the same names take buttons "
            "or a select, which join the group's corners. Works with textareas and selects, and with the sizes.",
            "html": lines(
                '<ui-input prefix="@" placeholder="Username" aria-label="Username"></ui-input>',
                '<ui-input suffix="@example.com" placeholder="Recipient’s username" aria-label="Recipient’s username"></ui-input>',
                '<ui-input label="Your vanity URL" prefix="https://example.com/" placeholder="username" '
                'help="Choose a unique URL for your profile."></ui-input>',
                '<ui-input prefix="$" suffix=".00" aria-label="Amount (to the nearest dollar)"></ui-input>',
                '<ui-input placeholder="Search" aria-label="Search">',
                '  <ui-button slot="suffix" appearance="outline" variant="secondary">Button</ui-button>',
                "</ui-input>",
                '<ui-input placeholder="Two buttons" aria-label="Two buttons">',
                '  <ui-button slot="prefix" appearance="outline" variant="secondary">Button</ui-button>',
                '  <ui-button slot="suffix" appearance="outline" variant="secondary">Button</ui-button>',
                '  <ui-button slot="suffix" appearance="outline" variant="secondary">Button</ui-button>',
                "</ui-input>",
                '<ui-textarea prefix="With textarea" aria-label="With textarea"></ui-textarea>',
                select(' prefix="Options"'),
                *(f'<ui-input size="{s}" prefix="{title}" aria-label="{title} input group"></ui-input>' for s, title in (("sm", "Small"), ("lg", "Large"))),
            ),
            "preview_class": "d-grid gap-3",
        },
        {
            "id": "floating-labels",
            "title": "Floating labels",
            "intro": "<code>floating</code> places the label inside the field; it floats up once there is a value "
            "or focus. <code>floating=\"always\"</code> keeps it up and shows the placeholder.",
            "html": lines(
                '<ui-input type="email" label="Email address" floating></ui-input>',
                '<ui-input type="password" label="Password" floating></ui-input>',
                '<ui-input type="email" label="Input with value" floating value="test@example.com"></ui-input>',
                '<ui-input type="email" label="Invalid input" floating value="test@example" error="Not a valid address"></ui-input>',
                '<ui-textarea label="Comments" floating rows="3"></ui-textarea>',
                select(' label="Works with selects" floating'),
                '<ui-input type="date" label="Date" floating value="2026-02-24"></ui-input>',
                '<ui-input label="Disabled" floating disabled></ui-input>',
                '<ui-input label="Email address" floating="always" placeholder="name@example.com"></ui-input>',
                '<ui-input label="Username" floating prefix="@"></ui-input>',
            ),
            "preview_class": "d-grid gap-3",
        },
        {
            "id": "adornments",
            "title": "Adornments",
            "intro": "Icons (slots <code>start</code> / <code>end</code>) or texts (attributes of the same names) "
            "inside the field (<code>.form-adorn</code>); clicking them focuses the field. They are decorative: "
            "name the field with <code>label</code>.",
            "html": lines(
                '<ui-input type="search" placeholder="Search..." aria-label="Search">',
                "  " + SEARCH.format(slot="start"),
                "</ui-input>",
                '<ui-input type="email" label="Email address" placeholder="you@example.com">',
                "  " + ENVELOPE.format(slot="end"),
                "</ui-input>",
                '<ui-input label="Amount" start="$" end="USD" placeholder="0.00"></ui-input>',
                '<ui-input label="Website" end=".example.com" placeholder="subdomain"></ui-input>',
                '<ui-input size="sm" start="@" placeholder="Small" aria-label="Small"></ui-input>',
                '<ui-input size="lg" start="@" placeholder="Large" aria-label="Large"></ui-input>',
            ),
            "preview_class": "d-grid gap-3",
        },
        {
            "id": "clearable",
            "title": "Clearable",
            "intro": "<code>clearable</code> adds an × while there is a value; it and Escape empty the field and fire "
            "<code>input</code> and <code>change</code>.",
            "html": '<ui-input type="search" clearable value="Something to clear" aria-label="Search"></ui-input>',
        },
        {
            "id": "password-strength",
            "title": "Password strength",
            "intro": "New in Bootstrap 6. <code>strength</code> on a password field adds a meter that rates the password while "
            "typing: four segments, or <code>strength=\"bar\"</code>; <code>strength-text</code> shows the level. Points for "
            "length (<code>strength-min-length</code>, default 8, and 4 more), lower and upper case, digits, special "
            "characters (two or more count twice) and 16+ characters; 1–2 weak, 3–4 fair, 5–6 good, more strong.",
            "html": lines(
                '<ui-input type="password" label="Password" strength strength-text placeholder="Enter password"></ui-input>',
                '<ui-input type="password" label="Password (bar)" strength="bar" strength-text class="mt-3"',
                '  weak-label="Too weak" strong-label="Excellent!" value="Abcdefgh1!"></ui-input>',
            ),
            "script": lines(
                'const field = document.querySelector("ui-input[strength]");',
                'field.addEventListener("ui-input:strength", (event) => console.log(event.detail.strength, event.detail.score));',
                "field.strengthWeights = { uppercase: 0, special: 2 }; // like Bootstrap's weights",
                "field.strengthThresholds = [3, 5, 7];",
                "field.strengthScorer = (password) => (password.length >= 12 ? 8 : 2); // or your own scoring",
            ),
        },
        {
            "id": "password-strength-plain",
            "title": "Password strength: plain and static markup",
            "intro": "Bootstrap's own markup works too: a <code>[data-bs-strength]</code> meter rates the password field in its "
            "container (or <code>data-bs-input</code>). With a level set (<code>data-bs-strength=\"good\"</code>) it is a "
            "static display.",
            "html": lines(
                "<div>",
                '  <input type="password" class="form-control" placeholder="Plain markup" aria-label="Password">',
                '  <div class="strength" data-bs-strength>' + '<div class="strength-segment"></div>' * 4 + "</div>",
                '  <span class="strength-text"></span>',
                "</div>",
                '<div class="strength-bar mt-3" data-bs-strength="good" aria-label="Good"></div>',
            ),
        },
        {
            "id": "validation",
            "title": "Validation",
            "intro": "Like Bootstrap 6: add <code>data-bs-validate</code> (and <code>novalidate</code> for your own messages) to the "
            "<code>&lt;form&gt;</code>. The native checks (<code>required</code>, <code>type</code>, <code>pattern</code>, "
            "<code>min</code>, …) then show once a field was left or a submit was tried (like <code>:user-invalid</code>), "
            "with a message below; nothing shows on page load. <code>data-bs-validate=\"valid\"</code> also marks valid "
            "fields (<code>valid-feedback</code> adds a message), <code>tooltip</code> shows messages as tooltips.",
            "html": lines(
                '<form class="d-grid gap-3" data-bs-validate="valid" novalidate onsubmit="event.preventDefault()">',
                '  <ui-input label="First name" value="Mark" required valid-feedback="Looks good!"></ui-input>',
                '  <ui-input label="Username" prefix="@" required></ui-input>',
                '  <ui-input label="Email" type="email" value="mark@example"></ui-input>',
                '  <ui-input label="City" required tooltip></ui-input>',
                lines('  <ui-select label="State" required>', OPTIONS, "  </ui-select>"),
                '  <ui-textarea label="Message" required minlength="10"></ui-textarea>',
                '  <ui-button type="submit" variant="primary">Submit form</ui-button>',
                "</form>",
            ),
        },
        {
            "id": "validation-browser",
            "title": "Browser defaults and server-side",
            "intro": "Without <code>data-bs-validate</code> the fields show no client-side styling: the browser blocks the submit "
            "and shows its own message. A server message (<code>error</code>) always shows at once, like Bootstrap's "
            "<code>.is-invalid</code>; <code>validate()</code> shows the feedback from script in any case.",
            "html": lines(
                '<form class="d-grid gap-3" onsubmit="event.preventDefault()">',
                '  <ui-input label="Required (browser message on submit)" required></ui-input>',
                '  <ui-input label="Username (server check)" value="mdo" error="That username is already taken."></ui-input>',
                '  <ui-button type="submit" variant="primary">Submit form</ui-button>',
                "</form>",
            ),
            "script": lines(
                'const email = document.querySelector("ui-input[type=email]");',
                "// a check of the page on top of the native ones",
                'email.validator = (value) => value.endsWith("@example.com") ? "" : "Use your example.com address";',
                "// show every field's feedback from script (also without data-bs-validate)",
                'const valid = [...form.querySelectorAll("ui-input, ui-select, ui-textarea")].every((field) => field.validate());',
            ),
        },
    ],
    "elements": [
        {
            "tag": "ui-input / ui-select / ui-textarea",
            "attributes": [
                ("name / value", "string", "Submitted under the name; value is the initial value."),
                ("label", "string", "The label (<code>.form-label</code>)."),
                ("help", "string", "Help text below (<code>.form-text</code>, linked by aria-describedby)."),
                ("size", "string", "<code>sm</code> or <code>lg</code>."),
                ("floating", "string", "Floating label; <code>always</code> keeps it floated."),
                ("prefix / suffix", "string", "Input group texts (the slots take buttons or a select)."),
                ("start / end", "string", "Adornment texts inside the field (the slots take icons)."),
                ("plaintext", "boolean", "Readonly value as plain text."),
                ("ghost", "boolean", "No field styling."),
                ("disabled / readonly / required / placeholder / autocomplete / spellcheck", "", "Forwarded."),
                ("error", "string", "Message from the server: invalid at once, until the value changes."),
                ("valid-feedback", "string", "Message for a valid value (green)."),
                ("tooltip", "boolean", "Feedback as a tooltip."),
            ],
            "slots": [
                ("prefix / suffix", "Buttons or a select in the input group."),
                ("start / end", "Icons inside the field."),
            ],
            "parts": [
                ("field", "The <code>.form-field</code>."),
                ("label, control, help", "Label, native control, help text."),
                ("group, prefix, suffix, prefix-slot, suffix-slot", "The input group and its addons."),
                ("adorn, start, end", "The adorned wrapper and its adornments."),
                ("floating", "The <code>.form-floating</code> wrapper."),
                ("feedback, valid-feedback", "The messages."),
                ("caret", "The arrow of selects and inputs with <code>caret</code>."),
            ],
            "events": [("input", "Native, composed."), ("change", "Re-dispatched on the host.")],
            "methods": [
                ("value", "Current value."),
                ("validate()", "Shows the feedback and returns the validity."),
                ("validator / formatter", "Page-defined check (value → message) and formatting (value → Promise)."),
                ("form, validity, validationMessage, checkValidity(), reportValidity(), focus()", "As on native fields."),
            ],
        },
        {
            "tag": "ui-input",
            "attributes": [
                ("type", "string", "text, number, email, password, search, url, tel, date, time, datetime-local, "
                 "month, week, color, file."),
                ("min / max / step / minlength / maxlength / pattern / inputmode", "", "Forwarded."),
                ("accept / multiple / capture", "", "File inputs."),
                ("caret", "boolean", "The select arrow (with a <code>&lt;datalist&gt;</code>)."),
                ("clearable", "boolean", "An × that empties the field."),
                ("strength", "string", "Password strength meter: <code>segments</code> (default) or <code>bar</code>."),
                ("strength-text / strength-min-length", "", "The level as text; minimum length (8)."),
                ("weak-label / fair-label / good-label / strong-label", "string", "Texts of the levels."),
            ],
            "slots": [("(datalist)", "A <code>&lt;datalist&gt;</code> child: suggestions.")],
            "parts": [("strength / strength-text", "The password strength meter and its message.")],
            "events": [("ui-input:strength", "The level changed: <code>detail.strength</code>, <code>detail.score</code>.")],
            "methods": [("files", "Chosen files (type file)."), ("clear()", "Empties the field."),
                        ("strength", "The password's level (read only)."),
                        ("strengthWeights / strengthThresholds / strengthScorer", "Scoring like Bootstrap's options.")],
        },
        {
            "tag": "ui-select",
            "attributes": [
                ("multiple", "boolean", "Several options."),
                ("rows", "number", "Visible rows of a list box."),
            ],
            "slots": [("(options)", "<code>&lt;option&gt;</code> and <code>&lt;optgroup&gt;</code> children.")],
            "methods": [("options / selectedValues", "Options and selected values.")],
        },
        {
            "tag": "ui-textarea",
            "attributes": [("rows / minlength / maxlength / wrap", "", "Forwarded.")],
        },
    ],
    "notes": [
        "Range, password strength, OTP input, combobox, datepicker and chip inputs are separate Bootstrap 6 "
        "components and not part of these three elements.",
        "The CSS variables below are shared by all three elements (the table lists them for <code>ui-input</code>).",
    ],
    "tokens": {"host": "ui-input", "example_token": "--bs-control-border-radius", "example_value": "var(--bs-radius-pill)"},
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["form_controls"]
