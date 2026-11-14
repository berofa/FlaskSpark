---
name: flaskspark-operations
description: Betrieb von Apps auf FlaskSpark (flaskspark.core) - Betriebsarten (Supervisor alles-in-einem mit
  `<app> run` oder ein Container/eine systemd-Unit pro Service), Router, Ports und Umgebungsvariablen, Container-
  Hinweise, Backups und Restore, `<app> status/services/units/routes/modules/data/guard-check`, FlaskSpark in einer
  App aktualisieren, Fehlersuche (Migration verweigert, Modul fehlt eine Abhängigkeit, NATS nicht erreichbar).
  Verwenden beim Deployen, Starten/Stoppen, Einrichten von Units/Containern/Backups, nach einem FlaskSpark-Update
  und wenn eine App nicht startet oder eine Statuskachel rot ist.
---

# Betrieb

Massgebend: README von FlaskSpark «Services and the command line», «Environment variables», «systemd»,
«Deployment», «Backups», «Guardian», «Notifications», «NATS users and permissions».

## 1. Betriebsarten

| Art | Start | Wann |
|---|---|---|
| Alles in einem Prozessbaum | `<app> run` (Supervisor: Migrationen, optional `nats-server`, web, push, Services der Module, Router zuletzt) | Entwicklung, ein Container, kleine Installation (`flaskspark.service`) |
| Ein Prozess pro Service | `<app> service <name>` je Container (`flaskspark-<name>`) bzw. Unit `flaskspark-<name>.service` | mehrere Hosts/Instanzen, getrennte Neustarts |

- Supervisor: startet beendete Prozesse neu (wachsende Pause), stoppt alles bei SIGTERM; nur er spricht mit systemd.
- Einzelne Services: Units mit `Type=notify`, `WatchdogSec=60` (Vorlage README «systemd»); `<app> units` listet die
  Unit-Namen. Migrationen laufen beim Start von `service web` (bzw. `run`), nicht in jedem Service.
- Namen ausserhalb des Codes immer `flaskspark-<service>` (Container, Compose-Service, Unit, Logs, Kacheln);
  `APP_HOST` pro Instanz setzen.
- Router (`APP_PORT`, Default 8100, bindet `ROUTER_HOST` 0.0.0.0) ist der einzige öffentliche Port; Web (8101) und
  Push (8102) binden auf 127.0.0.1. Ein Reverse Proxy kann den Router ersetzen: Routen aus `<app> routes`.

## 2. Umgebung (Auszug)

| Variable | Zweck |
|---|---|
| `APP_STATE_DIR` | DB, Sessions, NATS-Store, Modulzustand, Backups – lokale Platte, Volume im Container |
| `APP_CONFIG_DIR` | `app.env`, `<modul>.env` mit Secrets (`SECRET_KEY`, `APP_SECRET_KEY`, `OAUTH_*`, `NATS_*_USER/_PASSWORD`) |
| `APP_PORT`, `WEB_PORT`, `PUSH_PORT`, Ports aus `ROUTES` | pro App eindeutig, wenn mehrere auf einem Host laufen |
| `NATS_URL` (Komma für Cluster), `NATS_MONITOR`, `NATS_REPLICAS` | externer NATS; `nats.embedded: true` nur mit `nats-server` im Image |
| `SQLALCHEMY_DATABASE_URI` | andere DB als `STATE_DIR/app.db` |
| `APP_NAME`, `APP_CONFIG_FILE`, `APP_MODULES`, `APP_THEME` | Auswahl/Überschreiben |

Pfade und Ports müssen in der echten Umgebung stehen; alles andere darf aus den Env-Dateien kommen. Werte von
Secrets nie ausgeben oder loggen. Vollständige Tabelle: README «Environment variables».

Container: `CMD ["myapp", "run"]` (oder `["myapp", "service", "push"]`), Volumes für `APP_STATE_DIR` und
`APP_CONFIG_DIR`, nur `APP_PORT` veröffentlichen, Logs auf stdout.

## 3. Kommandozeile

```bash
myapp modules          # geladene Module, nicht geladene mit Grund, Theme
myapp services         # Name, Prozessname, Unit, Label, Entry
myapp routes           # Pfade des Routers → Ports
myapp units            # systemd-Units der Services
myapp status           # Statuskacheln (Exit 1 bei Fehler)
myapp guard-check      # Prüfungen des Wächters einmal, nichts wird gesendet (Exit 1 bei Befund)
myapp db upgrade|current|check|adopt|revision …   # Skill flaskspark-database
myapp data [clean <id…|all> [--yes]]                # Reste nicht mehr gelieferter Module
myapp backup | backup-list | backup-check <file> | backup-restore <file> [--yes]
```

