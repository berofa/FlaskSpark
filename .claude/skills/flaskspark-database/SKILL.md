---
name: flaskspark-database
description: Datenbank in Apps auf FlaskSpark (flaskspark.core.db) - Modelle auf db.Model, Sessions mit
  db.for_module(...).session(), Bausteine aus flaskspark.core.db statt sqlalchemy, Rechte (TABLES/SHARED_TABLES,
  DatabaseAccessError), Migrationen pro Modul (db revision --module, upgrade beim Start, check, adopt), Module, die
  nicht mehr geliefert werden, «Settings › Data» bzw. `<app> data`, Backups vor Migrationen. Verwenden bei jeder neuen
  oder geänderten Tabelle/Spalte, jeder Query, jeder Migration, bei Migrationsfehlern beim Start und beim Aufräumen
  alter Daten.
---

# Datenbank

Massgebend: README von FlaskSpark «Database», «Migrations», «Settings» (Abschnitt «Data»); Code
`flaskspark/core/db/__init__.py`, `sql.py`, `migrations.py`, `flaskspark/core/leftovers.py`.

## 1. Regeln

- Module importieren **nie `sqlalchemy`** direkt, nur `from flaskspark.core import db` bzw.
  `from flaskspark.core.db import …`. Fehlt ein Baustein, gehört er nach `flaskspark/core/db/sql.py` (FlaskSpark).
- Jede Sitzung ist eine Arbeitseinheit mit den Rechten des Moduls:
  `with db.for_module("notes").session() as s:` (Alias `.transaction()`); Commit am Ende, Rollback bei Fehler.
  Nie eigene Engines, Connections oder Sessions öffnen.
- Eine Session erreicht nur `TABLES` und `SHARED_TABLES` des Manifests; alles andere → `db.DatabaseAccessError`.
  Rohes SQL (`text`) ist in Modul-Sessions verboten. Fremde Daten über den `client.py` des anderen Moduls bzw. die
  Kern-APIs (`accounts`, `shares`, `attachments`), nicht über `SHARED_TABLES`, wenn es sich vermeiden lässt.
- Portables SQL: kein `json_extract`, Booleans als `Boolean`, keine SQLite-Eigenheiten (PostgreSQL kommt später).
- Benutzerbezogene Zeilen tragen die `user_id` (`flaskspark.core.web.user_id()`); Fremdschlüssel auf FlaskSparks
  Benutzer/Rollen: `ForeignKey(db.USER.c.id)`, `db.ROLES`.

## 2. Modell

```python
# myapp/modules/notes/models.py
from datetime import datetime

from flaskspark.core.db import (JSON, DateTime, ForeignKey, Integer, Mapped, Model, String, Text, func,
                                mapped_column, relationship)


class Note(Model):
    __tablename__ = "notes_note"                          # Präfix = Modulname

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
```

Manifest: `MODELS = ("myapp.modules.notes.models",)`, `TABLES = ("notes_note",)`.

```python
from flaskspark.core import db

with db.for_module("notes").session() as s:
    s.add(Note(title="Buy milk", owner_id=uid))
    rows = s.scalars(db.select(Note).where(Note.owner_id == uid).order_by(db.desc(Note.id))).all()
    s.execute(db.update(Note).where(Note.id == 7).values(title="x"))
    db.after_commit(s, lambda: remove_files(paths))   # Dateien erst nach dem Commit löschen
```

Weitere Hilfen: `db.after_rollback(s, cb)`, `db.has_table(s, name)`, `db.IntegrityError`.

## 3. Migrationen (eine Historie pro Modul)

Revisionen liegen in `<modul>/migrations/versions/` als eigener Zweig (`branch_labels = ("notes",)`, erste Revision
`down_revision = None`). Der Kern hat `core` (und `signin` mit Anmeldung). FlaskSpark führt alle beim Start des
Web-Service und von `<app> run` aus, mit DB-Backup vorher, wenn etwas zu tun ist.

