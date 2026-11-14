import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { FormControlElement } from "../../../core/form-control-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { assignItemSlots } from "../../../core/slotted-items.js";
import { BOOTSTRAP_SHADOW_STYLES } from "../shadow-styles.js";
import { ComboboxController, installComboboxDataApi } from "./combobox-controller.js";

const CARET = '<svg class="combobox-caret" part="caret" width="10" height="16" viewBox="0 0 10 16" fill="none" aria-hidden="true">'
  + '<path d="M.47 5.47a.75.75 0 0 1 1.06 0L5 8.94l3.47-3.47a.75.75 0 1 1 1.06 1.06l-4 4a.75.75 0 0 1-1.06 0l-4-4a.75.75 0 0 1 0-1.06Z" fill="currentcolor"/></svg>';
const CHECK = '<svg class="menu-item-check" part="check" width="16" height="16" fill="none" stroke="currentColor" stroke-linecap="round" '
  + 'stroke-linejoin="round" stroke-width="2" viewBox="0 0 16 16" aria-hidden="true"><path d="m2 7 4 5 8-8"/></svg>';

/**
 * <ui-combobox> (Bootstrap 6 combobox, new in v6): a select-like field whose options are your own markup (icons,
 * descriptions, badges), with search, check marks and multiple selection; on the menu plugin (top layer, keyboard).
 * Form-associated like ui-input (label, help, name, required, disabled, error, size …, see FormControlElement);
 * multiple submits every value under the name (like a multiple select).
 *
 * Options: <ui-option value [selected] [disabled] [description] [label]> children, their content slotted into the
 * menu item (label: the text in the field; default the option's text). <ui-option header> is a group heading,
 * <ui-option divider> a line.
 * Attributes: value (initial; several comma-separated), multiple, placeholder, search (a search field;
 * search-placeholder, no-results-label), normalize (search ignores accents), check (check marks), placement
 * ("bottom-start"), count-label ("{n} selected").
 * Properties: value (get / set), values (array). Methods: show(), hide(), toggle().
 * Events: ui-combobox:show / hide (cancelable), shown / hidden, ui-combobox:change {value, item}; change, input.
 * Parts: field, label, control (the toggle), value, caret, menu, item, check, search, no-results, help, feedback.
 */
export class UiCombobox extends FormControlElement {
  static stylesheets = [
    ...BOOTSTRAP_SHADOW_STYLES,
    new URL("../form-field.css", import.meta.url).href,
    new URL("./ui-combobox.css", import.meta.url).href,
  ];
  static observedAttributes = [...FormControlElement.sharedAttributes, "multiple", "search", "search-placeholder", "no-results-label",
    "normalize", "check", "placement", "count-label"];

  #controller = null;
  #options = [];
  #values = null; // chosen values once changed; null: the value attribute
  #observer = null;

  constructor() {
    super();
    this.validator = () => (this.hasAttribute("required") && !this.values.length ? "Pflichtfeld" : "");
  }

