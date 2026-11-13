"""Pytest plugin providing the Qt UI audit driver fixture."""

import pytest
from typing import Any, Generator
from audit_helper import QtAuditDriver, UiRecorder


@pytest.fixture
def ui(qapp: Any) -> Generator[QtAuditDriver, None, None]:
    recorder = UiRecorder()
    driver = QtAuditDriver(qapp, recorder)
    yield driver
    recorder.save()
