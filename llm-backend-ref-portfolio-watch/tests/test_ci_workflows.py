import os
import yaml

def test_ci_workflow_exists():
    path = ".github/workflows/ci.yml"
    assert os.path.exists(path), "ci.yml workflow file missing"
    
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        
    on_key = "on" if "on" in data else True
    assert on_key in data
    assert "push" in data[on_key]
    assert "pull_request" in data[on_key]
    
    steps = data["jobs"]["test"]["steps"]
    step_runs = [s.get("run") for s in steps if "run" in s]
    
    assert data["jobs"]["test"].get("env", {}).get("PYTHONPATH") == "src"
    assert any("pip install -e" in r for r in step_runs)
    assert any("prompt_lint" in r for r in step_runs)
    assert any("pytest" in r for r in step_runs)


def test_eval_gate_workflow_exists():
    path = ".github/workflows/eval-gate.yml"
    assert os.path.exists(path), "eval-gate.yml workflow file missing"
    
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        
    on_key = "on" if "on" in data else True
    assert on_key in data
    assert "pull_request" in data[on_key]
    
    # Path filters should exist
    paths = data[on_key]["pull_request"]["paths"]
    assert "resources/prompts/**" in paths
    assert "src/backend/**" in paths
    assert "resources/eval/**" in paths
    
    job = data["jobs"]["eval_gate"]
    assert job.get("env", {}).get("PYTHONPATH") == "src"
    assert job.get("env", {}).get("LLM_MODEL") == "gpt-4o-mini"

    steps = job["steps"]

    # Check cache
    cache_step = next((s for s in steps if s.get("uses") and "actions/cache" in s["uses"]), None)
    assert cache_step is not None
    assert "resources/prompts" in cache_step["with"]["key"]
    
    # Check eval run and gate run
    step_runs = [s.get("run", "") for s in steps]
    assert any("backend.eval.run" in r and "--subset" in r for r in step_runs)
    assert any("backend.eval.gate" in r and "pr_report.json" in r for r in step_runs)
