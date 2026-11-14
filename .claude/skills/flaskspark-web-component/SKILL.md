---
name: flaskspark-web-component
description: Eine neue wiederverwendbare ui-*-Web-Component im Paket webcomponents von FlaskSpark bauen oder eine
  bestehende ändern - Ordner modules/bootstrap/ui-x/ mit JS, CSS und submodule.json, ShadowComponentElement, Tokens
  auf :host, ::part, Bootstrap-6-Look hell/dunkel, Texte über *-label-Attribute, Doku-Seite im docs-App, JS-/Python-/
  Browser-Tests, Export für Projekte ohne Python. Verwenden, wenn ein UI-Baustein in mehr als einem Modul oder einer
  App gebraucht wird und Bootstrap 6 bzw. die vorhandenen ui-*-Komponenten ihn nicht hergeben.
---

# Neue Web Component (`ui-*`)

Zuerst Skill `flaskspark-ui` (was gehört wohin). Massgebend: `webcomponents/README.md` («Structure», «Writing
components», «Bootstrap module notes», «Tests», «Export without Python»).

## 1. Braucht es sie?

1. Kann Bootstrap 6 oder eine vorhandene `ui-*`-Komponente das (Liste: `webcomponents/modules/bootstrap/`, docs-App)?
   Dann die nehmen oder zusammensetzen.
2. Nur für ein Thema einer App → bleibt im Modul der App (`web/static/<modul>/`), nicht in FlaskSpark.
3. Unsichtbare Helfer (Feeds, Kanäle) sind keine `ui-*`-Komponenten (gehören in den Kern bzw. die App).
4. Sonst: **allgemein gehaltene** Komponente in `webcomponents/modules/bootstrap/ui-<name>/`.

## 2. Dateien

```text
webcomponents/modules/bootstrap/ui-<name>/
  submodule.json       # name, description, elements, entry, files, tokens, requires
  ui-<name>.js         # Klasse + registerComponent(...) am Ende
  ui-<name>.css        # reines CSS, Tokens auf :host
```

Plus: Import in `webcomponents/modules/bootstrap/bootstrap.js`; Doku-Seite `docs/app/pages/<name>.py` (`PAGE`-Dict),
View `docs/app/views/<name>_docs.py` (`url = "/components/<name>"`, rendert `components/_v6.html`), Eintrag in der
Navigation in `docs/app/__init__.py`; Browser-Checks in `docs/app/templates/tests/components.html`.

```json
{
  "name": "ui-meter",
  "description": "A labelled meter with thresholds.",
  "elements": ["ui-meter"],
  "entry": "ui-meter.js",
  "files": ["ui-meter.js", "ui-meter.css"],
  "requires": [],
  "tokens": {
    "sources": [{"selector": ":host", "prefix": "--ui-meter-", "file": "ui-meter.css"}],
    "descriptions": {"--ui-meter-height": "Height of the bar.", "--ui-meter-radius": "Corner radius."}
  }
}
```

## 3. Komponente

```js
import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { BOOTSTRAP_SHADOW_STYLES } from "../shadow-styles.js";

/**
 * <ui-meter>: … (Doc-Kommentar: Attribute, Slots, Events, Methoden, Parts, wie bei den anderen Komponenten)
 * Attributes: value, max, label, low-label ("Low").  Parts: track, bar, label.
 */
export class UiMeter extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-meter.css", import.meta.url).href];
  static observedAttributes = ["value", "max", "label", "low-label"];

  render() {
    const label = this.getAttribute("label") || "";
    return `<div part="track" class="ui-meter" role="meter" aria-label="${escapeHtml(label)}">`
      + `<div part="bar" class="ui-meter-bar"></div></div>`;
  }
}

registerComponent("ui-meter", UiMeter);
```

Regeln:
- **Shadow DOM** (`ShadowComponentElement`) für Bausteine; **Light DOM** (`LightComponentElement`,
  `LightFeedElement`) nur für Komponenten, die andere Komponenten zusammensetzen und von der Seite gestaltbar bleiben
  müssen. Begründung: README «Shadow DOM or light DOM».
- `render()` gibt das HTML des Shadow Roots zurück, `afterRender()` hängt Listener an. Jeder interpolierte Wert
  durch `escapeHtml()`. Rendering nicht selbst planen (Attributänderungen bündeln sich pro Microtask).
- Formularfelder: `static formAssociated = true` + `attachInternals()` (Vorbild `ui-input`, `ui-dropzone`);
  `change` auf dem Host neu auslösen.
- Events: `ui-<name>:<was>` (`bubbles`, `composed`), Detail als Objekt.
- **Texte:** keine fest verdrahteten Texte ausser englischen Defaults; jeder sichtbare/vorgelesene Text ist über ein
  Attribut änderbar (`label`, `remove-label`, `*-message`, Platzhalter wie `{name}`), damit Apps übersetzen können.
- **Aussehen wie Bootstrap 6:** nur Bootstrap-Tokens (`--bs-*`: Abstände, Radien, Farben `--bs-fg-*`, `--bs-bg-*`,
  Fokus-Ring, Zustände `is-invalid`), Bootstrap-Klassen im Shadow DOM (`btn`, `form-field`, `form-label`) wo passend.
- **Eigene Tokens** `--ui-<name>-*` nur auf `:host`, mit Default aus Bootstrap-Tokens, jedes in `submodule.json`
  beschrieben. Hell/dunkel über die vererbten Tokens bzw. `light-dark()`, nie über `[data-bs-theme]` im Shadow DOM.
- `part="…"` an allem, was Seiten gestalten müssen (Bootstrap setzt `--bs-*` oft auf der Komponentenklasse selbst;
  Überschreiben dann über den Part).
- Reines, modernes CSS (Nesting, `color-mix()`, `light-dark()`, logische Eigenschaften), kein SCSS, kein Build.
- Reine Logik (Berechnungen, Parser) in eine eigene Datei bzw. `core/`, damit sie mit `node --test` testbar ist.

## 4. Tests und Doku

```bash
.venv/bin/python -m pytest tests/webcomponents/python   # Tokens beschrieben + themebar, reines CSS, Export, Delivery
node --test tests/webcomponents/js/                     # reine Logik (neue Datei <name>.test.js)
.venv/bin/python -m pytest tests/webcomponents/python/test_browser.py   # headless Chromium, sonst übersprungen
.venv/bin/python docs/run.py                            # docs-App: Seite hell/dunkel, schmal ansehen
```

- Neues Element in die Liste `tags` und eigene `check("…", …)`-Einträge in `docs/app/templates/tests/components.html`
  (Rendering, Token auf dem Host wirkt, Formularverhalten).
- Doku-Seite: Abschnitte mit Live-Beispiel (`html`, optional `script`), Referenz der Elemente, Tokens.
- Ohne Chromium/Browser-Ansicht: ausdrücklich als ungeprüft melden.
- `CHANGELOG.md` von FlaskSpark ergänzen.

## 5. Nutzung und Export

- In Apps auf FlaskSpark: schon geladen (Modul `bootstrap`); Import-Map-Präfix `webcomponents/`.
- Projekte ohne Python: `python -m webcomponents.export ZIEL bootstrap/ui-<name>` (nimmt `requires` mit,
  `--no-vendor` ohne Bootstrap-Kopie); nach jedem FlaskSpark-Update neu exportieren.
