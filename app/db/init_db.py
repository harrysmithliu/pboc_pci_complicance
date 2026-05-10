from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import engine
from app.models import User


def _seed_user(db: Session, username: str, password: str, role: str) -> None:
    existing = db.query(User).filter(User.username == username).first()
    if existing is not None:
        return

    db.add(
        User(
            username=username,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        )
    )


def init_db(db: Session) -> None:
    Base.metadata.create_all(bind=engine)
    _seed_user(db, settings.seed_admin_username, settings.seed_admin_password, "admin")
    _seed_user(db, settings.seed_operator_username, settings.seed_operator_password, "operator")
    _seed_user(db, settings.seed_auditor_username, settings.seed_auditor_password, "auditor")
    db.commit()
