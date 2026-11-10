import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { observeItems } from "../../../core/slotted-items.js";
import { BOOTSTRAP_SHADOW_STYLES } from "../shadow-styles.js";

const SIZES = new Set(["xs", "sm", "lg"]);
// Children that take part in the group; a button may also sit in a <ui-tooltip> or <ui-popover>.
const MEMBERS = ["ui-button", "ui-check", "ui-button-group"];

/**
 * <ui-button-group> (Bootstrap 6 .btn-group).
 *
 * Groups <ui-button>, toggle buttons (<ui-check button>) and nested
 * <ui-button-group>s on one line or in a column (a .menu inside stays out), with
 * collapsed borders and radii. Bootstrap's .btn-group > [class*=btn-] rules
 * cannot reach into the children's shadow trees, so the group tells each child
 * its place (grouped, group-first, group-last, group-divider; see
 * ../grouped.css) and passes its size on. A nested group is first or last only
 * where it is itself.
 *
 * Attributes:
 * - vertical: stacks the buttons (.btn-group-vertical).
 * - divider: a line between the buttons (.btn-group-divider).
 * - size: xs, sm or lg for every button (.btn-group-*).
 * - label: accessible name; role: "group" (default) or "toolbar".
 * Part: group.
 */
export class UiButtonGroup extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-button-group.css", import.meta.url).href];
  static observedAttributes = ["vertical", "divider", "size", "label", "role", "grouped", "group-first", "group-last"];

  #stopObserving = null;

  connectedCallback() {
    super.connectedCallback();
    this.#stopObserving ??= observeItems(this, ["slot"], () => this.syncMembers());
  }

  disconnectedCallback() {
    this.#stopObserving?.();
    this.#stopObserving = null;
  }

  attributeChangedCallback(name, oldValue, newValue) {
    // The place in an outer group only changes the members, not the group's own markup.
    if (["grouped", "group-first", "group-last"].includes(name)) {
      this.syncMembers();
      return;
    }
    super.attributeChangedCallback(name, oldValue, newValue);
  }

  render() {
    const vertical = this.hasAttribute("vertical");
    const label = this.getAttribute("label");
    const role = this.getAttribute("role") === "toolbar" ? "toolbar" : "group";
    const classes = [vertical ? "btn-group-vertical" : "btn-group", this.hasAttribute("divider") ? "btn-group-divider" : ""];
    return `<div class="${classes.filter(Boolean).join(" ")}" part="group" role="${role}"`
      + `${label ? ` aria-label="${escapeHtml(label)}"` : ""}><slot></slot></div>`;
  }

  afterRender() {
    this.syncMembers();
  }

  get members() {
    return [...this.children].flatMap((child) => {
      if (MEMBERS.includes(child.localName)) {
        return [child];
      }
      if (child.localName === "ui-tooltip" || child.localName === "ui-popover") {
        const inner = [...child.children].find((element) => MEMBERS.includes(element.localName));
        return inner ? [inner] : [];
      }
      return [];
    });
  }

  syncMembers() {
    const orientation = this.hasAttribute("vertical") ? "vertical" : "horizontal";
    const size = (this.getAttribute("size") || "").trim().toLowerCase();
    // Inside an outer group, this group's own edges decide where its first and last members are.
    const nested = this.hasAttribute("grouped");
    const atStart = !nested || this.hasAttribute("group-first");
    const atEnd = !nested || this.hasAttribute("group-last");
    const members = this.members;
    members.forEach((member, index) => {
      setAttribute(member, "grouped", orientation);
      member.toggleAttribute("group-first", index === 0 && atStart);
      member.toggleAttribute("group-last", index === members.length - 1 && atEnd);
      member.toggleAttribute("group-divider", this.hasAttribute("divider"));
      if (SIZES.has(size)) {
        setAttribute(member, "size", size);
      }
    });
  }
}

function setAttribute(element, name, value) {
  if (element.getAttribute(name) !== value) {
    element.setAttribute(name, value);
  }
}

registerComponent("ui-button-group", UiButtonGroup);
