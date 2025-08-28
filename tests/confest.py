import os
import types
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base
from app import database

# --- Use SQLite in-memory for unit tests (fast & isolated) ---
TEST_DB_URL = "sqlite+pysqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False}, future=True)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)

# Override the app's get_db dependency
@pytest.fixture(autouse=True)
def _override_db(monkeypatch):
    def _get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    monkeypatch.setattr(database, "SessionLocal", TestingSessionLocal, raising=True)
    return

# Disable external APIs (Stripe/OpenAI) during tests
@pytest.fixture(autouse=True)
def _stub_external(monkeypatch):
    # Fake stripe module
    fake_stripe = types.SimpleNamespace()
    class _Sess: 
        @staticmethod
        def create(**kwargs): 
            return types.SimpleNamespace(id="cs_test_123")
    fake_stripe.checkout = types.SimpleNamespace(Session=_Sess)
    monkeypatch.setitem(os.environ, "STRIPE_SECRET", "sk_test_x")
    monkeypatch.setitem(os.environ, "STRIPE_PUB", "pk_test_x")
    # Fake OpenAI client usage in your routes
    monkeypatch.setitem(os.environ, "OPENROUTER_API_KEY", "or_test")
    monkeypatch.setitem(os.environ, "LLM_PROVIDER", "openrouter")
    return

@pytest.fixture
def client():
    return TestClient(app)
