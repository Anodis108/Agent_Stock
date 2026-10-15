"""Unit test suite cho Phase 3.2: AI Application Layer (src/ai_backend/application/).

Kiểm tra:
1. SwarmOrchestrator: Kế thừa BaseService, Fast-path Chào hỏi, Stream SSE events, Process input/output.
2. ConceptRagService: Kế thừa BaseService, Khớp khái niệm 5 file markdown (RSI, ATO, Trần/Sàn), Trả về 'Không có trong tài liệu.' khi không tìm thấy.
3. SymbolScannerService: Kế thừa BaseService, Quét biến động giá, Kiểm tra ngưỡng threshold_pct, Đánh giá Gate 1 HITL.
4. Eval Gate & Helpers: check_gates, GateResult, GATES thresholds, normalize_steps, mark_mid_run_error.
"""

from __future__ import annotations

import pytest

from common.base.base_service import BaseService
from ai_backend.application.swarm_orchestrator import (
    SwarmInput,
    SwarmOrchestrator,
    SwarmOutput,
    is_greeting,
)
from ai_backend.application.concept_rag_service import (
    ConceptRagInput,
    ConceptRagOutput,
    ConceptRagService,
    NOT_IN_DOCS,
)
from ai_backend.application.symbol_scanner_service import (
    SymbolScannerInput,
    SymbolScannerOutput,
    SymbolScannerService,
)
from ai_backend.application.eval.gate import (
    GATES,
    GateResult,
    check_gates,
    format_gate_result,
    normalize_gate_report,
)
from ai_backend.application.eval.steps import (
    ensure_steps_reflect_error,
    mark_mid_run_error,
    normalize_steps,
)


# ==============================================================================
# 1. Tests cho SwarmOrchestrator
# ==============================================================================

class TestSwarmOrchestrator:
    def test_subclass_of_base_service(self):
        assert issubclass(SwarmOrchestrator, BaseService)

    def test_greeting_detection(self):
        assert is_greeting("Xin chào bot")
        assert is_greeting("hello bạn")
        assert is_greeting("Hi trợ lý")
        assert is_greeting("chào bạn")
        assert not is_greeting("Giá cổ phiếu HPG hôm nay bao nhiêu?")
        assert not is_greeting("RSI là gì")

    def test_greeting_fastpath_process(self):
        orch = SwarmOrchestrator()
        inp = SwarmInput(question="Xin chào bạn")
        out = orch.process(inp)

        assert isinstance(out, SwarmOutput)
        assert out.routing == "greeting"
        assert "Xin chào" in out.answer
        assert len(out.steps) >= 1
        assert any(s["name"] == "greeting_fastpath" for s in out.steps)

    def test_standard_question_process(self):
        orch = SwarmOrchestrator()
        inp = SwarmInput(question="Giá HPG hiện tại thế nào?", user_id="user_test")
        out = orch.process(inp)

        assert isinstance(out, SwarmOutput)
        assert out.question == "Giá HPG hiện tại thế nào?"
        assert len(out.answer) > 0
        assert len(out.steps) >= 1

    def test_streaming_greeting(self):
        orch = SwarmOrchestrator()
        events = list(orch.stream(question="Xin chào", user_id="user_test"))
        event_names = [e[0] for e in events]

        assert "node_start" in event_names
        assert "token" in event_names
        assert "node_finish" in event_names
        assert "complete" in event_names

        complete_event = next(e[1] for e in events if e[0] == "complete")
        assert complete_event["route"] == "greeting"
        assert "Xin chào" in complete_event["answer"]

    def test_streaming_general_question(self):
        orch = SwarmOrchestrator()
        events = list(orch.stream(question="Phân tích mã FPT", user_id="user_test"))
        event_names = [e[0] for e in events]

        assert "node_start" in event_names
        assert "token" in event_names
        assert "complete" in event_names

        tokens = [e[1]["token"] for e in events if e[0] == "token"]
        assert len(tokens) > 0
        reconstructed = "".join(tokens)
        complete_event = next(e[1] for e in events if e[0] == "complete")
        assert complete_event["answer"] == reconstructed.strip()


# ==============================================================================
# 2. Tests cho ConceptRagService
# ==============================================================================

class TestConceptRagService:
    def test_subclass_of_base_service(self):
        assert issubclass(ConceptRagService, BaseService)

    def test_concept_rsi_found(self):
        service = ConceptRagService()
        inp = ConceptRagInput(question="RSI là gì")
        out = service.process(inp)

        assert isinstance(out, ConceptRagOutput)
        assert out.relevant is True
        assert out.source_file == "rsi-va-sma.md"
        assert "RSI" in out.answer

    def test_concept_ato_found(self):
        service = ConceptRagService()
        inp = ConceptRagInput(question="Lệnh ATO là gì")
        out = service.process(inp)

        assert isinstance(out, ConceptRagOutput)
        assert out.relevant is True
        assert out.source_file == "lenh-ato-atc-lo.md"
        assert "ATO" in out.answer

    def test_concept_gia_tran_found(self):
        service = ConceptRagService()
        inp = ConceptRagInput(question="Giá trần là gì")
        out = service.process(inp)

        assert isinstance(out, ConceptRagOutput)
        assert out.relevant is True
        assert out.source_file == "gia-tran-san.md"
        assert "trần" in out.answer.lower()

    def test_concept_out_of_scope_fallback(self):
        service = ConceptRagService()
        inp = ConceptRagInput(question="Thời tiết ngày mai ở Hà Nội thế nào?")
        out = service.process(inp)

        assert isinstance(out, ConceptRagOutput)
        assert out.relevant is False
        assert out.source_file is None
        assert out.answer == NOT_IN_DOCS

    def test_empty_question(self):
        service = ConceptRagService()
        inp = ConceptRagInput(question="")
        out = service.process(inp)

        assert out.relevant is False
        assert out.source_file is None
        assert out.answer == NOT_IN_DOCS


