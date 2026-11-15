---
name: flaskspark-access-and-settings
description: Zugriff, Einstellungen und Benutzerdaten in Apps auf FlaskSpark (flaskspark.core) - auth none/oauth/sso
  (OpenAccess, RoleAccess), Bereiche (Area) und Rolle×Bereich-Matrix, `area` an Views, OPEN/ADMIN, can(), Admin-Seiten
  «Settings», Setting/CONFIG und SETTINGS-Abschnitte, persönliche Einstellungen, Konten (AccountType, ACCOUNT_TYPES, APP_ACCOUNT_TYPES, GitLab,
  accounts.for_module), Teilen (Shareable, SHAREABLES), Anhänge (AttachmentOwner, ui-attachments), Secrets.
  Verwenden, wenn eine Seite/API geschützt, ein Recht oder eine Rolle eingeführt, eine Einstellung admin-änderbar,
  ein Konto/Login eines Benutzers genutzt, etwas teilbar oder mit Dateien versehen werden soll.
---

# Zugriff, Einstellungen, Konten, Teilen, Anhänge

Massgebend: README von FlaskSpark «Access», «Settings», «Personal settings», «Accounts», «Shares», «Attachments»,
«Secrets», «OAuth (OIDC) Login Provider».

## 1. Zugriff: die Module bleiben gleich, die App wählt

`config.yaml` `auth:`
- `none` → `OpenAccess`: keine Anmeldung, alle dürfen alles (auch Admin-Seiten). **Nur im vertrauenswürdigen Netz.**
  Keine Benutzer, also keine Konten, kein Teilen, persönliche Einstellungen nur pro Browser-Session.
- `oauth` / `sso` → `RoleAccess`: Anmeldung über OIDC (`OAUTH_*` in der Umgebung bzw. `CONFIG_DIR/app.env`;
  Gruppen → Rolle über `OAUTH_ROLE_MAP`, Rollen über `ROLE_DEFAULTS`, Default Administrators/Editors/Users/Guests).
  Braucht FlaskSparks Tabellen `user`/`roles` (Historie `signin`, läuft mit `db upgrade`).

Jede View nennt ihren Bereich (ohne `area`: nur Admins):

```python
from flaskspark.core.web import ADMIN, OPEN

area = "notes"                     # ein Bereich aus AREAS eines Manifests
area = OPEN                        # jeder, der die App benutzen darf
area = ADMIN                       # Admin-Rollen
area = {"GET": "notes", "*": ADMIN}
```

- Bereiche: `Area(key, label, description, defaults=frozenset({"Users"}), start="/notes", position=100, parent="")`;
  `parent` macht eine Seite eines Bereichs mit eigenem Recht (z.B. `"lager.tracking"` von `"lager"`; in der Matrix
  eingerückt unter dem Bereich, ein neuer übernimmt die Rechte des Bereichs; Views und Navigation der Seite tragen ihn);
  `defaults` = Rollennamen, die den Bereich haben, bis ein Admin die Matrix ändert («Settings › Access»,
  Tabelle `core_role_area`). Navigation, Kacheln, Push-Themen tragen ebenfalls einen Bereich.
- In Code und Templates: `can("notes")`, `user_id()` (0 ohne Anmeldung), `user_name()`, `roles_with("notes")`
  (`flaskspark.core.web`). Kein eigenes Rechtesystem im Modul, keine Rollennamen im Code abfragen.
- Feinere Rechte pro Objekt (wem gehört eine Notiz, wer darf sie sehen): Besitzer-Spalte + Teilen (§5).
- Endpoints ohne Anmeldung (Agent mit eigener Authentisierung): `PUBLIC_ENDPOINTS` im Manifest.
- Seite ohne Recht: 403 mit `flaskspark/no_access.html`, Hintergrund-Request: 403/401.

## 2. Admin-Einstellungen (`CONFIG`, `SETTINGS`)

