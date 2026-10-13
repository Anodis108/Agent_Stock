"""Routes re-export for backward compatibility."""
from __future__ import annotations

from backend.api.routers.v1 import *
from backend.api.routers.v1 import router
from backend.application.answer_question import answer_question
from backend.application.scan_symbol import scan_symbol
