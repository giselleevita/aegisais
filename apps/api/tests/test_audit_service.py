import pytest
from sqlalchemy import create_mock_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.modules.audit.models import AuditLog
from app.modules.audit.services import AuditService
from sqlalchemy import create_engine

# Use an in-memory SQLite for testing the audit service
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_log_event_persistence(db_session):
    """Verify that AuditService correctly persists a log entry."""
    AuditService.log_event(
        db_session,
        action="test.action",
        change_summary="This is a test summary",
        user_id="test_user",
        details={"key": "value"}
    )
    db_session.commit()
    
    log = db_session.query(AuditLog).first()
    assert log is not None
    assert log.action == "test.action"
    assert log.user_id == "test_user"
    assert log.change_summary == "This is a test summary"
    assert log.details == {"key": "value"}

def test_log_event_system_action(db_session):
    """Verify that system actions (no user_id) are recorded correctly."""
    AuditService.log_event(
        db_session,
        action="system.startup",
        change_summary="System started successfully"
    )
    db_session.commit()
    
    log = db_session.query(AuditLog).first()
    assert log.user_id is None
    assert log.action == "system.startup"
