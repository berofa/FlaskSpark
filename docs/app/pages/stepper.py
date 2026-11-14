"""ui-stepper (Bootstrap 6 stepper, new in v6)."""

from __future__ import annotations

from .common import lines

STEPS = ["Create account", "Confirm email", "Update profile", "Finish"]


def steps(names=STEPS, indent: str = "  ", extra: dict[int, str] | None = None) -> list[str]:
    return [f"{indent}<ui-step{(extra or {}).get(i, '')}>{name}</ui-step>" for i, name in enumerate(names)]


PAGE = {
    "title": "ui-stepper",
    "summary": "Numbered steps with a connecting track for timelines, wizards and progress — new in Bootstrap 6.",
    "submodule": "ui-stepper",
    "entry": "modules/bootstrap/ui-stepper/ui-stepper.js",
    "sections": [
        {
            "id": "basic",
            "title": "Basic",
            "intro": "Vertical by default. <code>current</code> marks the steps up to that one as active (or <code>active</code> on a step).",
            "html": lines('<ui-stepper current="2">', *steps(), "</ui-stepper>"),
        },
        {
            "id": "horizontal",
            "title": "Horizontal and responsive",
            "intro": "<code>horizontal</code> always, or <code>horizontal=\"sm\"</code> … <code>2xl</code> from that width of the stepper's "
            "container (container queries) — drag the box narrower.",
            "html": lines('<ui-stepper horizontal current="2">', *steps(), "</ui-stepper>",
                          '<div class="docs-resizable mt-3">', '  <ui-stepper horizontal="sm" current="3">', *steps(indent="    "), "  </ui-stepper>", "</div>"),
        },
        {
            "id": "gap",
            "title": "Gap",
            "html": lines('<ui-stepper current="2" style="--bs-stepper-gap: 3rem">', *steps(), "</ui-stepper>"),
        },
        {
            "id": "variants",
            "title": "Variants",
            "html": lines("<ui-stepper horizontal>", *steps(extra={0: ' active variant="accent"', 2: ' active variant="success"', 3: ' active variant="danger"'}), "</ui-stepper>"),
        },
        {
            "id": "overflow",
            "stacked": True,
            "title": "Overflow",
            "intro": "<code>overflow</code> scrolls a horizontal stepper that is wider than its place.",
            "html": lines('<ui-stepper horizontal overflow current="2">',
                          *steps(["Create account", "Verify email address", "Complete profile setup", "Add payment method", "Review and confirm", "Finish onboarding"]),
                          "</ui-stepper>"),
        },
        {
            "id": "complex",
            "stacked": True,
            "title": "Complex content",
            "intro": "A step's content is yours: descriptions, badges, theme helpers.",
            "html": lines(
                '<ui-stepper current="2" style="--bs-stepper-align-items: start">',
                *[f'  <ui-step><div class="pt-1"><div class="fw-semibold">{t}</div><small class="fg-3">{d}</small></div></ui-step>'
                  for t, d in (("Create", "Create an account."), ("Confirm", "Confirm your email."), ("Set-up", "Configure your profile."), ("Finish", "Welcome aboard!"))],
                "</ui-stepper>",
                '<ui-stepper horizontal full class="mt-4">',
                '  <ui-step active variant="success"><div>Create account</div><ui-badge variant="success" appearance="subtle">Complete</ui-badge></ui-step>',
                '  <ui-step active variant="success"><div>Confirm email</div><ui-badge variant="success" appearance="subtle">Complete</ui-badge></ui-step>',
                '  <ui-step active><div>Update profile</div><ui-badge variant="primary" appearance="subtle">In progress</ui-badge></ui-step>',
                '  <ui-step variant="secondary"><div>Finish</div><ui-badge variant="secondary" appearance="subtle">Pending</ui-badge></ui-step>',
                "</ui-stepper>",
            ),
        },
        {
            "id": "alignment",
            "stacked": True,
            "title": "Alignment and full width",
            "html": lines('<ui-stepper horizontal current="2">', *steps(), "</ui-stepper>",
                          '<ui-stepper horizontal current="2" align="center" class="mt-3">', *steps(), "</ui-stepper>",
                          '<ui-stepper horizontal current="2" align="end" class="mt-3">', *steps(), "</ui-stepper>",
                          '<ui-stepper horizontal current="2" full class="mt-3">', *steps(), "</ui-stepper>"),
        },
        {
            "id": "links",
            "title": "Links and clickable steps",
            "intro": "<code>href</code> on a step makes it a link (across pages); <code>clickable</code> makes every step a button "
            "and fires <code>ui-stepper:select</code> (steps within one page, e.g. a wizard).",
            "html": lines('<ui-stepper current="2">', *steps(extra={i: f' href="#step-{i + 1}"' for i in range(4)}), "</ui-stepper>",
                          '<ui-stepper id="stepperWizard" horizontal clickable current="1" class="mt-4">', *steps(), "</ui-stepper>"),
        },
        {
            "id": "javascript",
            "title": "JavaScript",
            "script": lines('const stepper = document.querySelector("#stepperWizard");',
                            'stepper.addEventListener("ui-stepper:select", (event) => { stepper.current = event.detail.index + 1; });'),
        },
    ],
    "tokens": {"host": "ui-stepper", "example_token": "--bs-stepper-size", "example_value": "2.5rem"},
    "elements": [
        {
            "tag": "ui-stepper",
            "attributes": [
                ("horizontal", "string", "Always, or from a container width <code>sm</code> … <code>2xl</code>."),
                ("current", "number", "Steps up to this one (from 1) are active."),
                ("overflow", "boolean", "Scrolls when too wide."), ("full", "boolean", "Full width."),
                ("align", "string", "<code>start</code>, <code>center</code>, <code>end</code>."),
                ("clickable", "boolean", "Steps are buttons (<code>ui-stepper:select</code>)."),
            ],
            "slots": [("(steps)", "<code>&lt;ui-step&gt;</code> children.")],
            "parts": [("stepper", "The list."), ("step", "A step.")],
            "events": [("ui-stepper:select", "<code>detail.index</code>, <code>detail.step</code> (clickable).")],
            "methods": [("current", "Get / set."), ("steps", "The step elements.")],
        },
        {
            "tag": "ui-step",
            "attributes": [("active", "boolean", "Done / current (without <code>current</code> on the stepper)."),
                           ("variant", "string", "Theme colour."), ("href", "string", "A link step."), ("disabled", "boolean", "Not clickable.")],
            "slots": [("(default)", "The step's content.")],
        },
    ],
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["stepper"]
PAGE["page_script"] = lines('document.querySelector("#stepperWizard").addEventListener("ui-stepper:select", (event) => {',
                            "  event.currentTarget.current = event.detail.index + 1;", "});")
