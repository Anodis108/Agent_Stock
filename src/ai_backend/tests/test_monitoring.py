import subprocess


def test_cost_dashboard_script_runs():
    # Run the dashboard script in a subprocess
    import sys
    result = subprocess.run(
        [sys.executable, "scripts/cost_dashboard.py"],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "src", **import_os_env()}
    )
    assert result.returncode == 0
    assert "Dashboard generated" in result.stdout

def import_os_env():
    import os
    return os.environ.copy()
