"""Test module for Capstone M3."""

import os
import subprocess
from pathlib import Path
import pytest
import yaml

from scripts.hitl_to_golden_draft import process_feedback
from backend.infra.cache.exact import ExactCache

def test_hitl_to_golden_draft_from_sample(tmp_path: Path):
    """Test generating draft from a hitl_feedback.json."""
    input_file = tmp_path / "hitl_feedback.json"
    output_dir = tmp_path / "drafts"
    
    # We write a sample JSON
    import json
    data = [
        {
            "id": "11111111",
            "question": "FPT?",
            "is_positive": False,
            "rating": 1,
            "reason": "Sai số liệu",
            "user_feedback": "Check again"
        },
        {
            "id": "22222222",
            "question": "HPG?",
            "is_positive": True,
            "rating": 5
        }
    ]
    input_file.write_text(json.dumps(data), encoding="utf-8")
    
    ret = process_feedback(input_file, output_dir, dry_run=False)
    assert ret == 0
    assert output_dir.exists()
    
    draft_files = list(output_dir.glob("*.yaml"))
    assert len(draft_files) == 1
    
    content = draft_files[0].read_text(encoding="utf-8")
    draft = yaml.safe_load(content)
    assert len(draft) == 1
    assert draft[0]["id"] == "hitl_draft_11111111"
    assert "From HITL feedback" in draft[0]["expected"]
    assert draft[0]["metadata"]["source"] == "hitl"

def test_pipeline_doc_exists():
    """Verify the M3 production pipeline document exists."""
    doc_path = Path(__file__).resolve().parents[1] / "resources" / "docs" / "m3-production-pipeline.md"
    assert doc_path.exists()
    content = doc_path.read_text(encoding="utf-8")
    assert "flowchart TD" in content or "flowchart LR" in content
    assert "hitl_to_golden_draft.py" in content

def test_v5_baseline_gate_passes():
    """Test gate on specs/eval/v5_baseline.json passes."""
    script = Path(__file__).resolve().parents[1] / "src" / "backend" / "eval" / "gate.py"
    baseline = Path(__file__).resolve().parents[1] / "specs" / "eval" / "v5_baseline.json"
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONIOENCODING"] = "utf8"
    
    result = subprocess.run(
        [sys.executable, str(script), "--run", str(baseline)],
        env=env,
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "Gate OK" in result.stdout

def test_connection_audit_cache_prompt_version():
    """Verify cache keys include prompt_version."""
    cache = ExactCache()
    import inspect
    sig = inspect.signature(cache.make_key)
    assert "prompt_version" in sig.parameters

def test_connection_audit_ci_paths():
    """Verify eval-gate.yml contains proper paths."""
    yaml_path = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "eval-gate.yml"
    assert yaml_path.exists()
    content = yaml_path.read_text(encoding="utf-8")
    assert "resources/prompts/**" in content
    assert "src/backend/**" in content
    assert "resources/eval/**" in content

def test_connection_audit_smoke_fpt_question():
    """Verify smoke test asks FPT."""
    smoke_path = Path(__file__).resolve().parents[1] / "deploy" / "smoke.py"
    assert smoke_path.exists()
    content = smoke_path.read_text(encoding="utf-8")
    assert "FPT" in content
    assert "FPT_MARKERS" in content

import sys