## 4. Backups

```yaml
backup:
  dir: /var/backups/myapp      # Default STATE_DIR/backups
  keep_hours: 48
  keep_days: 7
  state: true                  # Zustandsverzeichnis mitsichern (Anhänge inklusive)
  max_age_hours: 26            # Kachel warnt bei älterem Backup
  mirror_dir: /mnt/share/myapp # optional: Kopie auf zweites Ziel
  include: [/srv/myapp/files]  # optional: weitere Verzeichnisse (auch Module.backup_paths(cfg))
```

- `myapp backup` per Timer/cron (z.B. alle 15 min): DB konsistent kopiert, geprüft, gezippt; Zustand als tar;
  Ordner mit `.nobackup` und Secrets nie dabei.
- Restore: alle Services stoppen, `myapp backup-check <file>`, `myapp backup-restore <file>`, starten.
- Vor jeder Migration und jedem Aufräumen («Settings › Data») macht FlaskSpark selbst ein DB-Backup.

## 5. Optionale Kern-Services

`notifications: {enabled: true}` (Zustellung über die Job-Queue; Kanal ntfy: `NTFY_URL`, `NTFY_TOPIC`, `NTFY_TOKEN`)
und `guardian: {enabled: true}` (Prüfungen alle `interval` s, meldet neue/anhaltende/behobene Befunde). Beide
brauchen NATS mit JetStream.

## 6. FlaskSpark in einer App aktualisieren

1. `CHANGELOG.md` von FlaskSpark lesen («Changed»: Umbenennungen, neue Pflichten).
2. Abhängigkeit anheben (`uv pip install -U "FlaskSpark[core]"` bzw. Version in `pyproject.toml`; lokale Kopie:
   editierbar installiert, dann nur neu starten).
3. Testsuite der App laufen lassen (`differences() == {}`, Seiten, Rechte).
4. Neue Kern-Migrationen laufen beim nächsten Start (Backup vorher); vorab `myapp db upgrade` in einer Kopie der DB
   möglich.
5. Neue NATS-Rechte prüfen (README «NATS users and permissions»), Units/Container-Namen (`flaskspark-<service>`).
6. Projekte ohne Python: Web Components neu exportieren (`python -m webcomponents.export …`).
7. Nach dem Neustart: `myapp status`, Seiten hell/dunkel ansehen.

## 7. Fehlersuche

| Symptom | Ursache, Abhilfe |
|---|---|
| `Database schema: … Run \`<app> db upgrade\`` | Web direkt gestartet: `db upgrade` oder über `run`/`service web` starten. |
| `Database not migrated: tables exist without a revision …: run \`db adopt\`` | DB aus alter Einzelhistorie: Skill `flaskspark-database` §4. |
| `Target database is not up to date` bei `db revision` | Erst `db upgrade`. |
| Modul fehlt in Navigation, `myapp modules` zeigt `not loaded: needs <x>` | `DEPENDS` nicht erfüllt: Modul `<x>` installieren/Entry Point prüfen, `uv pip install -e .` nach Entry-Point-Änderung. |
| Modul gar nicht gelistet | Entry Point fehlt oder Paket nicht neu installiert; `modules:`/`APP_MODULES` schränkt ein. |
| Seite 403 «no access» | Bereich der View fehlt in der Rolle: «Settings › Access»; `Area.defaults` greifen nur für unberührte Zellen. |
| `nats-server not found (NATS_SERVER) …` | Binary installieren oder `nats.embedded: false` + `NATS_URL`. |
| Log `nats: … Connect call failed` / Kacheln «unknown» | NATS nicht erreichbar: `NATS_URL`, Port, Benutzer/Passwort (`NATS_<USER>_USER`), Rechte (`_INBOX.<user>.>`). Web und Router laufen weiter, Live-Daten fehlen. |
| Live-Daten kommen nicht an | Thema nicht in `PUSH_TOPICS` oder falscher Bereich, `push` darf das Subject nicht abonnieren, Absender ohne `events.init`. |
| Admin-Einstellung wirkt nicht | Setting mit `services=…`: betroffenen Service neu starten. |

Logs: Supervisor-Ausgabe bzw. `journalctl -u flaskspark-<service>` / Container-Log `flaskspark-<service>`.
Produktive Instanzen nie ohne Rückfrage neu starten, stoppen oder zurückspielen.
