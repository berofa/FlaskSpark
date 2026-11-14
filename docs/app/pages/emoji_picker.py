"""ui-emoji-picker (all emojis of Unicode in categories)."""

from __future__ import annotations

from .common import lines

PAGE = {
    "title": "ui-emoji-picker",
    "summary": "All emojis of Unicode (fully qualified, without skin tone variants) in categories like a phone's "
    "keyboard: recently used first, a tab per category, a search over the English names.",
    "submodule": "ui-emoji-picker",
    "entry": "modules/bootstrap/ui-emoji-picker/ui-emoji-picker.js",
    "sections": [
        {
            "id": "example",
            "title": "Example",
            "intro": "A pick fires <code>ui-emoji-picker:pick</code> with <code>detail.emoji</code>. "
            "<code>lang=\"de\"</code> (on the element or an ancestor) gives German labels.",
            "html": lines(
                '<ui-emoji-picker id="emojiDemo" style="max-width: 22rem"></ui-emoji-picker>',
                '<p class="mt-2 mb-0">Picked: <span id="emojiDemoOut">–</span></p>',
            ),
        },
    ],
    "page_script": lines(
        'document.getElementById("emojiDemo")?.addEventListener("ui-emoji-picker:pick", (e) => {',
        '  document.getElementById("emojiDemoOut").textContent = e.detail.emoji;',
        "});",
    ),
    "elements": [
        {
            "tag": "ui-emoji-picker",
            "attributes": [
                ("storage-key", "string", "localStorage key of the recently used ones (default <code>ui-emoji-picker:recent</code>)."),
                ("lang", "string", "<code>de</code>: German labels (else the closest <code>[lang]</code>, English by default)."),
            ],
            "slots": [],
            "events": [("ui-emoji-picker:pick", "An emoji was chosen (<code>detail.emoji</code>).")],
            "methods": [],
        }
    ],
    "notes": [
        "The list (<code>emoji.json</code>) is generated from Unicode's <code>emoji-test.txt</code> and loads on first use.",
        "Parts: <code>picker</code>, <code>tabs</code>, <code>search</code>, <code>grid</code>. Size: "
        "<code>--ui-emoji-picker-size</code>, <code>--ui-emoji-picker-height</code>.",
    ],
}
