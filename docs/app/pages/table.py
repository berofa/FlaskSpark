"""ui-table (Bootstrap 6 tables)."""

from __future__ import annotations

from .common import THEMES, VARIANT_ATTRIBUTE, lines

HEAD = ["  <table>", "    <thead>", '      <tr><th scope="col">#</th><th scope="col">First</th><th scope="col">Last</th><th scope="col">Handle</th></tr>',
        "    </thead>"]
ROWS = [("1", "Mark", "Otto", "@mdo"), ("2", "Jacob", "Thornton", "@fat"), ("3", "John", "Doe", "@social")]


def body(rows=ROWS, row_attributes: dict[int, str] | None = None, tbody: str = "<tbody>") -> list[str]:
    result = [f"    {tbody}"]
    for index, row in enumerate(rows):
        extra = (row_attributes or {}).get(index, "")
        cells = f'<th scope="row">{row[0]}</th>' + "".join(f"<td>{cell}</td>" for cell in row[1:])
        result.append(f"      <tr{extra}>{cells}</tr>")
    result.append("    </tbody>")
    return result


def table(attributes: str = "", table_class: str = "", **kwargs) -> str:
    opening = f"<ui-table{(' ' + attributes) if attributes else ''}>"
    head = HEAD if not table_class else [f'  <table class="{table_class}">', *HEAD[1:]]
    return lines(opening, *head, *body(**kwargs), "  </table>", "</ui-table>")


STACKED = lines(
    '<ui-table stacked="md" bordered>',
    "  <table>",
    '    <thead><tr><th scope="col">Name</th><th scope="col">Type</th><th scope="col">Default</th><th scope="col">Description</th></tr></thead>',
    "    <tbody>",
    "      <tr><td>backdrop</td><td>boolean or 'static'</td><td>true</td><td>Includes a backdrop element.</td></tr>",
    "      <tr><td>keyboard</td><td>boolean</td><td>true</td><td>Closes the component when escape key is pressed.</td></tr>",
    "      <tr><td>focus</td><td>boolean</td><td>true</td><td>Puts the focus on the component when initialized.</td></tr>",
    "    </tbody>",
    "  </table>",
    "</ui-table>",
)

ICON_EDIT = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true">'
    '<path d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 '
    ".11-.168zM11.207 2.5 13.5 4.793 14.793 3.5 12.5 1.207zm1.586 3L10.5 3.207 4 9.707V10h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h"
    '.293zm-9.761 5.175-.106.106-1.528 3.821 3.821-1.528.106-.106A.5.5 0 0 1 5 12.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.468-.325"/></svg>'
)
ICON_DELETE = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true">'
    '<path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m3 '
    '.5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0z"/><path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 '
    '0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4zM2.5 '
    '3h11V2h-11z"/></svg>'
)


def icon_row(name: str, role: str) -> str:
    buttons = (f'<ui-button icon size="sm" variant="secondary" appearance="outline" label="Edit {name}">{ICON_EDIT}</ui-button> '
               f'<ui-button icon size="sm" variant="danger" appearance="outline" label="Delete {name}">{ICON_DELETE}</ui-button>')
    return f"      <tr><td>{name}</td><td>{role}</td><td>{buttons}</td></tr>"


ICONS = lines(
    '<ui-table valign="middle" stacked="sm">',
    "  <table>",
    '    <thead><tr><th scope="col">Name</th><th scope="col">Role</th><th scope="col" class="table-icons"><span class="visually-hidden">Actions</span></th></tr></thead>',
    "    <tbody>",
    icon_row("Mark", "Owner"),
    icon_row("Jacob", "Editor"),
    "    </tbody>",
    "  </table>",
    "</ui-table>",
)