```python
from flaskspark.core.settings import Setting

CONFIG = (
    Setting("notes.page_size", N_("Notes per page"), "int", N_("How many notes a page shows"), N_("Display"),
            min=1, max=100),
    Setting("notes.sort", N_("Order"), "choice", choices=(("new", N_("Newest first")), ("old", N_("Oldest first")))),
    Setting("notes.archive", N_("Archive old notes"), "bool", services=("notes",)),   # wirkt erst nach Neustart
)
SETTINGS = ("notes/settings.html",)   # eigener Abschnitt oben im Reiter des Moduls, mit eigenem Skript und API
```

- Arten: `int`, `float`, `bool`, `str`/`text`, `time` (`"HH:MM"`/`"off"`), `choice`, `ints`, `texts`, `json`.
- Default bleibt in `config.yaml` (Abschnitt des Moduls); Änderungen landen in `core_settings` und werden in jedem
  Prozess über `config.load()` gelegt (spätestens nach 5 s). Lesen immer über
  `config.load().section("notes").get("page_size", 20)`, nie `config.yaml` selbst öffnen.
- Nie als Setting: Secrets, `modules`, `theme`, `auth`.
- Seite `/settings` (nur Admins): Reiter Access, Users, je Modul, Data; `/settings#notes` öffnet den des Moduls.

## 3. Persönliche Einstellungen

```python
from flaskspark.core.web import save_user_setting, user_setting

shown = user_setting("notes.columns").get("shown", [])
save_user_setting("notes.columns", {"shown": ["title", "date"]})
```

Browser: `GET`/`PUT /api/user-settings/<key>` (`{value: {...}}`, max. 64 KB). Key beginnt mit dem Modulnamen
(`notes.…`), sonst findet «Data» die Reste eines entfernten Moduls nicht.

## 4. Konten (Logins der Benutzer bei Anbietern)

Ein Benutzer verbindet ein Konto einmal im Profil; Module nutzen es, ohne erneut zu fragen. Nur mit Anmeldung.

```python
# Manifest
ACCOUNT_TYPES = ("imap", "smtp")              # Kern: imap, smtp, caldav, carddav, gitlab

from flaskspark.core import accounts

mail = accounts.for_module("notes")           # nur die Typen aus ACCOUNT_TYPES, sonst AccountAccessError
for account in mail.for_user(uid, "imap"):    # .id .name .username .password (entschlüsselt) .settings
    ...
mail.for_user(uid, "imap", shared=True)       # auch mit seiner Rolle geteilte
mail.all("imap")                               # alle aktiven (für Services)
mail.record_test(account_id, "imap", ok=False, error="refused")
accounts.listen(lambda change: ...)            # AccountChange(action, account_id, user_id, types)
```

**Konten der App** (gehören keiner Person, z.B. ein GitLab-Token, mit dem ein Dienst für alle pollt): das Modul nennt
den Typ in `APP_ACCOUNT_TYPES = ("gitlab",)`; Admins pflegen sie in «Einstellungen» → «Konten»
(`/api/settings/accounts`, auch ohne Anmeldung). Besitzer `accounts.APP` (Benutzer-ID 0), nie in `for_user()`/`all()`.

```python
from flaskspark.core import accounts
from flaskspark.core.gitlab import GitLab, GitLabError

account = accounts.for_module("tracker").app_account("gitlab")   # erstes aktives, oder None; .app("gitlab") = alle
if account is not None:
    with GitLab.from_account(account) as gitlab:                 # Token nur an den eigenen Host, Timeouts
        for issue in gitlab.pages("/issues", {"scope": "all", "state": "opened"}):
            ...                                                  # GitLabError(.status, .timeout) bei Fehlern
```

Ein Konto der App aus Code anlegen (z.B. ein Import aus `.env` oder ein CLI-Befehl des Moduls), nie
`accounts.store.create` direkt:

```python
tracker = accounts.for_module("tracker")
account = tracker.create_app_account("gitlab", "GitLab", url="https://gitlab.example.com", secret=token)
# settings={...} oder Felder als Keyword-Argumente, username="…" falls der Typ einen braucht,
# test=True: zuerst anmelden (schlägt es fehl: Konto wieder weg, AccountTestError); AccountError bei falschen Feldern
# oder vergebenem Namen; die Listener hören «connected»
```

