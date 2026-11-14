---
name: flaskspark-i18n
description: Übersetzungen in Apps auf FlaskSpark (flaskspark.core) und in FlaskSpark selbst - englische Quelltexte,
  _()/gettext, tr()/ntr() (flaskspark.core.i18n), N_() in Manifesten und Settings, lazy_gettext, t()/nt()/preload()/
  preloadCatalog() im Browser, JS-Extraktor für Template-Literale, Sprache im Profil, Sprache über NATS, Katalog pro Modul, der der App
  und der des Kerns (scripts/core-i18n), Reihenfolge Kern → Module → App, pybabel extract/update/compile, deutscher
  Stil (Schweizer «ss», «du»). Verwenden bei jedem neuen oder geänderten sichtbaren Text, neuen Templates/Skripten,
  einer neuen Sprache oder wenn ein Text nicht übersetzt erscheint.
---

# Übersetzungen

Massgebend: README von FlaskSpark «Translations» (Modular apps) und «i18n»; Code
`flaskspark/core/i18n.py` (`tr`, `ntr`, `using`, Cache, NATS), `flaskspark/core/i18n_extract.py` (JS-Extraktor),
`flaskspark/core/web/language.py` (Sprache des Besuchers), `flaskspark/core/web/app.py` (`translation_directories`),
`web/static/flaskspark/js/i18n.js`, `scripts/core-i18n`.

## 1. Regeln

- **Quelltexte sind Englisch**, überall (Python, Templates, JS, Manifeste). Kein Deutsch im Code.
- Jeder sichtbare Text geht durch gettext; nie Texte zusammensetzen, Platzhalter benutzen:
  Python/Jinja `%(name)s`, JS `{name}`.
- Ganze Sätze übersetzen, keine Satzteile; Plural mit `ngettext`/`ntr` (Python) bzw. `nt` (JS).
- Ein `%` im Quelltext, das kein Platzhalter ist (`"{pct} % of {size}"`), hält Babel für ein Python-Format und
  `pybabel compile` meldet einen Fehler: Zahl samt Einheit in den Platzhalter (`"{percent} of {size}"`).

## 2. Markieren

| Wo | Wie |
|---|---|
| Templates (Jinja) | `{{ _("Notes") }}`, `{{ _("%(n)s notes", n=count) }}`, `{{ ngettext("%(num)s note", "%(num)s notes", count) }}` |
| Views, Code im Request | `from flask_babel import gettext as _` → `_("Saved")`, oder `tr()` wie unten |
| Python-Code, der im Request **und** in Diensten läuft (Module, Dienste, Benachrichtigungen) | `from flaskspark.core.i18n import tr, ntr` → `tr("Saved")`, `tr("Said: %(text)s", text=x)` (Text positional-only), `ntr("%(num)s file", "%(num)s files", n)`; im Request die Sprache des Besuchers, sonst die der App |
| ein Block in einer bestimmten Sprache | `with i18n.using("de"): …` (`i18n.current_language()` sagt, welche gerade gilt) |
| Modul-Ebene (Konstanten, die erst im Request gebraucht werden) | `from flask_babel import lazy_gettext` oder `N_()` und beim Anzeigen `tr()` |
| Manifest, `Setting`, `Area`, `NavItem`, `Tile`, `StatusTile.NAME`, `Shareable.LABEL`, Fehlervorlagen | `N_("Notes")` (`flaskspark.core.module` oder `flaskspark.core.i18n`): markiert nur, übersetzt wird beim Anzeigen |
| Browser-JS | `import { t, nt, preload, preloadCatalog } from "flaskspark/i18n.js"`; der Katalog des Moduls der Seite kommt mit der Seite (`t("Saved")` sofort), `nt("{n} file", "{n} files", n)`, andere Module mit `await preloadCatalog("calendar")`, einzelne Texte mit `await preload(["Saved", ["{n} day", "{n} days"]])` |
| Web Components | keine Übersetzung in der Komponente; Seite setzt `label`, `*-label`, `*-message`-Attribute mit `_()` |
| Dienst, der eine NATS-Anfrage beantwortet | Handler mit `@i18n.with_request_language` dekorieren: `tr()` darin in der Sprache des Anfragenden (`events.request()` schickt `Accept-Language` automatisch mit) |
| ausserhalb eines Requests ohne Anfrage (Wächter, Benachrichtigungen an alle) | `tr()` bzw. `flaskspark.core.i18n.gettext(text, **params)`: Sprache der App (`notifications.language`, sonst erste von `app.locales`) |