PAGE = {
    "title": "ui-table",
    "summary": "Bootstrap's table styles for your own table markup: theme variants, accents, borders, sizes, card-like, "
    "responsive and stacked layouts.",
    "submodule": "ui-table",
    "entry": "modules/bootstrap/ui-table/ui-table.js",
    "sections": [
        {
            "id": "overview",
            "title": "Overview",
            "intro": "Put a plain <code>&lt;table&gt;</code> into <code>&lt;ui-table&gt;</code>; the component moves it into "
            "its shadow tree (rows cannot be slotted) and applies <code>.table</code>. Use the <code>table</code> property "
            "to reach it from script.",
            "html": table(),
        },
        {
            "id": "variants",
            "title": "Variants",
            "intro": "<code>variant</code> themes the whole table; a <code>theme-*</code> class on a row or cell themes just that.",
            "html": lines(
                *[line for name in ["primary", "success"] for line in table(f'variant="{name}"').splitlines()],
                "<ui-table>",
                "  <table>",
                '    <tbody>',
                *[f'      <tr class="theme-{name}"><th scope="row">{name.capitalize()}</th><td>Cell</td><td>Cell</td></tr>' for name in THEMES],
                "    </tbody>",
                "  </table>",
                "</ui-table>",
            ),
        },
        {
            "id": "striped",
            "title": "Striped rows and columns",
            "intro": "<code>striped</code> zebra-stripes the rows, <code>striped-columns</code> the columns; both combine with a variant.",
            "html": lines(table("striped"), table("striped-columns"), table('striped variant="success"')),
        },
        {
            "id": "hover-active",
            "title": "Hoverable rows and active tables",
            "intro": "<code>hover</code> highlights the row under the pointer; <code>.table-active</code> on a row or cell highlights it.",
            "html": lines(table("hover", row_attributes={0: ' class="table-active"'})),
        },
        {
            "id": "borders",
            "title": "Borders",
            "intro": "<code>bordered</code> draws all borders (colour them with a <code>border-*</code> class on the table), "
            "<code>borderless</code> none.",
            "html": lines(table("bordered"), table("bordered", table_class="border-primary"), table("borderless")),
        },
        {
            "id": "card",
            "title": "Card-like tables",
            "intro": "<code>card</code> rounds the corners like a card, clips the cell backgrounds and drops the last bottom border.",
            "html": lines(table("card hover"), table("card striped responsive")),
        },
        {
            "id": "small",
            "title": "Small tables",
            "intro": "<code>size=\"sm\"</code> halves the cell padding.",
            "html": table('size="sm"'),
        },
        {
            "id": "group-divider",
            "title": "Group dividers and alignment",
            "intro": "<code>.table-group-divider</code> on a <code>&lt;tbody&gt;</code> draws a thicker border; "
            "<code>valign</code> sets the vertical alignment (or <code>align-*</code> on rows and cells).",
            "html": table('valign="middle"', tbody='<tbody class="table-group-divider">'),
        },
        {
            "id": "icons",
            "title": "Icon column",
            "intro": "<code>class=\"table-icons\"</code> on a column header makes a column for icon buttons: as narrow as "
            "its buttons, right-aligned and never wrapping; the component copies the class to the cells of that column "
            "(also to rows added later). In stacked rows the buttons line up with the values.",
            "html": ICONS,
        },
        {
            "id": "caption",
            "title": "Caption and footer",
            "intro": "A <code>&lt;caption&gt;</code> works like a heading (<code>caption-top</code> on the table puts it on top); "
            "<code>&lt;tfoot&gt;</code> as usual.",
            "html": lines(
                "<ui-table>",
                '  <table class="caption-top">',
                "    <caption>List of users</caption>",
                *HEAD[1:],
                *body(),
                '    <tfoot><tr><td colspan="3">Footer</td><td>3 users</td></tr></tfoot>',
                "  </table>",
                "</ui-table>",
            ),
        },
        {
            "id": "stacked",
            "title": "Stacked tables",
            "intro": "<code>stacked</code> turns rows into blocks: the first cell is the title, the others label–value pairs. "
            "With a breakpoint (<code>stacked=\"md\"</code>) only below that container width (resize the window). Cells "
            "without <code>data-cell</code> take the label of their column header.",
            "html": STACKED,
        },
        {
            "id": "responsive",
            "title": "Responsive tables",
            "intro": "<code>responsive</code> scrolls wide tables horizontally; <code>responsive=\"lg\"</code> only below that "
            "breakpoint. The wrapper clips content beyond its edges (e.g. menus).",
            "html": lines(
                "<ui-table responsive>",
                "  <table>",
                "    <thead><tr><th>#</th>" + "".join("<th>Heading</th>" for _ in range(9)) + "</tr></thead>",
                "    <tbody><tr><th>1</th>" + "".join("<td>Cell</td>" for _ in range(9)) + "</tr></tbody>",
                "  </table>",
                "</ui-table>",
            ),
        },
    ],
    "tokens": {"host": "ui-table", "example_token": "--bs-table-cell-padding-x", "example_value": "1rem"},
    "elements": [
        {
            "tag": "ui-table",
            "attributes": [
                VARIANT_ATTRIBUTE,
                ("size", "string", "<code>sm</code>: compact cells."),
                ("striped / striped-columns / hover", "boolean", "Accents."),
                ("bordered / borderless", "boolean", "Borders."),
                ("valign", "string", "<code>top</code>, <code>middle</code> or <code>bottom</code>."),
                ("card", "boolean", "Card-like wrapper (<code>.table-card</code>)."),
                ("responsive", "boolean / string", "Horizontal scrolling, or below <code>sm</code> … <code>2xl</code>."),
                ("stacked", "boolean / string", "Stacked rows, or below a container width <code>sm</code> … <code>2xl</code>."),
            ],
            "slots": [("(default)", "One <code>&lt;table&gt;</code> (moved into the shadow tree).")],
            "parts": [("wrapper", "The wrapper (responsive / card)."), ("table", "The table.")],
            "methods": [("table", "The managed table element (read only).")],
        }
    ],
    "notes": ["Page CSS does not reach the moved table; Bootstrap's classes (utilities, <code>table-active</code>, "
              "<code>theme-*</code>, <code>align-*</code>) do.",
              "<code>table-icons</code> on a header or a single cell: icon column (narrow, right-aligned, no wrapping).",
              "<code>--ui-table-head-color</code> and <code>--ui-table-head-font-weight</code> on the host style the head "
              "cells; <code>--ui-table-last-row-border-width: 0</code> drops the bottom border of the last row."],
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["table"]
