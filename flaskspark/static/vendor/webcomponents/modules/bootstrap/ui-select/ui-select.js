import { registerComponent } from "../../../core/registry.js";
import { FormControlElement } from "../../../core/form-control-element.js";

/**
 * <ui-select>: Bootstrap .form-select as a form-associated custom element.
 *
 * Options are declared as light-DOM <option> / <optgroup> children and
 * mirrored into the shadow <select>; changes to the children re-render it.
 *
 * Attributes:
 * - name, value (initial value; otherwise the option marked "selected"),
 *   label, help, size ("sm" | "lg"), disabled, required, autocomplete.
 *
 * Properties and events as ui-input.
 *
 * The dropdown caret is an inline SVG in currentColor instead of Bootstrap's
 * background image, whose dark-mode variant is selected via
 * [data-bs-theme] and cannot match inside the shadow tree.
 */
export class UiSelect extends FormControlElement {
  static stylesheet = new URL("./ui-select.css", import.meta.url).href;
  static observedAttributes = FormControlElement.sharedAttributes;

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
    this.#observer?.disconnect();
  }

  get options() {
    return Array.from(this.control?.options ?? []);
  }

  renderControl(attrs) {
    // Options come from the author's light-DOM markup; outerHTML re-serializes
    // parsed nodes (escaped by the serializer), so no raw string is injected.
    const options = Array.from(this.children)
      .filter((child) => child.localName === "option" || child.localName === "optgroup")
      .map((child) => child.outerHTML)
      .join("");
    return `
      <div class="ui-select">
        <select
          class="form-select${this.sizeClass("form-select")}"
          id="control"
          part="control"
          data-control
          ${attrs}
        >${options}</select>
        <svg class="ui-select__caret" part="caret" viewBox="0 0 16 16" aria-hidden="true">
          <path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m2 5 6 6 6-6"/>
        </svg>
      </div>
    `;
  }
}

registerComponent("ui-select", UiSelect);
