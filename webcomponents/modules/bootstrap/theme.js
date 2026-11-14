const THEME_STORAGE_KEY = "ui-theme";
const systemThemeQuery = window.matchMedia("(prefers-color-scheme: dark)");

export function resolveTheme(theme) {
  if (theme === "system") {
    return systemThemeQuery.matches ? "dark" : "light";
  }
  return theme;
}

export function applyTheme(theme) {
  document.documentElement.setAttribute("data-bs-theme", resolveTheme(theme));
  window.localStorage.setItem(THEME_STORAGE_KEY, theme);

  document.querySelectorAll("[data-theme-value]").forEach((button) => {
    const active = button.getAttribute("data-theme-value") === theme;
    // ui-button reflects its state through the "active" attribute, plain buttons through the class.
    if (button.localName === "ui-button") {
      button.toggleAttribute("active", active);
    } else {
      button.classList.toggle("active", active);
    }
  });
}

export function getStoredTheme() {
  return window.localStorage.getItem(THEME_STORAGE_KEY) || "system";
}

export function setupThemeSwitcher() {
  applyTheme(getStoredTheme());

  document.querySelectorAll("[data-theme-value]").forEach((button) => {
    button.addEventListener("click", () => applyTheme(button.getAttribute("data-theme-value") || "system"));
  });

  // Follow OS-level changes while "system" is selected.
  systemThemeQuery.addEventListener("change", () => {
    if (getStoredTheme() === "system") {
      applyTheme("system");
    }
  });
}
