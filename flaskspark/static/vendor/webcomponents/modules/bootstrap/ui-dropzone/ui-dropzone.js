import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { formatSize, parseSize, selectFiles } from "../../../core/files.js";
import { BOOTSTRAP_SHADOW_STYLES, themeColor } from "../shadow-styles.js";

const UPLOAD = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true">'
  + '<path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5"/>'
  + '<path d="M7.646 1.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1-.708.708L8.5 2.707V11.5a.5.5 0 0 1-1 0V2.707L5.354 4.854a.5.5 0 1 1-.708-.708z"/></svg>';
const REMOVE = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" '
  + 'stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="4" y1="4" x2="12" y2="12"/><line x1="12" y1="4" x2="4" y2="12"/></svg>';

/**
 * <ui-dropzone>: an area to drop files on, pick them with the file dialog (click, Enter, Space) or paste them.
 * Not a Bootstrap component: built on Bootstrap 6's form field (label, help, feedback) and tokens, themed with
 * its own --ui-dropzone-* tokens.
 *
 * Two ways to use it:
 * - Hand-over (default): every accepted pick fires ui-dropzone:files; uploading is the page's job.
 * - Form field (`name`): the picked files are listed (with remove buttons) and submitted with the form like
 *   <input type="file" name multiple>; required needs one file.
 *
 * Attributes:
 * - accept (like <input type="file" accept>), multiple, max-files (in total), max-size ("10MB", "500KB", bytes).
 * - variant: theme colour of the drag-over state. disabled.
 * - label (above, .form-label), text (in the area, default "Drop files here or click to choose"), hint (second
 *   line in the area), help (.form-text), remove-label ("Remove"), error (a message shown as invalid).
 * - Messages of rejected files: type-message, size-message, count-message ({name}, {size}, {max} filled in).
 * Slots: default (replaces icon, text and hint), icon.
 * Events (bubble, composed): ui-dropzone:files {files} (accepted, after a drop / pick / paste),
 * ui-dropzone:reject {rejected: [{file, reason: "type" | "size" | "count"}]}, ui-dropzone:change {files}
 * (form field: the chosen files changed), plus `change`.
 * Methods / properties: open(), files (form field: the chosen files), clear(), remove(index).
 * Parts: field, label, zone, icon, text, hint, list, file, file-name, file-size, remove, help, feedback.
 */
