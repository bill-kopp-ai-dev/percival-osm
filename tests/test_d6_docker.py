"""Tests for the Docker deployment artifacts (Dockerfile, entrypoint, compose).

These tests are pure-Python: they validate the *static* properties of the
deployment files (existence, structure, expected configuration values) so
that simple mistakes like removing the tini init, dropping the
non-root user, or hardcoding a token default are caught in CI without
needing a Docker daemon.
"""

import os
import re
import stat
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = REPO_ROOT / "Dockerfile"
ENTRYPOINT = REPO_ROOT / "docker-entrypoint.sh"
COMPOSE = REPO_ROOT / "docker-compose.yml"
DOCKERIGNORE = REPO_ROOT / ".dockerignore"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "docker-build.sh"
SMOKE_SCRIPT = REPO_ROOT / "scripts" / "docker-smoke-test.sh"
INSPECT_SCRIPT = REPO_ROOT / "scripts" / "docker-inspect.sh"
CATALOG_DIR = REPO_ROOT / "servers" / "percival-osm"
CATALOG_SERVER = CATALOG_DIR / "server.yaml"
CATALOG_TOOLS = CATALOG_DIR / "tools.json"
CATALOG_README = CATALOG_DIR / "readme.md"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "docker.yml"


def test_dockerfile_exists() -> None:
    assert DOCKERFILE.is_file(), "Dockerfile is required for first-class Docker support"


def test_dockerfile_uses_non_root_user() -> None:
    """The runtime stage must declare USER percival (uid 10001) so the
    container never starts as root under default ``docker run``."""
    content = DOCKERFILE.read_text(encoding="utf-8")
    # The runtime stage (the last ``FROM``) must set USER.
    matches = re.findall(r"^USER\s+(\S+)", content, flags=re.MULTILINE)
    assert matches, "Dockerfile must declare a USER directive"
    assert "percival" in matches[-1], (
        f"runtime stage must use a non-root user, got USER {matches[-1]}"
    )
    # The UID 10001 is set on the useradd line (we can't put it directly
    # in the USER directive because that breaks RHEL/CentOS-style images).
    assert re.search(r"--uid\s+10001", content), (
        "non-root user must be created with --uid 10001 so it matches the compose file"
    )


def test_stdio_image_disables_transport_agnostic_healthcheck() -> None:
    content = DOCKERFILE.read_text(encoding="utf-8")
    assert re.search(r"^HEALTHCHECK\s+NONE\s*$", content, flags=re.MULTILINE), (
        "The default stdio image must not inherit a process-only HTTP healthcheck"
    )
    assert "pgrep" not in content, "the runtime image must not depend on pgrep"


def test_dockerfile_uses_tini_for_signal_reaping() -> None:
    content = DOCKERFILE.read_text(encoding="utf-8")
    assert "tini" in content, "PID 1 reaper (tini) is required for clean signal handling"
    assert "/usr/bin/tini" in content, "tini must be the ENTRYPOINT, not just installed"


def test_dockerfile_drops_capabilities_in_compose() -> None:
    """Verify compose also drops ALL capabilities and pins no-new-privileges."""
    content = COMPOSE.read_text(encoding="utf-8")
    assert "cap_drop" in content and "ALL" in content
    assert "no-new-privileges:true" in content


def test_dockerfile_resource_limits_align_with_docker_mcp_toolkit() -> None:
    """The Docker MCP Toolkit caps MCP containers at 1 CPU / 2 GB by default.
    The compose file should declare matching resource limits so the image
    runs in profiles without surprise throttling."""
    content = COMPOSE.read_text(encoding="utf-8")
    assert re.search(r"cpus:\s*\"1\"", content), "compose must cap CPU at 1"
    assert re.search(r"memory:\s*\d+[MG]", content), "compose must cap memory"


def test_entrypoint_exists_and_is_executable() -> None:
    assert ENTRYPOINT.is_file()
    mode = stat.S_IMODE(os.stat(ENTRYPOINT).st_mode)
    assert mode & 0o111, f"docker-entrypoint.sh must be executable, got mode {oct(mode)}"


def test_entrypoint_validates_required_env() -> None:
    """The entrypoint must check USER_AGENT and FROM_HEADER before exec
    so a misconfigured container fails loudly with a clear error."""
    content = ENTRYPOINT.read_text(encoding="utf-8")
    assert "USER_AGENT" in content
    assert "FROM_HEADER" in content
    assert re.search(r"exit\s+78", content), "missing-env failure should use EX_CONFIG (78)"


def test_entrypoint_refuses_root_invocation() -> None:
    content = ENTRYPOINT.read_text(encoding="utf-8")
    assert re.search(r"id -u.*=.*0", content), (
        "entrypoint must check whether it is running as root"
    )
    assert re.search(r"refus", content, flags=re.IGNORECASE), (
        "entrypoint must refuse to run as root"
    )


def test_entrypoint_supports_both_transport_modes() -> None:
    content = ENTRYPOINT.read_text(encoding="utf-8")
    for mode in ("stdio", "sse", "streamable-http"):
        assert mode in content, f"entrypoint must support {mode} mode"


def test_compose_stdio_is_non_tty_without_http_health_or_restart() -> None:
    import yaml

    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    service = compose["services"]["mcp-osm"]
    assert service["stdin_open"] is True
    assert service["tty"] is False
    assert service["restart"] == "no"
    assert "ports" not in service
    assert service["healthcheck"]["disable"] is True


