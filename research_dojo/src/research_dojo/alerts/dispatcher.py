"""Fan an AlertTrigger out to configured notifiers, respecting
DOJO_ALERT_MIN_SEVERITY, and persist every dispatch to `alert_events`
(pillar 5.2 + CLI `dojo alerts history`).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from research_dojo.alerts.notifiers import FileNotifier, LogNotifier, Notifier, WebhookNotifier
from research_dojo.alerts.rules import AlertTrigger
from research_dojo.config.settings import get_settings
from research_dojo.db.repositories import AlertRepo

_SEVERITY_RANK = {"info": 0, "warning": 1, "critical": 2}


def build_notifiers(webhook_url: str | None = None) -> list[Notifier]:
    settings = get_settings()
    notifiers: list[Notifier] = [LogNotifier(), FileNotifier(settings.resolve_data_dir() / "alerts.jsonl")]
    url = webhook_url or settings.alert_webhook_url
    if url:
        notifiers.append(WebhookNotifier(url))
    return notifiers


def dispatch(
    session: Session,
    trigger: AlertTrigger,
    run_id: str | None,
    notifiers: list[Notifier] | None = None,
    min_severity: str | None = None,
) -> None:
    settings = get_settings()
    min_sev = min_severity or settings.alert_min_severity
    if _SEVERITY_RANK.get(trigger.severity, 0) < _SEVERITY_RANK.get(min_sev, 0):
        return
    notifiers = notifiers if notifiers is not None else build_notifiers()
    delivered_to = {}
    for notifier in notifiers:
        result = notifier.notify(rule=trigger.rule, severity=trigger.severity, message=trigger.message, run_id=run_id)
        delivered_to[notifier.name] = result
    AlertRepo.record(
        session, run_id=run_id, rule=trigger.rule, severity=trigger.severity,
        message=trigger.message, delivered_to=delivered_to,
    )
