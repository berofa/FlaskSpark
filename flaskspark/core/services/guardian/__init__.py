"""The guardian: a service of the core that watches the application from the outside and reports findings.

Switched on in config.yaml (`guardian: {enabled: true}`, off by default). Every `guardian.interval` seconds it runs the
checks (GuardCheck) of the core and of every enabled module (Module.guard_checks()), with their own simple logic and
without the code they watch (a bug there must not blind the guardian too):

- core: NATS answers (a cluster without some nodes: warning), every service of the core and the modules has a live
  instance in the service directory (never two of a service that allows only one), notifications don't pile up in
  the work queue (with the notifications service on);
- the modules: their own checks.

Reports (flaskspark.core.notify, straight to the channels, never through the queue it watches): a finding once it
has lasted its grace time, reminders while it lasts (critical every 30 min, warnings every 4 h), and "Resolved" when
it is gone. A check may react to its finding when it is reported (GuardCheck.react()). The findings live in
STATE_DIR/guardian/findings.json, so a restart doesn't repeat them; the heartbeat carries them to the status tile.
"""

from .base import DEFAULTS, Finding, GuardCheck, GuardContext, settings  # noqa: F401
from .guard import Guard, default_checks, findings  # noqa: F401
