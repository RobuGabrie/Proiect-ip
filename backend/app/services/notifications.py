"""Notificări prin email: se salvează în tranzacția operației și se trimit după răspunsul API."""
import logging
import smtplib
from collections.abc import Iterable
from datetime import datetime, timezone
from email.message import EmailMessage

from fastapi import BackgroundTasks
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Notification, NotificationType, Reservation, User

logger = logging.getLogger(__name__)

SUBJECTS = {
    NotificationType.CERERE_NOUA: "Cerere nouă de rezervare",
    NotificationType.APROBARE: "Rezervare aprobată",
    NotificationType.RESPINGERE: "Rezervare respinsă",
    NotificationType.ANULARE: "Rezervare anulată",
    NotificationType.INSTRUIRE: "Instruire necesară pentru rezervare",
    NotificationType.MENTENANTA: "Rezervare afectată de mentenanță",
    NotificationType.LISTA_ASTEPTARE: "S-a eliberat un interval",
}


def queue(
    db: Session,
    recipients: Iterable[User],
    tip: NotificationType,
    mesaj: str,
    reservation: Reservation | None = None,
) -> list[Notification]:
    created = [Notification(user=user, tip=tip, mesaj=mesaj, reservation=reservation) for user in recipients]
    db.add_all(created)
    return created


def send_email(to: str, subject: str, body: str) -> None:
    if not settings.smtp_host:
        logger.info("SMTP neconfigurat; email pentru %s nu a fost trimis: %s", to, subject)
        return
    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        smtp.send_message(message)


def _deliver(bind: Engine | Connection, notification_ids: list[int]) -> None:
    with Session(bind) as db:
        for notification_id in notification_ids:
            notification = db.get(Notification, notification_id)
            try:
                send_email(notification.user.email, SUBJECTS[notification.tip], notification.mesaj)
            except (OSError, smtplib.SMTPException):
                logger.exception("Emailul pentru notificarea %s nu a putut fi trimis", notification_id)
                continue
            notification.data_trimitere = datetime.now(timezone.utc)
            db.commit()


def schedule_delivery(background: BackgroundTasks, db: Session, notifications: list[Notification]) -> None:
    """Se apelează după commit, când notificările au deja identificator."""
    if notifications:
        background.add_task(_deliver, db.get_bind(), [notification.id for notification in notifications])
