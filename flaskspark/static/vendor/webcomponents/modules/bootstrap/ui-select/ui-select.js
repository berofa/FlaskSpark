import { registerComponent } from "../../../core/registry.js";
import { FormControlElement } from "../../../core/form-control-element.js";
import { BOOTSTRAP_SHADOW_STYLES } from "../shadow-styles.js";

const CARET = '<svg class="ui-caret" part="caret" viewBox="0 0 16 16" aria-hidden="true"><path fill="none" '
  + 'stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m2 5 6 6 6-6"/></svg>';

/**
 * <ui-select> (Bootstrap 6: a <select> styled with .form-control), form-associated.
 *
 * Options are declared as light-DOM <option> / <optgroup> children and mirrored into the shadow <select>;
 * changes to the children re-render it.
 *
 * Attributes (besides those of every text field, see FormControlElement: label, help, size, floating,
 * prefix/suffix, error, valid-feedback, tooltip, …):
 * - value: initial value; otherwise the option marked "selected".
 * - multiple: several options (the form gets each selected value under the name).
 * - rows: the visible rows of a list box (the <select>'s own size attribute; "size" sets sm / lg here).
 *
 * Properties: value, selectedValues, options, form, validity, … as ui-input. Events: input, change.
 *
 * The caret is an inline SVG in currentColor instead of Bootstrap's background image, whose dark variant is
 * chosen with [data-bs-theme], which cannot match inside the shadow tree.
 */
export class UiSelect extends FormControlElement {
  static stylesheets = [
    ...BOOTSTRAP_SHADOW_STYLES,
    new URL("../grouped.css", import.meta.url).href,
    new URL("../form-field.css", import.meta.url).href,
  ];
  static observedAttributes = [...FormControlElement.sharedAttributes, "multiple", "rows"];

  #observer = null;

  connectedCallback() {
    if (!this.#observer) {
      // Host attributes are handled by attributeChangedCallback; only react to the options.
      this.#observer = new MutationObserver((records) => {
        if (records.some((record) => record.target !== this || record.type === "childList")) {
          this.requestRender();
        }
      });
    }
    this.#observer.observe(this, { childList: true, subtree: true, characterData: true, attributes: true });
    super.connectedCallback();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.#observer?.disconnect();
  }

  get options() {
    return Array.from(this.control?.options ?? []);
  }

  get selectedValues() {
    return this.options.filter((option) => option.selected).map((option) => option.value);
  }

  formValue(control) {
    if (!control.multiple) {
      return control.value;
    }
    const data = new FormData();
    this.selectedValues.forEach((value) => data.append(this.name, value));
    return data;
  }

  renderControl(attrs, classes) {
    // Options come from the author's light-DOM markup; outerHTML re-serializes
    // parsed nodes (escaped by the serializer), so no raw string is injected.
    const options = Array.from(this.children)
      .filter((child) => child.localName === "option" || child.localName === "optgroup")
      .map((child) => child.outerHTML)
      .join("");
    const multiple = this.hasAttribute("multiple") ? " multiple" : "";
    const rows = Number.parseInt(this.getAttribute("rows") || "", 10);
    const select = `<select class="${classes}" id="control" part="control" data-control${multiple}`
      + `${rows > 1 ? ` size="${rows}"` : ""} ${attrs}>${options}</select>${CARET}`;
    // With a floating label the .form-floating wrapper holds the caret (Bootstrap reads label:has(~ select)).
    return this.floatingClass ? select : `<div class="ui-caret-wrap">${select}</div>`;
  }

  get floatingClass() {
    return this.hasAttribute("floating") && this.getAttribute("label") ? "ui-caret-wrap" : "";
  }
}

registerComponent("ui-select", UiSelect);
