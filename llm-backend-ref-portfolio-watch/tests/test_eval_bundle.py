import json
import sys
from pathlib import Path

def test_run_golden_v5_eval_bundle(monkeypatch, tmp_path):
    """
    Test that the eval bundle script correctly calls run_detailed_evaluation
    and writes out the required directory structure.
    """
    # Create a mock for run_detailed_evaluation
    def mock_run_detailed_evaluation(*args, **kwargs):
        # We need to write dummy output to kwargs["output_md_path"] and kwargs["output_json_path"]
        md_path = kwargs.get("output_md_path")
        json_path = kwargs.get("output_json_path")
        
        if md_path:
            md_path.write_text("# Mock Markdown Report")
        if json_path:
            json_payload = {
                "timestamp": "2026-01-01T00:00:00Z",
                "dataset": "golden_v5.yaml",
                "summary": {
                    "total_cases": 2,
                    "passed_cases": 1,
                    "failed_cases": 1,
                    "pass_rate_pct": 50.0,
                    "by_slice": {"lookup": {"total": 2, "passed": 1, "rate": 0.5}}
                },
                "cases": []
            }
            json_path.write_text(json.dumps(json_payload))
            
        # detailed_results, json_payload
        return [], json_payload if json_path else {}
    
    # Patch the function where it is imported in the script
    # To do this safely, we will mock the function and then run the script's main
    
    # The script is in scripts/run_golden_v5_eval_bundle.py
    # We will import it dynamically.
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    
    import run_golden_v5_eval_bundle
    monkeypatch.setattr(run_golden_v5_eval_bundle, "run_detailed_evaluation", mock_run_detailed_evaluation)
    
    # Patch root_dir in the script to use tmp_path so it doesn't pollute actual specs
    monkeypatch.setattr(run_golden_v5_eval_bundle, "root_dir", tmp_path)
    
    # Set args to empty to use defaults
    monkeypatch.setattr(sys, "argv", ["run_golden_v5_eval_bundle.py"])
    
    run_golden_v5_eval_bundle.main()
    
    # Verify outputs
    specs_eval_dir = tmp_path / "specs" / "eval"
    runs_dir = specs_eval_dir / "runs"
    
    assert runs_dir.exists(), "Runs directory was not created"
    
    run_folders = list(runs_dir.iterdir())
    assert len(run_folders) == 1, "Expected exactly 1 run folder"
    
    run_dir = run_folders[0]
    
    assert (run_dir / "eval_results.md").exists(), "eval_results.md missing in run_dir"
    assert (run_dir / "eval_results.json").exists(), "eval_results.json missing in run_dir"
    assert (run_dir / "summary.json").exists(), "summary.json missing in run_dir"
    
    with open(run_dir / "summary.json", "r") as f:
        summary = json.load(f)
        assert summary["total_cases"] == 2
        assert summary["pass_rate"] == 50.0
        assert summary["slice_breakdown"] == {"lookup": {"total": 2, "passed": 1, "rate": 0.5}}

    assert (specs_eval_dir / "eval_results_golden_v5.md").exists(), "Latest symlink/copy MD missing"
    assert (specs_eval_dir / "eval_results_golden_v5.json").exists(), "Latest symlink/copy JSON missing"
