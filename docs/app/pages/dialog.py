"""ui-dialog (Bootstrap 6 dialog)."""

from __future__ import annotations

from .common import lines

TEXT = "This is a native dialog element. It uses the browser’s built-in modal behavior for accessibility and focus management."


def dialog(dialog_id: str, title: str, body: str = TEXT, attributes: str = "", footer: bool = True) -> str:
    rows = [f'<ui-dialog id="{dialog_id}" heading="{title}"{attributes}>', f"  <p>{body}</p>"]
    if footer:
        rows.append('  <ui-button slot="footer" variant="secondary" data-bs-dismiss="dialog">Close</ui-button>')
        rows.append('  <ui-button slot="footer" variant="primary">Save changes</ui-button>')
    rows.append("</ui-dialog>")
    return lines(*rows)


def trigger(dialog_id: str, label: str, extra: str = "") -> str:
    return f'<ui-button variant="primary" data-bs-toggle="dialog" data-bs-target="#{dialog_id}"{extra}>{label}</ui-button>'


PAGE = {
    "title": "ui-dialog",
    "summary": "Dialogs on the browser's native <dialog>: top layer, backdrop, focus trap and Escape for free; static "
    "backdrops, non-modal dialogs, sizes, fullscreen, scrollable bodies, animations and swapping.",
    "submodule": "ui-dialog",
    "entry": "modules/bootstrap/ui-dialog/ui-dialog.js",
    "sections": [
        {
            "id": "example",
            "title": "Example",
            "intro": "A trigger with <code>data-bs-toggle=\"dialog\"</code> and <code>data-bs-target</code> opens it "
            "(<code>showModal()</code>); <code>data-bs-dismiss=\"dialog\"</code> inside closes it. Focus returns to "
            "the trigger.",
            "html": lines(trigger("exampleDialog", "Open dialog"), dialog("exampleDialog", "Dialog title")),
        },
        {
            "id": "without-javascript",
            "title": "Without data attributes",
            "intro": "Invoker commands work too, where the browser supports them: <code>commandfor</code> and "
            "<code>command=\"show-modal\"</code> / <code>\"close\"</code>.",
            "html": lines(
                '<button type="button" class="btn-solid theme-primary" commandfor="invokerDialog" command="show-modal">Open dialog</button>',
                '<ui-dialog id="invokerDialog" heading="Invoker Commands">',
                "  <p>This dialog opens with <code>command=\"show-modal\"</code> and closes with <code>command=\"close\"</code>.</p>",
                '  <button slot="footer" type="button" class="btn-solid theme-secondary" commandfor="invokerDialog" command="close">Close</button>',
                "</ui-dialog>",
            ),
        },
        {
            "id": "dark",
            "title": "Dark dialog",
            "intro": "<code>data-bs-theme=\"dark\"</code> on the element.",
            "html": lines(trigger("darkDialog", "Open dark dialog"),
                          dialog("darkDialog", "Dark dialog title", attributes=' data-bs-theme="dark"')),
        },
        {
            "id": "static-backdrop",
            "title": "Static backdrop",
            "intro": "<code>backdrop=\"static\"</code>: a click outside does not close it (it pulses and fires "
            "<code>ui-dialog:hide-prevented</code>). Use the close button or Escape. <code>keyboard=\"false\"</code> "
            "also keeps Escape from closing it; <code>backdrop=\"false\"</code> hides the backdrop.",
            "html": lines(
                trigger("staticDialog", "Static backdrop"),
                dialog("staticDialog", "Static backdrop", "I will not close if you click outside of me.", ' backdrop="static"'),
                trigger("strictDialog", "Static, no Escape"),
                dialog("strictDialog", "Strict", "Only the buttons close me.", ' backdrop="static" keyboard="false"'),
                trigger("noBackdropDialog", "No backdrop"),
                dialog("noBackdropDialog", "No backdrop", "The page stays visible behind me.", ' backdrop="false"'),
            ),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "overlays",
            "title": "Overlays",
            "intro": "Tooltips, popovers and menus inside a modal dialog open in the top layer above it.",
            "html": lines(
                trigger("overlayDialog", "Open dialog"),
                '<ui-dialog id="overlayDialog" heading="Overlays inside dialogs">',
                '  <div class="d-flex gap-2 flex-wrap">',
                '    <ui-tooltip title="Tooltip inside a dialog!"><ui-button variant="secondary">Tooltip</ui-button></ui-tooltip>',
                "    <ui-menu>",
                '      <ui-button variant="secondary" data-bs-toggle="menu">Menu</ui-button>',
                '      <div class="menu">',
                '        <a class="menu-item" href="#">Action</a>',
                '        <a class="menu-item" href="#">Another action</a>',
                '        <hr class="menu-divider">',
                '        <div class="submenu">',
                '          <button class="menu-item" type="button">More options</button>',
                '          <div class="menu"><a class="menu-item" href="#">Sub-action A</a><a class="menu-item" href="#">Sub-action B</a></div>',
                "        </div>",
                "      </div>",
                "    </ui-menu>",
                "  </div>",
                '  <ui-button slot="footer" variant="secondary" data-bs-dismiss="dialog">Close</ui-button>',
                "</ui-dialog>",
            ),
        },
        {
            "id": "animations",
            "title": "Animations",
            "intro": "<code>animation</code>: fade (default), <code>instant</code>, <code>slide-down</code> or "
            "<code>slide-up</code>.",
            "html": lines(
                *(lines(trigger(f"anim{name.title().replace('-', '')}", title), dialog(f"anim{name.title().replace('-', '')}", title,
                        attributes=f' animation="{name}"', footer=False))
                  for name, title in (("instant", "Instant"), ("slide-down", "Slide down"), ("slide-up", "Slide up"))),
            ),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "scrollable",
            "title": "Scrollable",
            "intro": "<code>scrollable</code>: the body scrolls, header and footer stay.",
            "html": lines(
                trigger("scrollableDialog", "Launch scrollable body dialog"),
                '<ui-dialog id="scrollableDialog" heading="Scrollable body" scrollable>',
                "  <p>This is some placeholder content to show the scrolling behavior for dialogs.</p>",
                '  <div style="height: 1200px"></div>',
                "  <p>This content should appear at the bottom after you scroll.</p>",
                '  <ui-button slot="footer" variant="secondary" data-bs-dismiss="dialog">Close</ui-button>',
                "</ui-dialog>",
            ),
        },
        {
            "id": "swapping",
            "title": "Swapping dialogs",
            "intro": "A trigger inside an open dialog opens the next one before the current closes; the backdrop "
            "stays.",
            "html": lines(
                trigger("swapDialog1", "Open first dialog"),
                '<ui-dialog id="swapDialog1" heading="First dialog">',
                "  <p>Click below to swap to the second dialog.</p>",
                '  <ui-button slot="footer" variant="primary" data-bs-toggle="dialog" data-bs-target="#swapDialog2">Open second dialog</ui-button>',
                "</ui-dialog>",
                '<ui-dialog id="swapDialog2" heading="Second dialog">',
                "  <p>You swapped from the first dialog.</p>",
                '  <ui-button slot="footer" variant="primary" data-bs-toggle="dialog" data-bs-target="#swapDialog1">Back to first</ui-button>',
                "</ui-dialog>",
            ),
        },
        {
            "id": "non-modal",
            "title": "Non-modal dialogs",
            "intro": "<code>modal=\"false\"</code> (or <code>data-bs-modal=\"false\"</code> on the trigger): no "
            "backdrop, no focus trap, the page stays usable; Escape still closes it.",
            "html": lines(trigger("nonModalDialog", "Open non-modal dialog", ' data-bs-modal="false"'),
                          dialog("nonModalDialog", "Non-modal dialog", "You can still use the page behind me.", footer=False)),
        },
        {
            "id": "sizes",
            "title": "Optional sizes",
            "intro": "<code>size</code>: <code>sm</code> (280px), default (500px), <code>lg</code> (800px), "
            "<code>xl</code> (1140px).",
            "html": lines(*(lines(trigger(f"size{s or 'Md'}", f"{title} dialog"), dialog(f"size{s or 'Md'}", f"{title} dialog",
                                 attributes=f' size="{s}"' if s else "", footer=False))
                            for s, title in (("xl", "Extra large"), ("lg", "Large"), ("", "Default"), ("sm", "Small")))),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "fullscreen",
            "title": "Fullscreen dialog",
            "intro": "<code>fullscreen</code> covers the viewport; with a breakpoint (<code>sm</code> … <code>2xl</code>) "
            "only below it.",
            "html": lines(
                trigger("fullscreenDialog", "Full screen"),
                dialog("fullscreenDialog", "Full screen dialog", "This covers the whole viewport.", " fullscreen", footer=False),
                trigger("fullscreenLgDialog", "Full screen below lg"),
                dialog("fullscreenLgDialog", "Full screen below lg", "Fullscreen below 1024px.", ' fullscreen="lg"', footer=False),
            ),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "javascript",
            "title": "JavaScript",
            "intro": "<code>show()</code>, <code>hide()</code> and <code>toggle()</code> return promises; the "
            "cancelable <code>ui-dialog:show</code> / <code>ui-dialog:hide</code> can stop them.",
            "script": lines(
                'const dialog = document.querySelector("#myDialog");',
                'dialog.addEventListener("ui-dialog:show", () => loadContent());',
                'dialog.addEventListener("ui-dialog:hidden", () => form.reset());',
                "",
                'await dialog.show({ backdrop: "static" });',
                "await dialog.hide();",
            ),
        },
    ],
    "elements": [
        {
            "tag": "ui-dialog",
            "attributes": [
                ("open", "boolean", "Shown; reflected."),
                ("heading", "string", "Title (or the slot <code>heading</code>); adds the header with a close button."),
                ("no-close / close-label", "", "Header without close button / its accessible name."),
                ("size", "string", "<code>sm</code>, <code>lg</code> or <code>xl</code>."),
                ("fullscreen", "string", "Empty: always; <code>sm</code> … <code>2xl</code>: below that breakpoint."),
                ("scrollable", "boolean", "The body scrolls."),
                ("animation", "string", "<code>instant</code>, <code>slide-down</code>, <code>slide-up</code> (default: fade)."),
                ("backdrop", "string", "<code>static</code> or <code>false</code>."),
                ("keyboard", "string", "<code>false</code>: Escape does not close it."),
                ("modal", "string", "<code>false</code>: non-modal."),
            ],
            "slots": [("(default)", "The body."), ("heading", "The title."), ("footer", "Footer buttons.")],
            "parts": [("dialog", "The native <code>&lt;dialog class=\"dialog\"&gt;</code>."),
                      ("header, title, close, body, footer", "Its parts.")],
            "events": [
                ("ui-dialog:show / ui-dialog:hide", "Before opening / closing; cancelable."),
                ("ui-dialog:shown / ui-dialog:hidden", "After the animation."),
                ("ui-dialog:hide-prevented", "A close was refused (static backdrop, keyboard false)."),
                ("ui-dialog:cancel", "Escape was pressed."),
            ],
            "methods": [
                ("show(options) / hide() / toggle(options)", "Promises; options <code>{ backdrop, keyboard, modal }</code>."),
                ("isOpen", "Shown (read only)."),
            ],
        }
    ],
    "notes": ["<code>ui-modal</code> (Bootstrap 5) is replaced by <code>ui-dialog</code>."],
    "tokens": {"host": "ui-dialog", "example_token": "--bs-dialog-border-radius", "example_value": "var(--bs-radius-3)"},
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["dialog"]
