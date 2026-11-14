---
name: flaskspark-ui
description: Wohin gehören CSS, Templates und Web Components in Apps auf FlaskSpark (flaskspark.core)? Layout, Theme,
  Modul-Styles, wiederverwendbare Komponenten, modernes CSS ohne Präprozessor. Verwenden vor jeder Änderung an
  Aussehen, CSS, Templates, Themes oder Web Components einer App auf FlaskSpark und in FlaskSpark selbst.
---

# UI in Apps auf FlaskSpark: was gehört wohin?

Ziel: alles möglichst generisch, und was spezifisch ist, sauber getrennt dort, wo es verwendet wird.

## 1. Die Ebenen

| Ebene | Ort | Enthält |
|---|---|---|
| **Layout** | FlaskSpark: `flaskspark/core/web/static/flaskspark/css/frame.css`, `templates/layouts/main.html` | Rahmen, Sidebar, Topbar, Navigation, Karten, Buttons, Felder, Hilfsklassen (`app-*`) – für alle Apps gleich |
| **Komponenten** | FlaskSpark: `webcomponents/modules/bootstrap/ui-*` (Bootstrap 6, Shadow DOM) und die Kern-Komponenten unter `flaskspark/core/web/static/flaskspark/js/` | alles Wiederverwendbare |
| **Theme** | App: ihr Theme-Paket (`theme.yaml`, `theme.css`, `images/`) | Tokens (`--app-*`, `--bs-*` mit `light-dark()`), Logos, Favicon, ein paar Marken-Details |
| **Modul** | App: `modules/<name>/web/templates/<name>/`, `…/static/<name>/` | Templates, CSS und JS der eigenen Seiten und Komponenten des Moduls |

## 2. Theme: Variablen statt Regeln (Richtlinie)

- Ein Theme setzt so weit wie möglich **nur Variablen** (die Tokens aus der Token-Tabelle im README von FlaskSpark,
  Abschnitt «Themes»). Das gilt für jede App auf FlaskSpark, heutige und künftige. Eigene CSS-Regeln nur, wenn es
  sinnvoll ist (Best Practice, kein Gesetz).
- Das Layout ist für alle Apps gleich (z.B. die schwebende Sidebar); eine App ändert es nur über Tokens, nie durch
  eigene Layout-Regeln.
- Muss ein Theme etwas am Layout ändern, das es nicht über ein Token kann (z.B. Kartenradius, Sidebar-Hintergrund,
  Stil des aktiven Menüeintrags), dann **ein neues, dokumentiertes Token in FlaskSpark** einführen (frame.css +
  README-Tabelle), statt Layout-Regeln im Theme zu überschreiben.
- Hell/dunkel über `light-dark()` in den Tokens; Regeln pro Modus nur, wo `light-dark()` nicht reicht (z.B.
  Verläufe: `html.theme-dark`/`html.theme-light`).

## 3. Module: eigene Templates und eigenes CSS, wo nötig

- Ein Modul darf eigene Templates und eigenes CSS mitbringen, wenn seine Seiten es brauchen (z.B. ein Webmail-Client).
  Auch dort zuerst Tokens und Layout-Hilfsklassen des Kerns verwenden, eigene Regeln nur für das Spezifische.
- **CSS eines Moduls nur laden, wo es gebraucht wird:** im Template der Seite im Block `{% block page_styles %}`
  (bzw. JS in `{% block page_scripts %}`), nie global über `Module.LAYOUT` oder ein Sammel-Stylesheet. Keine
  Posteingangs-Styles auf der Kalenderseite.
- Styles einer Web Component des Moduls gehören in deren eigenes CSS im Shadow DOM, nicht in die Seite.
- Farben, Abstände, Radien nur über Tokens (`--app-*`, `--bs-*`), nie fest im Modul.

## 4. Wiederverwendbares gehört nach FlaskSpark

- Ein Element, das mehr als ein Modul oder eine App brauchen kann, wird eine **Web Component in FlaskSpark** (Paket
  `webcomponents`, Präfix `ui-`, Shadow DOM, über CSS-Variablen und `::part()` gestaltbar).
- Zuerst prüfen, ob Bootstrap 6 (bzw. eine vorhandene `ui-*`-Komponente) das schon kann oder sich daraus zusammensetzen
  lässt. Gibt es nichts, eine eigene, **allgemein gehaltene** Komponente bauen, die optisch zu den Bootstrap-Komponenten
  passt (Bootstrap-6-Tokens, gleiche Abstände, Radien, Fokus-Ringe, Zustände) und hell/dunkel kann.
- App-spezifische Komponenten (nur für dieses eine Thema) bleiben im Modul der App.
- Unsichtbare Helfer (Daten-Feeds, Kanäle) sind keine `ui-*`-Komponenten; generische liegen im Kern unter
  `flaskspark/…` (Import-Map), app-spezifische in der App.

