import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { acceptsFile } from "../../../core/files.js";

/**
 * <ui-dropzone>: area to drop files on or pick them with the file dialog (click, Enter, Space). It only hands the
 * files over; uploading (and showing the progress) is the host's job. Not a Bootstrap component: styled with
 * Bootstrap's tokens.
 *
 * Attributes:
 * - accept: like <input type="file" accept> (e.g. "image/*,video/*,.pdf"); dropped files are filtered by it too.
 * - multiple: more than one file at a time (without it only the first file counts).
 * - disabled.
 * - label: text of the area (default "Dateien hierher ziehen oder klicken"), hint: second, smaller line.
 *
 * Slot: default (replaces label and hint).
 * Events: ui-dropzone:files (bubbles, composed) with detail {files: File[]} after a drop or a pick; nothing when
 *   every file was filtered out.
 * Methods: open() opens the file dialog.
 * CSS parts: zone.
 * Custom properties: --ui-dropzone-padding, --ui-dropzone-border-color, --ui-dropzone-bg,
 *   --ui-dropzone-over-border-color, --ui-dropzone-over-bg, --ui-dropzone-color, --ui-dropzone-radius.
 */
export class UiDropzone extends ShadowComponentElement {
  static stylesheet = new URL("./ui-dropzone.css", import.meta.url).href;
  static observedAttributes = ["accept", "multiple", "disabled", "label", "hint"];

  #depth = 0;

  get disabled() {
    return this.hasAttribute("disabled");
  }

  set disabled(value) {
    this.toggleAttribute("disabled", Boolean(value));
  }

  render() {
    const label = this.getAttribute("label") ?? "Dateien hierher ziehen oder klicken";
    const hint = this.getAttribute("hint");
    return `
      <div part="zone" class="ui-dropzone" role="button" tabindex="${this.disabled ? -1 : 0}"
        aria-disabled="${this.disabled}">
        <slot>
          <span class="ui-dropzone__label">${escapeHtml(label)}</span>
          ${hint ? `<span class="ui-dropzone__hint">${escapeHtml(hint)}</span>` : ""}
        </slot>
      </div>
      <input type="file" hidden${this.hasAttribute("multiple") ? " multiple" : ""}
        accept="${escapeHtml(this.getAttribute("accept") || "")}">`;
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
    input.addEventListener("change", () => {
      this.#hand([...input.files]);
      input.value = ""; // the same file can be picked again
    });
    zone.addEventListener("dragenter", (event) => {
      if (!this.#hasFiles(event)) return;
      event.preventDefault();
      this.#depth += 1;
      zone.classList.add("is-over");
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
      this.#hand([...event.dataTransfer.files]);
    });
  }

  open() {
    if (!this.disabled) this.shadowRoot.querySelector("input")?.click();
  }

  #hasFiles(event) {
    return [...(event.dataTransfer?.types || [])].includes("Files");
  }

  #hand(files) {
    if (this.disabled) return;
    let picked = files.filter((file) => acceptsFile(this.getAttribute("accept"), file));
    if (!this.hasAttribute("multiple")) picked = picked.slice(0, 1);
    if (!picked.length) return;
    this.dispatchEvent(new CustomEvent("ui-dropzone:files", { bubbles: true, composed: true, detail: { files: picked } }));
  }
}

registerComponent("ui-dropzone", UiDropzone);
