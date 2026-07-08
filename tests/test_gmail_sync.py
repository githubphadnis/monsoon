from unittest.mock import MagicMock, patch

from sqlalchemy import JSON, Uuid, create_engine, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.db import Base
from app.models import EmailParticipant
from app.models import tables as _tables  # noqa: F401
from app.services.gmail_sync import GmailSyncService, GmailSyncStats


def _sqlite_engine():
    engine = create_engine("sqlite:///:memory:")
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()
            elif isinstance(column.type, UUID):
                column.type = Uuid(as_uuid=True)
    Base.metadata.create_all(bind=engine)
    return engine


def test_upsert_participant_dedupes_pending_duplicates():
    engine = _sqlite_engine()
    db: Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    settings = Settings(
        gmail_client_id="client",
        gmail_client_secret="secret",
        gmail_refresh_token="token",
    )

    with patch("app.services.gmail_sync.build_gmail_service", return_value=MagicMock()):
        service = GmailSyncService(db, settings)

    stats = GmailSyncStats()
    service._upsert_participant("AbhayKPatil@rediffmail.com", "Abhay Patil", stats)
    service._upsert_participant("abhaykpatil@rediffmail.com", None, stats)
    db.flush()

    participants = list(db.scalars(select(EmailParticipant)))
    assert len(participants) == 1
    assert participants[0].email == "abhaykpatil@rediffmail.com"
    assert participants[0].display_name == "Abhay Patil"
    assert stats.participants_upserted == 1

    db.close()