# ==============================================================================
# 3. Tests cho SymbolScannerService
# ==============================================================================

class TestSymbolScannerService:
    def test_subclass_of_base_service(self):
        assert issubclass(SymbolScannerService, BaseService)

    def test_symbol_scan_triggered_on_low_threshold(self):
        scanner = SymbolScannerService()
        # Ngưỡng cực thấp 0.001% chắc chắn bị vượt
        inp = SymbolScannerInput(symbol="HPG", threshold_pct=0.001)
        out = scanner.process(inp)

        assert isinstance(out, SymbolScannerOutput)
        assert out.symbol == "HPG"
        assert out.route == "technical"
        assert out.threshold_pct == 0.001
        assert out.triggered is True
        assert "vượt ngưỡng" in out.reason
        assert len(out.steps) >= 2

    def test_symbol_scan_not_triggered_on_high_threshold(self):
        scanner = SymbolScannerService()
        # Ngưỡng cực cao 100% không thể bị vượt
        inp = SymbolScannerInput(symbol="VNM", threshold_pct=100.0)
        out = scanner.process(inp)

        assert isinstance(out, SymbolScannerOutput)
        assert out.symbol == "VNM"
        assert out.triggered is False
        assert "nằm trong giới hạn" in out.reason

    def test_scan_helper_method(self):
        scanner = SymbolScannerService()
        res = scanner.scan(symbol="VCB", user_id="user_demo", threshold_pct=2.5)

        assert res.symbol == "VCB"
        assert res.threshold_pct == 2.5
        assert len(res.alerts) == 1
        assert res.alerts[0].symbol == "VCB"
        assert len(res.steps) >= 2


# ==============================================================================
# 4. Tests cho Eval Gate & Steps
# ==============================================================================

class TestEvalGateAndSteps:
    def test_gate_constants(self):
        assert "overall" in GATES
        assert "rule_pass_rate" in GATES
        assert "slice:injection" in GATES
        assert "slice:out_of_scope" in GATES
        assert GATES["slice:injection"]["baseline"] == 1.00
        assert GATES["slice:injection"]["drop_tolerance"] == 0.00

    def test_check_gates_pass(self):
        passing_report = {
            "rate": 0.88,
            "rule_pass_rate": 0.94,
            "by_slice": {
                "injection": {"rate": 1.0, "total": 5, "passed": 5},
                "out_of_scope": {"rate": 1.0, "total": 5, "passed": 5},
            },
        }
        res = check_gates(passing_report)
        assert isinstance(res, GateResult)
        assert res.passed is True
        formatted = format_gate_result(res)
        assert "Gate OK" in formatted

    def test_check_gates_fail_on_injection(self):
        failing_report = {
            "rate": 0.90,
            "rule_pass_rate": 0.95,
            "by_slice": {
                "injection": {"rate": 0.8, "total": 5, "passed": 4, "failed": 1},
                "out_of_scope": {"rate": 1.0, "total": 5, "passed": 5},
            },
        }
        res = check_gates(failing_report)
        assert res.passed is False
        formatted = format_gate_result(res)
        assert "Gate FAIL" in formatted
        assert "slice:injection" in formatted

    def test_check_gates_fail_on_overall_drop(self):
        failing_report = {
            "rate": 0.75,  # Dưới 0.85 - 0.03 = 0.82
            "rule_pass_rate": 0.95,
            "by_slice": {
                "injection": {"rate": 1.0, "total": 5, "passed": 5},
                "out_of_scope": {"rate": 1.0, "total": 5, "passed": 5},
            },
        }
        res = check_gates(failing_report)
        assert res.passed is False

    def test_steps_normalization(self):
        raw = [{"name": "price_agent", "status": "DONE"}, {"name": "chart_agent"}]
        norm = normalize_steps(raw)
        assert len(norm) == 2
        assert norm[0]["id"] == "1"
        assert norm[0]["status"] == "done"
        assert norm[1]["id"] == "2"
        assert norm[1]["status"] == "done"

    def test_steps_error_marking(self):
        steps = [{"id": "1", "name": "step1", "status": "done"}]
        marked = ensure_steps_reflect_error(steps, error="Timeout calling Vnstock")
        assert any(s["status"] == "error" for s in marked)
        err_step = next(s for s in marked if s["status"] == "error")
        assert "Timeout calling Vnstock" in err_step.get("detail", "")
