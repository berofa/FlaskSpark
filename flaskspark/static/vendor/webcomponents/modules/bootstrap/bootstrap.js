/**
 * Module entry "bootstrap": imports every submodule (each registers its own
 * custom elements) and wires the theme switcher.
 *
 * Load via <script type="module" src=".../modules/bootstrap/bootstrap.js"></script>,
 * or import single submodules (e.g. ui-tooltip/ui-tooltip.js) to load only those.
 */
import { UiAccordion, UiAccordionItem } from "./ui-accordion/ui-accordion.js";
import { UiAlert } from "./ui-alert/ui-alert.js";
import { UiBadge } from "./ui-badge/ui-badge.js";
import { UiBreadcrumb, UiBreadcrumbItem } from "./ui-breadcrumb/ui-breadcrumb.js";
import { UiButton } from "./ui-button/ui-button.js";
import { UiButtonGroup } from "./ui-button-group/ui-button-group.js";
import { UiCard, UiCardGroup } from "./ui-card/ui-card.js";
import { UiCarousel, UiCarouselItem } from "./ui-carousel/ui-carousel.js";
import { UiCheck } from "./ui-check/ui-check.js";
import { UiChip } from "./ui-chip/ui-chip.js";
import { UiChipInput } from "./ui-chip/ui-chip-input.js";
import { UiCloseButton } from "./ui-close-button/ui-close-button.js";
import { UiCollapse } from "./ui-collapse/ui-collapse.js";
import { UiDialog } from "./ui-dialog/ui-dialog.js";
import { UiDrawer } from "./ui-drawer/ui-drawer.js";
import { UiDropzone } from "./ui-dropzone/ui-dropzone.js";
import { UiGallery, UiGalleryItem } from "./ui-gallery/ui-gallery.js";
import { UiGrid } from "./ui-grid/ui-grid.js";
import { UiGridEditor } from "./ui-grid-editor/ui-grid-editor.js";
import { UiInput } from "./ui-input/ui-input.js";
import { UiListGroup, UiListGroupItem } from "./ui-list-group/ui-list-group.js";
import { MenuController, UiMenu } from "./ui-menu/ui-menu.js";
import { UiOtp } from "./ui-otp/ui-otp.js";
import { UiPopover } from "./ui-popover/ui-popover.js";
import { UiRange } from "./ui-range/ui-range.js";
import { UiSelect } from "./ui-select/ui-select.js";
import { UiTable } from "./ui-table/ui-table.js";
import { UiTabs, UiTabPanel } from "./ui-tabs/ui-tabs.js";
import { UiRichtext } from "./ui-richtext/ui-richtext.js";
import { UiTextarea } from "./ui-textarea/ui-textarea.js";
import { UiToast, UiToastContainer, showToast } from "./ui-toast/ui-toast.js";
import "./toggler.js";
import "./strength.js";
import { UiTooltip } from "./ui-tooltip/ui-tooltip.js";
import { setupThemeSwitcher } from "./theme.js";

if (document.readyState === "loading") {
  window.addEventListener("DOMContentLoaded", () => setupThemeSwitcher());
} else {
  setupThemeSwitcher();
}

export {
  UiAccordion,
  UiAccordionItem,
  UiAlert,
  UiBadge,
  UiBreadcrumb,
  UiBreadcrumbItem,
  UiButton,
  UiButtonGroup,
  UiCard,
  UiCardGroup,
  UiCarousel,
  UiCarouselItem,
  UiCheck,
  UiChip,
  UiChipInput,
  UiCloseButton,
  UiCollapse,
  UiDialog,
  UiDrawer,
  UiDropzone,
  UiGallery,
  UiGalleryItem,
  UiGrid,
  UiGridEditor,
  UiInput,
  UiListGroup,
  UiListGroupItem,
  MenuController,
  UiMenu,
  UiOtp,
  UiPopover,
  UiRange,
  UiSelect,
  UiTable,
  UiTabs,
  UiTabPanel,
  UiRichtext,
  UiTextarea,
  UiToast,
  UiToastContainer,
  UiTooltip,
  showToast,
};
export { registerComponent } from "../../core/registry.js";
export { ShadowComponentElement } from "../../core/shadow-component-element.js";
export { FormControlElement } from "../../core/form-control-element.js";
export { computePlacement } from "../../core/placement.js";
export { SharedShadowStyles } from "../../core/shared-shadow-styles.js";
export { escapeHtml } from "../../core/escape.js";
export { applyTheme, setupThemeSwitcher } from "./theme.js";
export { toggle as toggleToggler } from "./toggler.js";
export { normalizeGridLayout, defaultLayout, buildUnitAreas } from "./ui-grid/grid-layout.js";
