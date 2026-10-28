"""Unit test suite cho Phase 3.2: AI Application Layer (src/ai_backend/application/).

Kiểm tra:
1. SwarmOrchestrator: Kế thừa BaseService, Fast-path Chào hỏi, Stream SSE events, Process input/output.
2. RagService: Kế thừa BaseService, Khớp khái niệm 5 file markdown (RSI, ATO, Trần/Sàn), Trả về 'Không có trong tài liệu.' khi không tìm thấy.
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
)
from ai_backend.application.rag_service import NOT_IN_DOCS, RagInput, RagOutput, RagService
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
)
from ai_backend.infra.eval.steps import (
    ensure_steps_reflect_error,
    normalize_steps,
)


# ==============================================================================
# 1. Tests cho SwarmOrchestrator
# ==============================================================================

class TestSwarmOrchestrator:
    def test_subclass_of_base_service(self):
        assert issubclass(SwarmOrchestrator, BaseService)

    def test_requires_graph_runner(self):
        with pytest.raises(RuntimeError, match="graph_runner"):
            SwarmOrchestrator().process(SwarmInput(question="Giá HPG?"))

    def test_standard_question_process(self, fake_chat_runner):
        orch = SwarmOrchestrator(graph_runner=fake_chat_runner)
        inp = SwarmInput(question="Giá HPG hiện tại thế nào?", user_id="user_test")
        out = orch.process(inp)

        assert isinstance(out, SwarmOutput)
        assert out.question == "Giá HPG hiện tại thế nào?"
        assert len(out.answer) > 0
        assert len(out.steps) >= 1

    def test_streaming_general_question(self, fake_chat_runner):
        orch = SwarmOrchestrator(graph_runner=fake_chat_runner)
        events = list(orch.stream(question="Phân tích mã FPT", user_id="user_test"))
        event_names = [e[0] for e in events]

        assert "node_start" in event_names
        assert "token" in event_names
        assert "complete" in event_names

        tokens = [e[1]["delta"] for e in events if e[0] == "token"]
        assert len(tokens) > 0
        reconstructed = "".join(tokens)
        complete_event = next(e[1] for e in events if e[0] == "complete")
        assert complete_event["answer"] == reconstructed.strip()


# ==============================================================================
# 2. Tests cho RagService
# ==============================================================================

class TestRagService:
    def test_subclass_of_base_service(self):
        assert issubclass(RagService, BaseService)

    def test_concept_rsi_found(self):
        service = RagService()
        inp = RagInput(question="RSI là gì")
        out = service.process(inp)

        assert isinstance(out, RagOutput)
        assert out.relevant is True
        assert out.source_file == "rsi-va-sma.md"
        assert "RSI" in out.answer

    def test_concept_ato_found(self):
        service = RagService()
        inp = RagInput(question="Lệnh ATO là gì")
        out = service.process(inp)

        assert isinstance(out, RagOutput)
        assert out.relevant is True
        assert out.source_file == "lenh-ato-atc-lo.md"
        assert "ATO" in out.answer

    def test_concept_gia_tran_found(self):
        service = RagService()
        inp = RagInput(question="Giá trần là gì")
        out = service.process(inp)

        assert isinstance(out, RagOutput)
        assert out.relevant is True
        assert out.source_file == "gia-tran-san.md"
        assert "trần" in out.answer.lower()

    def test_concept_out_of_scope_fallback(self):
        service = RagService()
        inp = RagInput(question="Thời tiết ngày mai ở Hà Nội thế nào?")
        out = service.process(inp)

        assert isinstance(out, RagOutput)
        assert out.relevant is False
        assert out.source_file is None
        assert out.answer == NOT_IN_DOCS

    def test_empty_question(self):
        service = RagService()
        inp = RagInput(question="")
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

    def test_requires_graph_runner(self):
        # Không còn kết quả giả lập: thiếu graph thì báo lỗi rõ ràng
        with pytest.raises(RuntimeError, match="graph_runner"):
            SymbolScannerService().process(SymbolScannerInput(symbol="HPG"))

    def test_abnormal_result_is_triggered(self, fake_scan_runner):
        scanner = SymbolScannerService(graph_runner=fake_scan_runner(change_pct=-6.0, abnormal=True))
        out = scanner.process(SymbolScannerInput(symbol="hpg", threshold_pct=3.0))

        assert isinstance(out, SymbolScannerOutput)
        assert out.symbol == "HPG"
        assert out.route == "bất thường"
        assert out.change_pct == -6.0
        assert out.triggered is True
        assert len(out.steps) >= 2

    def test_normal_result_is_not_triggered(self, fake_scan_runner):
        scanner = SymbolScannerService(graph_runner=fake_scan_runner(change_pct=0.5, abnormal=False))
        out = scanner.process(SymbolScannerInput(symbol="VNM", threshold_pct=3.0))

        assert out.route == "bình thường"
        assert out.triggered is False

    def test_scan_helper_method(self, fake_scan_runner):
        scanner = SymbolScannerService(graph_runner=fake_scan_runner())
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
        assert "Timeout calling Vnstock" in err_step["detail"]