export class UiDropzone extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-dropzone.css", import.meta.url).href];
  static formAssociated = true;
  static observedAttributes = ["accept", "multiple", "max-files", "max-size", "variant", "disabled", "label", "text", "hint", "help",
    "remove-label", "error", "name", "required", "type-message", "size-message", "count-message"];

  #internals;
  #depth = 0;
  #files = [];
  #message = "";
  #formDisabled = false;

  constructor() {
    super();
    this.#internals = this.attachInternals();
  }

  get disabled() {
    return this.hasAttribute("disabled") || this.#formDisabled;
  }

  set disabled(value) {
    this.toggleAttribute("disabled", Boolean(value));
  }

  /** The chosen files (form field). */
  get files() {
    return [...this.#files];
  }

  get name() {
    return this.getAttribute("name") || "";
  }

  get form() {
    return this.#internals.form;
  }

  get validity() {
    return this.#internals.validity;
  }

  checkValidity() {
    return this.#internals.checkValidity();
  }

  reportValidity() {
    return this.#internals.reportValidity();
  }

  #isField() {
    return this.hasAttribute("name");
  }

  render() {
    const disabled = this.disabled;
    const text = this.getAttribute("text") ?? "Drop files here or click to choose";
    const hint = this.getAttribute("hint");
    const variant = themeColor(this.getAttribute("variant"));
    const label = this.getAttribute("label") ? `<label class="form-label" part="label" id="label">${escapeHtml(this.getAttribute("label"))}</label>` : "";
    const help = this.getAttribute("help") ? `<div class="form-text" part="help" id="help">${escapeHtml(this.getAttribute("help"))}</div>` : "";
    const error = this.getAttribute("error") || this.#message;
    const list = this.#isField() && this.#files.length
      ? `<ul class="ui-dropzone-list list-unstyled" part="list">${this.#files.map((file, index) => `<li class="ui-dropzone-file" part="file">`
        + `<span class="ui-dropzone-file-name" part="file-name">${escapeHtml(file.name)}</span>`
        + `<span class="ui-dropzone-file-size" part="file-size">${formatSize(file.size)}</span>`
        + `<button type="button" class="btn-icon btn-sm btn-text" part="remove" data-remove="${index}"${disabled ? " disabled" : ""} `
        + `aria-label="${escapeHtml(`${this.getAttribute("remove-label") || "Remove"}: ${file.name}`)}">${REMOVE}</button></li>`).join("")}</ul>` : "";
    const describedBy = [help ? "help" : "", error ? "feedback" : ""].filter(Boolean).join(" ");
    return `<div class="form-field" part="field">${label}`
      + `<div part="zone" class="ui-dropzone${variant ? ` theme-${variant}` : ""}${error ? " is-invalid" : ""}" role="button" `
      + `tabindex="${disabled ? -1 : 0}" aria-disabled="${disabled}"${label ? ' aria-labelledby="label"' : ""}`
      + `${describedBy ? ` aria-describedby="${describedBy}"` : ""}>`
      + `<slot><span class="ui-dropzone-icon" part="icon"><slot name="icon">${UPLOAD}</slot></span>`
      + `<span class="ui-dropzone-text" part="text">${escapeHtml(text)}</span>`
      + `${hint ? `<span class="ui-dropzone-hint" part="hint">${escapeHtml(hint)}</span>` : ""}</slot></div>`
      + `${list}${help}<div class="invalid-feedback" part="feedback" id="feedback"${error ? ' style="display: block"' : ""}>${escapeHtml(error)}</div>`
      + `<input type="file" hidden${this.hasAttribute("multiple") ? " multiple" : ""} accept="${escapeHtml(this.getAttribute("accept") || "")}"></div>`;
  }

  afterRender() {
    const zone = this.shadowRoot.querySelector(".ui-dropzone");
    const input = this.shadowRoot.querySelector("input");
    zone.addEventListener("click", () => this.open());
    zone.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        this.open();
      }
    });
    zone.addEventListener("paste", (event) => {
      const files = [...(event.clipboardData?.files || [])];
      if (files.length) {
        event.preventDefault();
        this.add(files);
      }
    });
    input.addEventListener("change", () => {
      this.add([...input.files]);
      input.value = ""; // the same file can be picked again
    });
    zone.addEventListener("dragenter", (event) => {
      if (!this.#hasFiles(event)) return;
      event.preventDefault();
      this.#depth += 1;
      zone.classList.toggle("is-over", !this.disabled);
    });
    zone.addEventListener("dragover", (event) => {
      if (!this.#hasFiles(event)) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = this.disabled ? "none" : "copy";
    });
    zone.addEventListener("dragleave", () => {
      this.#depth = Math.max(0, this.#depth - 1);
      if (!this.#depth) zone.classList.remove("is-over");
    });
    zone.addEventListener("drop", (event) => {
      if (!this.#hasFiles(event)) return;
      event.preventDefault();
      this.#depth = 0;
      zone.classList.remove("is-over");
      this.add([...event.dataTransfer.files]);
    });
    this.shadowRoot.querySelector(".ui-dropzone-list")?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-remove]");
      if (button) {
        this.remove(Number(button.dataset.remove));
        zone.focus();
      }
    });
    this.#sync();
  }

  open() {
    if (!this.disabled) this.shadowRoot.querySelector("input")?.click();
  }

  #hasFiles(event) {
    return [...(event.dataTransfer?.types || [])].includes("Files");
  }

  /** Hands files over as if they were dropped (filters them like a drop). */
  add(files) {
    if (this.disabled) return;
    const { accepted, rejected } = selectFiles(files, {
      accept: this.getAttribute("accept"),
      maxSize: parseSize(this.getAttribute("max-size")),
      maxFiles: Number.parseInt(this.getAttribute("max-files"), 10) || null,
      multiple: this.hasAttribute("multiple"),
      existing: this.#isField() && this.hasAttribute("multiple") ? this.#files.length : 0,
    });
    this.#message = rejected.length ? this.#rejectMessage(rejected[0]) : "";
    if (rejected.length) {
      this.dispatchEvent(new CustomEvent("ui-dropzone:reject", { bubbles: true, composed: true, detail: { rejected } }));
    }
    if (accepted.length) {
      this.dispatchEvent(new CustomEvent("ui-dropzone:files", { bubbles: true, composed: true, detail: { files: accepted } }));
      if (this.#isField()) {
        this.#files = this.hasAttribute("multiple") ? [...this.#files, ...accepted] : accepted.slice(0, 1);
        this.#changed();
        return;
      }
    }
    this.requestRender();
  }

  remove(index) {
    if (index < 0 || index >= this.#files.length) return;
    this.#files.splice(index, 1);
    this.#message = "";
    this.#changed();
  }

  clear() {
    this.#files = [];
    this.#message = "";
    this.#changed();
  }

  #changed() {
    this.requestRender();
    this.dispatchEvent(new CustomEvent("ui-dropzone:change", { bubbles: true, composed: true, detail: { files: this.files } }));
    this.dispatchEvent(new Event("change", { bubbles: true }));
  }

  #rejectMessage({ file, reason }) {
    const defaults = {
      type: "{name}: this file type is not allowed.",
      size: "{name} is too large ({size}, at most {max}).",
      count: "Too many files (at most {max}).",
    };
    const max = reason === "size" ? formatSize(parseSize(this.getAttribute("max-size"))) : (this.getAttribute("max-files") || "1");
    return (this.getAttribute(`${reason}-message`) || defaults[reason])
      .replaceAll("{name}", file.name).replaceAll("{size}", formatSize(file.size)).replaceAll("{max}", max);
  }

  #sync() {
    const zone = this.shadowRoot.querySelector(".ui-dropzone");
    if (this.#isField() && this.#files.length) {
      const data = new FormData();
      this.#files.forEach((file) => data.append(this.name, file));
      this.#internals.setFormValue(data);
    } else {
      this.#internals.setFormValue(null);
    }
    const error = this.getAttribute("error");
    if (error) {
      this.#internals.setValidity({ customError: true }, error, zone);
    } else if (this.hasAttribute("required") && this.#isField() && !this.#files.length) {
      this.#internals.setValidity({ valueMissing: true }, "Pflichtfeld", zone);
    } else {
      this.#internals.setValidity({});
    }
  }

  formResetCallback() {
    this.#files = [];
    this.#message = "";
    this.requestRender();
  }

  formDisabledCallback(disabled) {
    this.#formDisabled = disabled;
    this.requestRender();
  }
}

registerComponent("ui-dropzone", UiDropzone);
