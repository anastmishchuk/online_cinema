from celery import shared_task
from datetime import datetime
from sqlalchemy.orm import Session

from src.users.config.database import SessionLocal
from src.users.models import ActivationToken, PasswordResetToken


@shared_task
def cleanup_expired_tokens():
    db: Session = SessionLocal()
    now = datetime.utcnow()

    deleted_activations = db.query(ActivationToken).filter(ActivationToken.expires_at < now).delete()
    deleted_resets = db.query(PasswordResetToken).filter(PasswordResetToken.expires_at < now).delete()

    db.commit()
    db.close()

    return {
        "activation_tokens_deleted": deleted_activations,
        "password_reset_tokens_deleted": deleted_resets
    }