def test_compose_http_profile_keeps_auth_bind_and_health_probe() -> None:
    import yaml

    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    service = compose["services"]["mcp-osm-http"]
    environment = service["environment"]
    probe = " ".join(service["healthcheck"]["test"])
    assert service["profiles"] == ["http"]
    assert service["ports"] == ["${HTTP_BIND_ADDRESS:-127.0.0.1}:${HTTP_PORT:-8080}:8080"]
    assert environment["USER_AGENT"].startswith("${USER_AGENT:?")
    assert environment["FROM_HEADER"].startswith("${FROM_HEADER:?")
    assert environment["MCP_OSM_AUTH_TOKEN"].startswith("${MCP_OSM_AUTH_TOKEN:?")
    assert environment["ALLOW_REMOTE_HTTP"] == "true"
    assert "http://127.0.0.1:8080/" in probe
    assert "200|401|404|405" in probe
    assert "pgrep" not in probe


def test_compose_pins_user_to_10001() -> None:
    content = COMPOSE.read_text(encoding="utf-8")
    assert "10001:10001" in content, (
        "compose must pin user: to 10001:10001 so it matches the Dockerfile"
    )


def test_dockerignore_blocks_secrets_and_tests() -> None:
    content = DOCKERIGNORE.read_text(encoding="utf-8")
    # The .env file is the most common source of accidentally-baked secrets.
    assert re.search(r"^\.env(\.|$)", content, flags=re.MULTILINE), (
        ".dockerignore must block .env files (but allow .env.example via the negation rule)"
    )
    assert "tests" in content, ".dockerignore must block the test tree"


def test_dockerignore_allows_readme_for_hatchling() -> None:
    content = DOCKERIGNORE.read_text(encoding="utf-8")
    # The build pipeline runs `uv sync` which needs the README to be
    # available; the negation rule for *.md must allow it through.
    assert "*.md" in content, ".dockerignore should blanket-exclude markdown"
    assert "!README.md" in content, "README.md must be whitelisted for the build"


@pytest.mark.parametrize("script", [BUILD_SCRIPT, SMOKE_SCRIPT, INSPECT_SCRIPT])
def test_helper_scripts_are_executable(script: Path) -> None:
    assert script.is_file(), f"{script.name} must exist"
    mode = stat.S_IMODE(os.stat(script).st_mode)
    assert mode & 0o111, f"{script.name} must be executable, got mode {oct(mode)}"


def test_build_script_supports_platform_flag() -> None:
    content = BUILD_SCRIPT.read_text(encoding="utf-8")
    assert "--platform=" in content, (
        "build script must accept --platform=<arch> for multi-arch builds"
    )
    assert "buildx build" in content, (
        "build script must use docker buildx so multi-arch works"
    )


def test_inspect_script_validates_image_exists() -> None:
    content = INSPECT_SCRIPT.read_text(encoding="utf-8")
    assert "docker image inspect" in content
    assert "not found" in content.lower() or "missing" in content.lower(), (
        "inspect script must refuse to run against a missing image"
    )


def test_ci_workflow_exists_and_builds_matrix() -> None:
    """The repo must ship a CI workflow so a broken Dockerfile is caught
    on every PR."""
    assert CI_WORKFLOW.is_file(), ".github/workflows/docker.yml is required for CI"
    content = CI_WORKFLOW.read_text(encoding="utf-8")
    assert "matrix" in content, "CI must build across a platform matrix"
    assert "linux/amd64" in content and "linux/arm64" in content, (
        "CI must cover the same architectures the build script advertises"
    )
    assert "docker-smoke-test.sh" in content or "scripts/docker-smoke-test.sh" in content, (
        "CI must invoke the smoke test against the freshly built image"
    )


def test_docker_mcp_catalog_entry_exists() -> None:
    """The Docker MCP catalog submission format requires three artifacts
    under ``servers/<name>/``:
    - ``server.yaml`` — server definition
    - ``tools.json``  — list of exposed tools (or [] for dynamic)
    - ``readme.md``    — documentation link
    """
    assert CATALOG_DIR.is_dir(), "servers/percival-osm/ directory must exist"
    assert CATALOG_SERVER.is_file()
    assert CATALOG_TOOLS.is_file()
    assert CATALOG_README.is_file()


def test_docker_mcp_catalog_server_yaml_minimum_fields() -> None:
    import yaml

    payload = yaml.safe_load(CATALOG_SERVER.read_text(encoding="utf-8"))
    for field in ("name", "image", "type", "meta", "about", "source", "config"):
        assert field in payload, f"server.yaml missing required field: {field}"
    assert payload["type"] == "server", "type must be 'server' for a local container"
    assert "category" in payload["meta"], "meta.category is required"
    assert "USER_AGENT" in str(payload["config"]).upper()
    assert "FROM_HEADER" in str(payload["config"]).upper()


def test_docker_mcp_catalog_tools_json_has_canonical_tools() -> None:
    import json

    tools = json.loads(CATALOG_TOOLS.read_text(encoding="utf-8"))
    names = {t["name"] for t in tools}
    expected = {
        "osm_find_nearby",
        "osm_find_place",
        "osm_find_address",
        "osm_geocode",
        "osm_navigate",
        "osm_directions",
        "osm_get_health",
        "osm_get_version",
    }
    missing = expected - names
    assert not missing, f"tools.json missing canonical tools: {sorted(missing)}"


def test_docker_mcp_catalog_readme_links_back_to_repo() -> None:
    content = CATALOG_README.read_text(encoding="utf-8")
    assert "github.com/bill-kopp-ai-dev/percival-osm" in content
