"""Tests for Docker & Local Run Scripts setup."""

from pathlib import Path
import yaml


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def test_docker_compose_structure():
    """Verify docker-compose.yml has correct syntax, services, and volume mounts."""
    root = get_project_root()
    compose_path = root / "docker-compose.yml"
    assert compose_path.exists(), "docker-compose.yml must exist at project root"

    with open(compose_path, "r", encoding="utf-8") as f:
        compose_data = yaml.safe_load(f)

    assert "services" in compose_data, "docker-compose.yml must define services"
    services = compose_data["services"]

    # 1. Backend service
    assert "backend" in services, "backend service must be defined"
    backend = services["backend"]
    assert backend["image"] == "portfolio-watch:backend"
    assert backend["build"]["context"] == "."
    assert backend["build"]["dockerfile"] == "src/backend/Dockerfile"
    assert backend["entrypoint"] == ["sh", "/docker-entrypoint.sh"]
    assert "backend.main:app" in " ".join(backend["command"])
    assert "pw_data:/app/data" in backend["volumes"]
    assert "./src:/app/src:ro" in backend["volumes"]
    assert "healthcheck" in backend, "backend must configure healthcheck"
    backend_env = backend.get("environment") or {}
    assert backend_env.get("HOME") == "/app/data"
    assert backend_env.get("XDG_CONFIG_HOME") == "/app/data/.config"
    assert backend_env.get("MPLCONFIGDIR") == "/app/data/.matplotlib"

    # 2. Frontend service
    assert "frontend" in services, "frontend service must be defined"
    frontend = services["frontend"]
    assert frontend["image"] == "portfolio-watch:frontend"
    assert frontend["build"]["context"] == "./src/frontend"
    assert frontend["build"]["dockerfile"] == "Dockerfile"
    assert "backend" in frontend["depends_on"]

    # 3. Volumes
    assert "volumes" in compose_data, "docker-compose.yml must define volumes"
    assert "pw_data" in compose_data["volumes"]
    assert compose_data["volumes"]["pw_data"]["name"] == "portfolio-watch-data"


def test_backend_dockerfile():
    """Verify src/backend/Dockerfile implements multi-stage build and non-root appuser."""
    root = get_project_root()
    dockerfile_path = root / "src" / "backend" / "Dockerfile"
    assert dockerfile_path.exists(), "src/backend/Dockerfile must exist"

    content = dockerfile_path.read_text(encoding="utf-8")

    # Multi-stage check
    assert "AS builder" in content, "Dockerfile must have builder stage"
    assert "AS runner" in content, "Dockerfile must have runner stage"

    # Non-root user check
    assert "gosu" in content, "Dockerfile must install gosu for dropping root privileges"
    assert "appuser" in content, "Dockerfile must configure appuser"
    assert "10001" in content, "Dockerfile must use uid/gid 10001 for appuser"
    assert "/opt/venv" in content, "Dockerfile must use virtualenv in /opt/venv"


def test_docker_entrypoint_script():
    """Verify src/backend/docker-entrypoint.sh fixes permissions and uses gosu."""
    root = get_project_root()
    entrypoint_path = root / "src" / "backend" / "docker-entrypoint.sh"
    assert entrypoint_path.exists(), "src/backend/docker-entrypoint.sh must exist"

    content = entrypoint_path.read_text(encoding="utf-8")
    assert content.startswith("#!/bin/sh"), "Entrypoint script must have #!/bin/sh shebang"
    assert "chown -R appuser:appuser /app/data" in content, "Entrypoint must fix data directory ownership"
    assert "exec gosu appuser" in content, "Entrypoint must step down privileges via gosu appuser"
    assert 'HOME="$APP_HOME"' in content, "Entrypoint must override gosu passwd HOME to /app/data"
    assert "/app/data/.config" in content, "Entrypoint must prepare writable config dirs"


def test_local_run_scripts():
    """Verify run_local.ps1 and run_local.sh exist and invoke uvicorn backend.main:app."""
    root = get_project_root()
    ps1_path = root / "scripts" / "run_local.ps1"
    sh_path = root / "scripts" / "run_local.sh"

    assert ps1_path.exists(), "scripts/run_local.ps1 must exist"
    assert sh_path.exists(), "scripts/run_local.sh must exist"

    ps1_content = ps1_path.read_text(encoding="utf-8")
    assert "uvicorn backend.main:app" in ps1_content
    assert "PYTHONPATH" in ps1_content
    assert ".env" in ps1_content

    sh_content = sh_path.read_text(encoding="utf-8")
    assert "uvicorn backend.main:app" in sh_content
    assert "PYTHONPATH" in sh_content
    assert ".env" in sh_content