JS-Texte kommen aus denselben Katalogen (im Layout eingebettet bzw. `/api/i18n/catalog`); sie müssen also im `.po`
stehen (Extraktion mit den Keywords `t` und `nt:1,2` und FlaskSparks JS-Extraktor, siehe 4.). Eine Seite, die Texte
anderer Module braucht, nennt sie oben im Template: `{% set i18n_modules = ["calendar", "core"] %}`.

Sprache des Besuchers: Profil (angemeldet, Einstellung `core.language`) > Cookie `lang` (Sidebar) > Browser >
erste von `app.locales`. Die Sprach-Buttons der Sidebar ändern bei Angemeldeten die Wahl im Profil mit.

Kataloge werden pro Prozess und Sprache gecacht und neu geladen, wenn sich eine `.mo`-Datei ändert (mtime); ein
Neustart ist für `tr()`/`i18n.gettext()` nicht nötig, für Flask-Babel (`_()` in Views und Templates) schon.

## 3. Kataloge und Reihenfolge

Geladen in dieser Reihenfolge, der spätere gewinnt pro Text:

1. Kern: `flaskspark/core/locales` (Englisch, Deutsch; Layout, Settings, Status, Zugriff),
2. jedes geladene Modul: `<modul-paket>/locales/` (in Modulreihenfolge),
3. die App: `<app-paket>/locales/` (klassisches Layout: `web/<app>/locales`).

Ein Modul übersetzt also nur seine eigenen Texte; die App nur, was sie anders sagen will. `.mo`-Dateien
mitliefern (`package-data`), sonst fehlt die Übersetzung im installierten Paket.

## 4. Katalog eines Moduls pflegen

Mapping-Datei (sonst werden Templates und JS nicht extrahiert), z.B. `babel.cfg` im App-Repo. Für JS **nicht** Babels
`javascript`-Extraktor nehmen (verliert `t()` in Template-Literalen, z.B. `` `<b title="${t("Save")}">` ``, und bei
`t(a ? "x" : "y")`), sondern FlaskSparks:

```ini
[extractors]
flaskspark_js = flaskspark.core.i18n_extract:extract_js

[python: **.py]
[jinja2: **/templates/**.html]
[flaskspark_js: **/static/**.js]
```

```bash
M=src/myapp/modules/notes
K="-k _ -k gettext -k lazy_gettext -k N_ -k tr -k ntr:1,2 -k t -k nt:1,2"
pybabel extract -F babel.cfg $K --no-location --sort-output -o /tmp/notes.pot $M
pybabel init   -i /tmp/notes.pot -d $M/locales -l de        # nur beim ersten Mal pro Sprache
pybabel update -i /tmp/notes.pot -d $M/locales --no-fuzzy-matching --ignore-obsolete
pybabel compile -d $M/locales
```

`.po` und `.mo` committen. Danach die Web-App neu starten (Flask-Babel lädt die Kataloge beim Start; `tr()` merkt
geänderte `.mo`-Dateien selbst). Neue Sprache der App:
`app.locales` in `config.yaml` ergänzen und in jedem Katalog `init`.

## 5. Katalog des Kerns (nur im FlaskSpark-Repo)

`scripts/core-i18n` (extrahiert Python, Templates und JS aus `flaskspark/core`, aktualisiert alle Sprachen,
kompiliert); `scripts/core-i18n init fr` für eine neue Sprache. Danach die neuen `msgstr` in
`flaskspark/core/locales/de/LC_MESSAGES/messages.po` ausfüllen und das Skript nochmals laufen lassen.

## 6. Deutscher Stil

- Schweizer Hochdeutsch: immer «ss», nie «ß»; Anführungszeichen «…».
- Benutzer mit **«du»** ansprechen (klein, «dein», «dich»), kurz und freundlich, wie im Kern-Katalog.
- Begriffe des Kerns übernehmen (z.B. «Einstellungen», «Bereich», «Rolle», «Anmelden»), damit die App einheitlich
  klingt; im Zweifel im Kern-Katalog nachschlagen.
- Platzhalter unverändert übernehmen (`%(name)s`, `{name}`).

## 7. Prüfen

- Seite mit `Accept-Language: de` laden (Test-Client: `client.get(url, headers={"Accept-Language": "de"})`) bzw. im
  Browser die Sprache umschalten; kein englischer Rest, keine leeren Texte.
- `grep -n "^msgstr.*ß" $(find . -name "*.po")` muss leer sein.
- Fuzzy-Einträge (`#, fuzzy`) werden nicht verwendet: auflösen.