  connectedCallback() {
    super.connectedCallback();
    this.#observer ??= new MutationObserver(() => this.requestRender());
    this.#observer.observe(this, { childList: true, attributes: true, subtree: true,
      attributeFilter: ["value", "selected", "disabled", "description", "label", "header", "divider"] });
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.#observer?.disconnect();
    this.#controller?.hide();
  }

  get #initialValues() {
    const attribute = this.getAttribute("value");
    if (attribute !== null) return attribute.split(",").map((v) => v.trim()).filter(Boolean);
    return [...this.querySelectorAll(":scope > ui-option[selected]")].map((option) => option.getAttribute("value") ?? "");
  }

  /** The chosen values (array). */
  get values() {
    if (this.#controller) return [this.#controller.value].flat().filter((v) => v !== "");
    return [...(this.#values ?? this.#initialValues)];
  }

  get value() {
    return this.values.join(",");
  }

  set value(value) {
    this.#values = String(value ?? "").split(",").map((v) => v.trim()).filter(Boolean);
    if (!this.hasAttribute("multiple")) this.#values = this.#values.slice(0, 1);
    this.#controller?.select(this.#values);
    this.syncFormState();
  }

  formValue() {
    const values = this.values;
    if (!values.length || !this.name) return null;
    if (!this.hasAttribute("multiple")) return values[0];
    const data = new FormData();
    values.forEach((value) => data.append(this.name, value));
    return data;
  }

  get renderValue() {
    return null;
  }

  renderControl(attrs, classes) {
    this.#options = assignItemSlots(this, "ui-option", "option");
    const selected = new Set(this.#values ?? this.#initialValues);
    const check = this.hasAttribute("check") ? CHECK : "";
    const items = this.#options.map((option, index) => {
      if (option.hasAttribute("divider")) return '<hr class="menu-divider">';
      if (option.hasAttribute("header")) return `<h6 class="menu-header" part="header"><slot name="option-${index}"></slot></h6>`;
      const value = option.getAttribute("value") ?? option.textContent.trim();
      const description = option.getAttribute("description");
      const disabled = option.hasAttribute("disabled");
      const content = description
        ? `<span class="menu-item-content"><span><slot name="option-${index}"></slot></span><small class="menu-item-description">${escapeHtml(description)}</small></span>`
        : `<span class="ui-combobox-label"><slot name="option-${index}"></slot></span>`;
      return `<button type="button" class="menu-item${selected.has(value) ? " selected" : ""}" part="item" data-index="${index}" `
        + `data-bs-value="${escapeHtml(value)}"${disabled ? " disabled" : ""}>${content}${check}</button>`;
    }).join("");
    const search = this.hasAttribute("search")
      ? `<div class="combobox-search"><input type="text" class="form-control combobox-search-input" part="search" autocomplete="off" `
        + `placeholder="${escapeHtml(this.getAttribute("search-placeholder") || "Search…")}" aria-label="${escapeHtml(this.getAttribute("search-placeholder") || "Search…")}"></div>`
      : "";
    const noResults = this.hasAttribute("search")
      ? `<div class="combobox-no-results d-none" part="no-results">${escapeHtml(this.getAttribute("no-results-label") || "No results found")}</div>` : "";
    return `<button type="button" class="${classes} combobox-toggle" id="control" part="control" data-control ${attrs}>`
      + `<span class="combobox-value" part="value"></span>${CARET}</button>`
      + `<div class="menu ${HOST_TOKENS_CLASS}" part="menu">${search}${items}${noResults}</div>`;
  }

  afterRender() {
    super.afterRender();
    const toggle = this.control;
    const menu = this.shadowRoot.querySelector(".menu");
    const countLabel = this.getAttribute("count-label");
    this.#controller = new ComboboxController(toggle, menu, {
      multiple: this.hasAttribute("multiple"),
      placeholder: this.getAttribute("placeholder") || "",
      search: this.hasAttribute("search"),
      searchNormalize: this.hasAttribute("normalize"),
      placement: this.getAttribute("placement") || "bottom-start",
      countLabel: (n) => (countLabel || "{n} selected").replace("{n}", String(n)),
      labelOf: (item) => {
        const option = this.#options[Number(item.dataset.index)];
        return option?.getAttribute("label") || option?.textContent.trim() || "";
      },
      textOf: (item) => this.#options[Number(item.dataset.index)]?.textContent || "",
      emit: (name, detail, cancelable) => {
        const result = this.dispatchEvent(new CustomEvent(`ui-combobox:${name}`, { bubbles: true, cancelable, detail }));
        if (name === "change") {
          this.#values = [detail.value].flat();
          this.syncFormState();
          this.dispatchEvent(new Event("input", { bubbles: true, composed: true }));
          this.dispatchEvent(new Event("change", { bubbles: true }));
        }
        return result;
      },
    });
    toggle.addEventListener("click", () => this.#controller.toggleMenu());
    this.syncFormState();
  }

  show() {
    this.#controller?.show();
  }

  hide() {
    this.#controller?.hide();
  }

  toggle() {
    this.#controller?.toggleMenu();
  }

  formResetCallback() {
    this.#values = null;
    this.requestRender();
  }
}

/** One option of a <ui-combobox> (its content is shown in the menu). */
export class UiOption extends HTMLElement {}

registerComponent("ui-combobox", UiCombobox);
registerComponent("ui-option", UiOption);
installComboboxDataApi();