### Texteingaben: welches Feld?

| Inhalt | Komponente |
|---|---|
| eine Zeile, Zahl, E-Mail | `ui-input` |
| mehrzeiliger Klartext ohne Formatierung | `ui-textarea` |
| formatierter Text, der als **Markdown** gespeichert wird (Beschreibungen, Notizen, Kommentare, alles, was auch in GitLab/GitHub landet oder von dort kommt) | `ui-markdown-editor` (Wert = Markdown; Modi «Text» und «Markdown», «/»- und «+»-Befehle, Anhänge) |
| formatierter Text, der als **HTML** gespeichert wird (z.B. E-Mails) | `ui-richtext` |

- Markdown immer über `flaskspark.markdown` bzw. den Jinja-Filter `markdown` anzeigen (`{{ text|markdown }}`), nie
  selbst rendern oder mit `|safe` ausgeben; im Browser `<ui-markdown>`. Beide bereinigen nach denselben Regeln.
- Relative Links/Bilder (z.B. GitLab-Uploads) mit `base_url` / `base-url`, Bild-Proxy mit `rewrite_url` / `rewriteUrl`.
- Texte des Editors in Apps auf `flaskspark.core`: `labels='{{ markdown_editor_labels()|tojson }}'` (Deutsch im
  Kern-Katalog). Uploads über `editor.uploadHandler = async (file) => ({url, name})`; eigene Schnellaktionen
  (z.B. «Embedded view») über `UiMarkdownEditor.addCommand({id, label, icon, menus, markdown | run})`.
- Kein Mermaid/PlantUML: bleiben Codeblöcke.

## 5. CSS-Standard

- **Modernes, natives CSS**, kein Präprozessor (kein SCSS/LESS), kein Build-Schritt: Nesting, Custom Properties,
  `color-mix()`, `light-dark()`, Container Queries, logische Eigenschaften (`margin-inline`, `inset-block` …),
  `:is()`/`:where()`, `@layer` wo es hilft.
- Keine Inline-Styles in Templates ausser für Werte, die aus Daten kommen (dann als Custom Property, z.B.
  `style="--c: {{ color }}"`).
- Bootstrap 5 gibt es nicht mehr (kein `.row`/`.col-md-*`, `.form-control`, `.modal`, `.dropdown`, `.text-muted`);
  Layout mit den Hilfsklassen des Kerns und den Bootstrap-6-Utilities.

## 6. Infobildschirme (`layouts/screen.html`)

- Seite für einen Bildschirm an der Wand, den niemand bedient (Manifest `SCREENS`, Abschnitte
  `PAGE_SECTIONS["screen:<key>"]`, Skill `flaskspark-new-module`): keine Navigation, keine Buttons, kein Kontextmenü,
  füllt den Viewport (ausgelegt auf 1920 × 1080 ohne Scrollen).
- Grössen folgen dem Viewport: 1rem = 16px × `--app-screen-scale` bei 1920 × 1080 (Token im Theme, `?scale=` in der
  URL). Moduleigenes CSS für den Bildschirm unter `html[data-screen] { … }`, Grössen in `rem` oder relativ zum
  Container (`cqi`), nicht in festen `px`.
- Helfer des Kerns: `app-screen-section`, `app-screen-section-head`, `app-screen-section-title` (Icon davor),
  `app-screen-fill` (nimmt die restliche Höhe), `app-screen-aside` (Spalte rechts über die ganze Höhe, Breite
  `--app-screen-aside-width`, Standard 28 %; die anderen Abschnitte bleiben links untereinander; was nicht Platz hat,
  wird abgeschnitten).
- `<html data-screen>` blendet aus: `ui-button`, `ui-button-group`, `ui-dialog`, `button`, `.btn`, `.app-toolbar`,
  `.app-page-actions` …; in den Web Components deren eigene Bedienelemente (`--ui-screen: on`). Opt-out
  `data-screen-keep`, Opt-in `data-screen-hide` (auch im Shadow DOM einer Komponente). Eine neue Komponente mit
  eigenen Bedienelementen markiert sie mit `data-screen-hide`.
- Farbmodus wie in der App, ausser `Screen.mode` oder `?mode=` legt ihn fest (`<html data-theme-fixed>`).
- Admins sehen alle Bildschirme der Module (Titel, Modul, Bereich, Farbmodus, Neuladen, Link) unter «Einstellungen ›
  Bildschirme» (`/settings#screens`); `/screen` listet die, die der Besucher nutzen darf.
- Prüfen: Headless-Screenshot bei 1920 × 1080 hell und dunkel; alles sichtbar ohne Scrollen.

## 7. Prüfen

- Jede Seite hell **und** dunkel ansehen (Headless-Browser genügt für den Überblick), auch schmal (Handy).
- Keine Konsolenfehler; Texte über gettext (`_()`, `N_()`, JS `t()`), nicht fest im Template.
