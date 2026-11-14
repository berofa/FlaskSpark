import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { morph } from "../../../core/morph.js";
import { BOOTSTRAP_SHADOW_STYLES, themeColor } from "../shadow-styles.js";

const SIZES = new Set(["xs", "sm", "lg", "xl"]);
const STATUS = { online: "Online", offline: "Offline", busy: "Busy", away: "Away" };

/**
 * <ui-avatar> (Bootstrap 6 avatar, new in v6): a user or entity as an image, or initials (the content).
 *
 * Attributes: src (+ alt), variant (theme colour of initials), subtle (light theme colour), size (xs, sm, lg, xl),
 * status (online, offline, busy, away; status-label names it, default the status in English).
 * In a <ui-avatar-stack> the avatars overlap. Parts: avatar, img, status.
 */
export class UiAvatar extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-avatar.css", import.meta.url).href];
  static observedAttributes = ["src", "alt", "variant", "subtle", "size", "status", "status-label", "stacked", "stack-last"];

  renderShadow() {
    morph(this.shadowRoot, this.render());
  }

  render() {
    const variant = themeColor(this.getAttribute("variant"));
    const size = SIZES.has(this.getAttribute("size")) ? `avatar-${this.getAttribute("size")}` : "";
    const classes = ["avatar", HOST_TOKENS_CLASS, size, variant ? `theme-${variant}` : "", this.hasAttribute("subtle") ? "avatar-subtle" : "",
      this.hasAttribute("stacked") ? "ui-avatar-stacked" : "", this.hasAttribute("stack-last") ? "ui-avatar-stack-last" : ""].filter(Boolean).join(" ");
    const src = this.getAttribute("src");
    const content = src ? `<img class="avatar-img" part="img" src="${escapeHtml(src)}" alt="${escapeHtml(this.getAttribute("alt") || "")}">` : "<slot></slot>";
    const status = STATUS[this.getAttribute("status")];
    const badge = status ? `<span class="avatar-status status-${this.getAttribute("status")}" part="status" role="img" `
      + `aria-label="${escapeHtml(this.getAttribute("status-label") || status)}"></span>` : "";
    return `<span class="${classes}" part="avatar">${content}${badge}</span>`;
  }
}

/**
 * <ui-avatar-stack> (Bootstrap 6 .avatar-stack): <ui-avatar> children overlapping, the first on top, lifted on
 * hover. size (xs, sm, lg, xl) applies to every avatar without its own. Parts: stack.
 */
export class UiAvatarStack extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-avatar.css", import.meta.url).href];
  static observedAttributes = ["size"];

  #observer = null;

  connectedCallback() {
    super.connectedCallback();
    this.#observer ??= new MutationObserver(() => this.#mark());
    this.#observer.observe(this, { childList: true });
  }

  disconnectedCallback() {
    this.#observer?.disconnect();
  }

  render() {
    return '<div class="ui-avatar-stack" part="stack"><slot></slot></div>';
  }

  afterRender() {
    this.#mark();
  }

  /** The avatars of the stack get its look (ring, overlap) and its size (unless they have their own). */
  #mark() {
    const size = this.getAttribute("size");
    const avatars = [...this.children].filter((child) => child.localName === "ui-avatar");
    avatars.forEach((avatar, index) => {
      if (!avatar.hasAttribute("stacked")) avatar.setAttribute("stacked", "");
      avatar.toggleAttribute("stack-last", index === avatars.length - 1);
      const fromStack = avatar.dataset.stackSize !== undefined;
      if (size && (fromStack || !avatar.hasAttribute("size")) && avatar.getAttribute("size") !== size) {
        avatar.dataset.stackSize = size;
        avatar.setAttribute("size", size);
      }
    });
  }
}

registerComponent("ui-avatar", UiAvatar);
registerComponent("ui-avatar-stack", UiAvatarStack);
