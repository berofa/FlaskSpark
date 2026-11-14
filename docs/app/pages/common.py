"""Shared bits of the component pages."""

from __future__ import annotations

# Bootstrap 6 theme colours (site/data/theme-colors.yml), in the order of its docs.
THEMES = ["primary", "accent", "success", "danger", "warning", "info", "inverse", "secondary"]

VARIANT_ATTRIBUTE = (
    "variant",
    "string",
    "Theme colour: " + ", ".join(f"<code>{name}</code>" for name in THEMES) + ". Without one the component is neutral.",
)

ICON_WARNING = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" '
    'role="img" aria-label="Warning:"><path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 '
    "1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 "
    '1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5zm.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2z"/></svg>'
)
ICON_CHECK = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" '
    'aria-hidden="true"><path d="M12.736 3.97a.733.733 0 0 1 1.047 0c.286.289.29.756.01 1.05L7.88 12.01a.733.733 0 0 1-1.065.02L3.217 '
    "8.384a.757.757 0 0 1 0-1.06.733.733 0 0 1 1.047 0l3.052 3.093 5.4-6.425z\"/></svg>"
)
ICON_STAR = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" '
    'aria-hidden="true"><path d="M3.612 15.443c-.386.198-.824-.149-.746-.592l.83-4.73L.173 6.765c-.329-.314-.158-.888.283-.95l4.898-.696'
    "L7.538.792c.197-.39.73-.39.927 0l2.184 4.327 4.898.696c.441.062.612.636.282.95l-3.522 3.356.83 4.73c.078.443-.36.79-.746.592L8 "
    '13.187l-4.389 2.256z"/></svg>'
)


def placeholder(text: str, height: int = 180, slot: str = "", extra: str = "") -> str:
    """A grey placeholder image (SVG) like the ones in Bootstrap's docs."""
    slot_attr = f' slot="{slot}"' if slot else ""
    return (
        f'<svg{slot_attr}{extra} xmlns="http://www.w3.org/2000/svg" width="100%" height="{height}" role="img" '
        f'aria-label="Placeholder: {text}" preserveAspectRatio="xMidYMid slice"><rect width="100%" height="100%" '
        f'fill="#868e96"></rect><text x="50%" y="50%" fill="#dee2e6" dy=".3em" text-anchor="middle">{text}</text></svg>'
    )


def lines(*parts: str) -> str:
    return "\n".join(parts)