Kern-Typen: `imap`, `smtp`, `caldav`, `carddav`, `gitlab` (Adresse, Access Token, `verify_tls`). Ein Typ nur mit
Geheimnis (Token statt Benutzername/Passwort): `USERNAME = False`, `SECRET_LABEL = N_("Access token")`.

Eigener Typ: Unterklasse von `accounts.AccountType` (`KEY`, `LABEL`, `ICON`, `FIELDS` aus `accounts.Field`,
`test(account, timeout)` → `accounts.Result(text, params)` oder `AccountTestError`), registriert in
`Module.register()` mit `accounts.register_type(MyType())`. Ein Konto, das ein Modul noch braucht, schützt es mit
`account_change_veto(change)` (Grund als `N_()`-Text). Anbieter-Vorgaben: `config.yaml` `accounts.providers`.

## 5. Teilen (mit Rollen, nie mit Einzelpersonen)

```python
# Manifest: SHAREABLES = ("myapp.modules.notes.sharing:NoteShareable",)
from flaskspark.core import shares
from flaskspark.core.module import N_


class NoteShareable(shares.Shareable):
    TYPE, AREA, LABEL = "note", "notes", N_("Note")     # JOINS = True: Eingeladene treten erst bei

    def owner_of(self, s, object_id):
        note = s.get(Note, object_id)
        return note.owner_id if note else None

    def name_of(self, s, object_id):
        note = s.get(Note, object_id)
        return note.title if note else "?"
```

Prüfen mit `shares.access(uid, "note", id)` (`"owner"`, `"write"`, `"read"`, `None`), `can_read`, `can_write`,
`shared_with(uid, "note")`; beim Löschen `shares.forget("note", id)`; Empfänger einer Änderung
`shares.audience(...)`. `session=` übergeben, um in der Transaktion des Moduls zu bleiben. UI:
`<ui-share-dialog>` (`flaskspark/ui-share-dialog.js`), `dialog.open("note", 7, {name})`.

## 6. Anhänge (Dateien an Objekten)

```python
# Manifest: ATTACHMENT_OWNERS = ("myapp.modules.notes.files:NoteFiles",)
from flaskspark.core import attachments


class NoteFiles(attachments.AttachmentOwner):
    TYPE, AREA = "note", "notes"
    SHAREABLE = "note"       # Rechte wie das Teilen; sonst can_read/can_write überschreiben

# Objekt löschen: Dateien mit (Zeilen sofort, Dateien nach dem Commit)
with db.for_module("notes").session() as s:
    s.delete(note)
    attachments.delete_for("note", note.id, session=s)
```

```html
<ui-attachments owner-type="note" owner-id="{{ note.id }}"></ui-attachments>
<script type="module" src="{{ url_for('static', filename='flaskspark/js/ui-attachments.js') }}"></script>
```

Ablage unter `STATE_DIR/attachments/<store>` (bzw. `attachments.dir`/`attachments.stores`), Thumbnails mit Extra
`files`. Grenzen und Pfade: README «Attachments».

## 7. Secrets eines Moduls

```python
from flaskspark.core import secrets

box = secrets.for_module("notes")
row.api_key = box.encrypt(api_key)         # in der eigenen Tabelle, verschlüsselt
api_key = box.decrypt(row.api_key)         # secrets.SecretKeyError, wenn der Schlüssel nicht passt
secrets.mask(api_key)                      # für die Anzeige
```

Schlüssel `APP_SECRET_KEY` (oder `APP_SECRET_KEY_NOTES`) nur in der Umgebung/`CONFIG_DIR/*.env`, nie in
`config.yaml`, Repo oder Logs. Schlüssel ändern macht gespeicherte Secrets unlesbar.

## 8. Tests

Mit `auth: none` die Logik; Rechte mit `create(auth="oauth")` und Benutzern verschiedener Rollen (Muster:
`tests/core/sso.py`, `tests/core/test_access.py`, `test_shares.py`, `test_accounts.py` in FlaskSpark).
