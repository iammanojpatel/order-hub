"""Contract tests — Schemathesis generates hundreds of requests from the OpenAPI spec and
verifies: no 5xx, responses match the documented schemas/status codes/content types."""

import time
import uuid

import jwt
import schemathesis
from schemathesis import Case

from app.config import get_settings
from app.main import create_app
from tests.conftest import TEST_SETTINGS
from tests.fakes import FakeDatabase

_db = FakeDatabase()
app = create_app(TEST_SETTINGS, uow_factory=_db.uow)
app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
app.state.uow_factory = _db.uow

# /health/ready needs a real DB (covered by integration/smoke tests)
schema = schemathesis.openapi.from_asgi("/openapi.json", app).exclude(path="/health/ready")

_TOKEN = jwt.encode(
    {
        "sub": "contract-bot",
        "tid": str(uuid.uuid4()),
        "roles": ["admin"],
        "iss": TEST_SETTINGS.jwt_issuer,
        "aud": TEST_SETTINGS.jwt_audience,
        "exp": int(time.time()) + 3600,
    },
    TEST_SETTINGS.jwt_secret.get_secret_value(),
    algorithm="HS256",
)


@schema.parametrize()
def test_api_conforms_to_openapi(case: Case) -> None:
    case.call_and_validate(headers={"Authorization": f"Bearer {_TOKEN}"})
