"""ui-progress (Bootstrap 6 progress bars)."""

from __future__ import annotations

from .common import VARIANT_ATTRIBUTE, lines

PAGE = {
    "title": "ui-progress",
    "summary": "Progress bars with labels, theme colours, stripes and animation, and stacked segments; accessible as "
    "role=\"progressbar\".",
    "submodule": "ui-progress",
    "entry": "modules/bootstrap/ui-progress/ui-progress.js",
    "sections": [
        {
            "id": "example",
            "title": "Example",
            "intro": "<code>value</code> between <code>min</code> (0) and <code>max</code> (100); <code>label</code> names it for "
            "screen readers.",
            "html": lines('<div class="vstack gap-3">', *[f'  <ui-progress value="{v}" label="Basic example"></ui-progress>' for v in (0, 25, 50, 75, 100)], "</div>"),
        },
        {
            "id": "height",
            "title": "Height",
            "intro": "The height is a token on the element (<code>--bs-progress-height</code>).",
            "html": lines('<ui-progress value="25" label="1px high" style="--bs-progress-height: 1px"></ui-progress>',
                          '<ui-progress value="25" label="20px high" style="--bs-progress-height: 20px" class="mt-3"></ui-progress>'),
        },
        {
            "id": "labels",
            "title": "Labels",
            "intro": "<code>show-value</code> writes the percentage into the bar; or your own text as content.",
            "html": lines('<ui-progress value="25" show-value label="With label"></ui-progress>',
                          '<ui-progress value="3" max="7" label="Steps" class="mt-3">Step 3 of 7</ui-progress>'),
        },
        {
            "id": "variants",
            "title": "Backgrounds",
            "intro": "<code>variant</code> colours the bar with a theme colour and its contrast text colour.",
            "html": lines('<div class="vstack gap-3">', *[f'  <ui-progress value="{v}" variant="{t}" show-value label="{t}"></ui-progress>'
                                                          for v, t in ((25, "success"), (50, "info"), (75, "warning"), (100, "danger"))], "</div>"),
        },
        {
            "id": "stacked",
            "title": "Multiple bars",
            "intro": "<code>&lt;ui-progress-bar&gt;</code> children stack segments in one bar.",
            "html": lines("<ui-progress>", '  <ui-progress-bar value="15" label="Segment one"></ui-progress-bar>',
                          '  <ui-progress-bar value="30" variant="success" label="Segment two"></ui-progress-bar>',
                          '  <ui-progress-bar value="20" variant="info" label="Segment three">20%</ui-progress-bar>', "</ui-progress>"),
        },
        {
            "id": "striped",
            "title": "Striped and animated",
            "intro": "<code>striped</code> adds stripes, <code>animated</code> moves them.",
            "html": lines('<div class="vstack gap-3">', '  <ui-progress value="10" striped label="Striped"></ui-progress>',
                          '  <ui-progress value="50" striped variant="info" label="Striped info"></ui-progress>',
                          '  <ui-progress value="75" animated label="Animated"></ui-progress>', "</div>"),
        },
        {
            "id": "javascript",
            "title": "JavaScript",
            "script": lines('const progress = document.querySelector("ui-progress");', "progress.value = 60; // the bar moves (transition)"),
        },
    ],
    "tokens": {"host": "ui-progress", "example_token": "--bs-progress-height", "example_value": ".5rem"},
    "elements": [
        {
            "tag": "ui-progress",
            "attributes": [("value / min / max", "number", "Progress (0–100 by default)."), ("label", "string", "Accessible name."),
                           ("show-value", "boolean", "The percentage in the bar."), VARIANT_ATTRIBUTE,
                           ("striped / animated", "boolean", "Stripes, moving stripes.")],
            "slots": [("(default)", "Text in the bar."), ("(segments)", "<code>&lt;ui-progress-bar&gt;</code> children.")],
            "parts": [("progress", "The track."), ("bar", "The bar(s)."), ("segment", "A stacked segment.")],
            "methods": [("value", "Get / set as a number.")],
        },
        {
            "tag": "ui-progress-bar",
            "attributes": [("value", "number", "Share of the segment."), ("variant / striped / animated / label", "", "As above.")],
            "slots": [("(default)", "Text in the segment.")],
        },
    ],
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["progress"]
