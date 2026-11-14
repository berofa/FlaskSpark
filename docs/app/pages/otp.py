"""ui-otp (Bootstrap 6 OTP input, new in v6)."""

from __future__ import annotations

from .common import lines

PAGE = {
    "title": "ui-otp",
    "summary": "One-time passwords, PINs and verification codes in one accessible text field drawn as separate slots — "
    "new in Bootstrap 6. Autofill, paste of formatted codes and normal text editing work.",
    "submodule": "ui-otp",
    "entry": "modules/bootstrap/ui-otp/ui-otp.js",
    "sections": [
        {
            "id": "example",
            "title": "Example",
            "intro": "One real <code>&lt;input&gt;</code> backs the slots, so screen readers announce one field and SMS / "
            "password-manager autofill (<code>autocomplete=\"one-time-code\"</code>) works. Click a slot to overwrite it; paste "
            "<code>123-456</code> and the dash is dropped.",
            "html": lines('<ui-otp aria-label="Verification code"></ui-otp>'),
        },
        {
            "id": "connected",
            "title": "Connected and PIN",
            "intro": "<code>connected</code> merges the slots into one field; <code>length</code> sets their number.",
            "html": lines('<ui-otp connected aria-label="Code"></ui-otp>', '<ui-otp connected length="4" aria-label="PIN" class="mt-3"></ui-otp>'),
        },
        {
            "id": "separator",
            "title": "With separator",
            "intro": "<code>groups=\"3,3\"</code> splits the slots with a decorative <code>separator</code> (never part of the value).",
            "html": lines('<ui-otp groups="3,3" aria-label="Code"></ui-otp>', '<ui-otp groups="2,2,2" separator="–" class="mt-3" aria-label="Code"></ui-otp>'),
        },
        {
            "id": "sizes",
            "title": "Sizes",
            "html": lines('<ui-otp size="sm" aria-label="Small"></ui-otp>', '<ui-otp size="lg" class="mt-3" aria-label="Large"></ui-otp>'),
        },
        {
            "id": "types",
            "title": "Alphanumeric and masking",
            "intro": "<code>type</code> <code>alphanumeric</code> or <code>alpha</code> accepts letters (default only digits); "
            "<code>mask</code> shows dots while it stays a text field (numeric keyboard and autofill still work).",
            "html": lines('<ui-otp connected type="alphanumeric" aria-label="Code with letters"></ui-otp>',
                          '<ui-otp connected mask value="123" class="mt-3" aria-label="Masked"></ui-otp>'),
        },
        {
            "id": "states",
            "title": "Disabled and validation",
            "intro": "<code>disabled</code>; <code>error</code> (a server message) and the field validation of the other inputs. "
            "A started but incomplete code is invalid (<code>incomplete-message</code>).",
            "html": lines('<ui-otp connected disabled value="12" aria-label="Disabled"></ui-otp>',
                          '<ui-otp connected class="mt-3" value="123456" error="This code has expired." aria-label="Code"></ui-otp>'),
        },
        {
            "id": "form-field",
            "title": "Form field",
            "intro": "<code>label</code>, <code>help</code>, <code>name</code>, <code>required</code>; "
            "<code>ui-otp:complete</code> fires when every slot is filled.",
            "html": lines(
                '<form data-bs-validate novalidate onsubmit="event.preventDefault(); if (this.checkValidity()) this.querySelector(\'output\').value = new FormData(this).get(\'code\')">',
                '  <ui-otp name="code" label="Verification code" help="Enter the 6-digit code sent to your phone." required groups="3,3"></ui-otp>',
                '  <ui-button type="submit" variant="primary" class="mt-3">Verify</ui-button> <output class="ms-2"></output>',
                "</form>",
            ),
        },
        {
            "id": "plain-markup",
            "title": "Plain markup",
            "intro": "Bootstrap's own <code>.otp[data-bs-otp]</code> markup (<code>data-bs-length</code>, <code>data-bs-type</code>, "
            "<code>data-bs-mask</code>, <code>data-bs-groups</code>, <code>data-bs-separator</code>).",
            "html": lines('<div class="otp otp-connected" data-bs-otp data-bs-groups="[3,3]">',
                          '  <input type="text" class="form-control" maxlength="6" aria-label="Plain code">', "</div>"),
        },
        {
            "id": "javascript",
            "title": "JavaScript",
            "script": lines('const otp = document.querySelector("ui-otp");',
                            'otp.addEventListener("ui-otp:complete", (event) => verify(event.detail.value));',
                            'otp.setValue("654321");', "otp.clear();", "otp.focus();"),
        },
    ],
    "tokens": {"host": "ui-otp", "example_token": "--bs-otp-size", "example_value": "3.5rem"},
    "elements": [
        {
            "tag": "ui-otp",
            "attributes": [
                ("length", "number", "Number of slots (6)."),
                ("type", "string", "<code>numeric</code> (default), <code>alphanumeric</code>, <code>alpha</code>."),
                ("mask", "boolean", "Dots instead of the characters."),
                ("groups / separator", "string", "Group sizes (<code>3,3</code>) and the character between them (<code>·</code>)."),
                ("connected", "boolean", "One field with shared borders."),
                ("size", "string", "<code>sm</code> or <code>lg</code>."),
                ("name / value / label / help / required / disabled / error", "string", "Like the other form fields."),
                ("incomplete-message", "string", "Message for a started, incomplete code."),
            ],
            "parts": [("field / label / help / feedback", "The form field."), ("otp / control", "The container and the real input."),
                      ("slots / slot / separator", "The drawn slots.")],
            "events": [("input / change", "As usual."), ("ui-otp:input", "Every change; <code>detail.value</code>."),
                       ("ui-otp:complete", "Every slot filled; <code>detail.value</code>.")],
            "methods": [("value / setValue(value)", "Get / set (sanitized)."), ("clear() / focus()", "Empty / focus the next free slot.")],
        }
    ],
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["otp"]