```bash
myapp db upgrade                                          # alle Historien auf ihren Head (immer zuerst)
myapp db revision -m "notes: add tags" --module notes      # autogeneriert, nur die Tabellen von notes
myapp db revision -m "notes: fill tags" --module notes --empty   # leer, Daten-Migration von Hand
myapp db upgrade
myapp db check                                            # Modelle vs. DB, Exit 1 bei Unterschied
myapp db current                                          # Stand jeder Historie
```

- `revision` verlangt eine DB auf allen Heads (sonst «Target database is not up to date»): erst `db upgrade`.
  Ohne Änderung schreibt es nichts.
- **Jedes generierte Skript lesen** (Autogenerate schreibt `op.batch_alter_table`, damit SQLite Spalten ändern kann;
  neue `nullable=False`-Spalten auf vollen Tabellen brauchen ein `server_default`), dann im selben Commit wie das
  Modell.
- Braucht eine Revision die Tabelle eines anderen Moduls (Fremdschlüssel): dessen Revision in `depends_on`.
- Revisionen nie nachträglich ändern, die schon irgendwo liefen; neue Revision schreiben.
- Test pro App: `migrations.differences(config.load()) == {}` (Skill `flaskspark-new-app` §5).

## 4. Fehler beim Start

| Meldung | Bedeutung, Abhilfe |
|---|---|
| `Database schema: … not at the head. Run \`<app> db upgrade\`` | Web-App direkt gestartet ohne Migration: `db upgrade` (oder über `run`/`service web` starten). Notfalls `APP_SKIP_MIGRATION_CHECK=1`. |
| `Database not migrated: tables exist without a revision of their history (…): run \`db adopt\`` | Tabellen ohne Revision ihrer Historie (alte Einzelhistorie, z.B. Flask-Migrate in `web/migrations`): einmalig übernehmen, siehe unten. |
| `Tables missing in the database: …` (Warnung) | Modell ohne Migration: `db revision --module <name>`. |
| `module 'x' is no longer delivered …` (Warnung) | Kein Fehler: Modul nicht mehr in der App; Tabellen bleiben. Aufräumen siehe §5. |

**Übernahme (`db adopt`)** einer DB aus einer früheren Einzelhistorie: (1) mit der alten App-Version auf die letzte
alte Revision bringen, (2) jedem Modul (und dem Kern) eine erste Revision geben, die seine Tabellen **genau so**
beschreibt, (3) `myapp db adopt` (Backup, stempelt Historien, deren Tabellen alle existieren; bei teilweise vorhandenen
bricht es ohne Änderung ab), (4) `myapp db upgrade`, (5) `myapp db check` muss leer sein.

## 5. Module, die nicht mehr geliefert werden, und Aufräumen

- Entfernt eine neue App-Version ein Modul (oder benennt es um), bleiben Revision in `alembic_version`, Tabellen und
  Daten unangetastet; Start warnt, Kachel «Modules» zeigt es. Kommt das Modul zurück, geht die Historie weiter.
  FlaskSpark merkt sich gelieferte Module in `core_module_chains`.
- **Umbenennen eines Moduls** heisst für FlaskSpark: altes Modul weg, neues da (neue Historie, leere Tabellen).
  Daten vorher per Migration des neuen Moduls übernehmen oder Umbenennen vermeiden.
- Aufräumen nur bewusst: Admin-Seite «Settings › Data» oder `myapp data` (listet Ids `module:<name>`,
  `table:<name>`, `revision:<rev>`, `setting:<path>`, `area:<key>`, `user-setting:<key>`, `state:<name>`),
  `myapp data clean <id…|all> [--yes]`. Vorher Backup (`db-<stamp>.db.gz`, Zustand `removed-<stamp>.tar.gz`);
  rückgängig nur aus diesem Backup. Nie Tabellen von Hand droppen.

## 6. Backups

`<app> backup` kopiert die DB konsistent (auch im Betrieb), dazu den Zustand; Restore nur mit gestoppten Services
(`backup-restore <file>`). Details und Konfiguration: Skill `flaskspark-operations`.
