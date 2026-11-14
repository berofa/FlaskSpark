const THEME_STORAGE_KEY = "ui-theme";
const systemThemeQuery = window.matchMedia("(prefers-color-scheme: dark)");

export function resolveTheme(theme) {
  if (theme === "system") {
    return systemThemeQuery.matches ? "dark" : "light";
  }
  return theme;
}

/** The mode a page fixes (<html data-theme-fixed="light|dark|system">, e.g. an info screen), else "". */
export function fixedTheme() {
  return document.documentElement.getAttribute("data-theme-fixed") || "";
}

export function applyTheme(theme) {
  const fixed = fixedTheme();
  if (fixed) theme = fixed; // a fixed page neither follows nor changes the stored choice
  document.documentElement.setAttribute("data-bs-theme", resolveTheme(theme));
  if (!fixed) {
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // no storage (private window, blocked): the mode applies to this page only
    }
  }

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
  const fixed = fixedTheme();
  if (fixed) return fixed;
  try {
    return window.localStorage.getItem(THEME_STORAGE_KEY) || "system";
  } catch {
    return "system";
  }
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
