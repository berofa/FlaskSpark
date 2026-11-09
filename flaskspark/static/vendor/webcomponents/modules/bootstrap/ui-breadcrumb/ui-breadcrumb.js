import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";

/**
 * <ui-breadcrumb> container.
 *
 * Attributes:
 * - label: aria-label of the nav landmark (default "Breadcrumb").
 *
 * The divider is inherited via --bs-breadcrumb-divider on the host.
 */
export class UiBreadcrumb extends ShadowComponentElement {
  static stylesheet = new URL("./ui-breadcrumb.css", import.meta.url).href;
  static observedAttributes = ["label"];

  render() {
    const label = this.getAttribute("label") || "Breadcrumb";
    return `
      <nav aria-label="${escapeHtml(label)}">
        <ol class="breadcrumb">
          <slot></slot>
        </ol>
      </nav>
    `;
  }
}

/**
 * <ui-breadcrumb-item>.
 *
 * Attributes:
 * - href: renders the content as a link.
 * - active: current page; rendered without a link and with aria-current.
 */
export class UiBreadcrumbItem extends ShadowComponentElement {
  static stylesheet = new URL("./ui-breadcrumb.css", import.meta.url).href;
  static observedAttributes = ["href", "active"];

  render() {
    const href = this.getAttribute("href");
    const active = this.hasAttribute("active");
    const content = href && !active
      ? `<a href="${escapeHtml(href)}"><slot></slot></a>`
      : "<slot></slot>";
    return `
      <span class="breadcrumb-item${active ? " active" : ""}"${active ? ' aria-current="page"' : ""}>
        ${content}
      </span>
    `;
  }
}

registerComponent("ui-breadcrumb", UiBreadcrumb);
registerComponent("ui-breadcrumb-item", UiBreadcrumbItem);
