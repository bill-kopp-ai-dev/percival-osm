"""Exercise the container's stdio MCP contract without network access."""

from __future__ import annotations

import argparse
import json
import selectors
import subprocess
import sys
import time


def redact_secrets(text: str, entries: list[str]) -> str:
    for entry in entries:
        _, _, value = entry.partition("=")
        if value:
            text = text.replace(value, "[redacted]")
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--mount", action="append", default=[])
    parser.add_argument("--env", action="append", default=[])
    parser.add_argument("--secret-env", action="append", default=[])
    parser.add_argument("--expected-tool", action="append", default=[])
    parser.add_argument("--expected-uid", type=int)
    parser.add_argument("--compose-file", default="docker-compose.yml")
    parser.add_argument("--compose-service")
    parser.add_argument("--compose-profile", action="append", default=[])
    args = parser.parse_args()
    if args.expected_uid is not None:
        probe = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--network=none",
                "--entrypoint",
                "python",
                args.image,
                "-c",
                "import os; print(os.getuid())",
            ],
            check=False,
            text=True,
            capture_output=True,
            timeout=30,
        )
        if probe.returncode or probe.stdout.strip() != str(args.expected_uid):
            print(
                (
                    f"container UID mismatch: expected {args.expected_uid}, "
                    f"got {probe.stdout.strip()!r}"
                ),
                file=sys.stderr,
            )
            return 1
    if args.compose_service:
        compose = ["docker", "compose", "-f", args.compose_file]
        for profile in args.compose_profile:
            compose += ["--profile", profile]
        try:
            rendered = subprocess.run(
                [*compose, "config", "--format", "json"],
                check=False,
                text=True,
                capture_output=True,
                timeout=30,
            )
            config = json.loads(rendered.stdout) if rendered.returncode == 0 else {}
        except (json.JSONDecodeError, subprocess.TimeoutExpired):
            config = {}
        service = config.get("services", {}).get(args.compose_service)
        if not isinstance(service, dict):
            print(f"Compose service missing: {args.compose_service}", file=sys.stderr)
            return 1
        healthcheck = service.get("healthcheck")
        if (
            service.get("stdin_open") is not True
            or service.get("tty", False) is not False
            or service.get("ports")
            or service.get("restart") not in (None, "no")
            or (healthcheck and healthcheck.get("disable") is not True)
        ):
            print(
                f"Compose stdio contract failed for {args.compose_service}",
                file=sys.stderr,
            )
            return 1
    command = ["docker", "run", "--rm", "-i", "--network=none"]
    for mount in args.mount:
        command += ["--mount", mount]
    for item in args.env + args.secret_env:
        command += ["--env", item]
    command.append(args.image)
    requests = (
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "percival-ci", "version": "0.1.0"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    )
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except OSError as exc:
        print(f"failed to launch container: {exc}", file=sys.stderr)
        return 1
    assert process.stdin is not None and process.stdout is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    responses = []
    stdout_lines: list[str] = []

    def send(request: dict) -> None:
        process.stdin.write(json.dumps(request) + "\n")
        process.stdin.flush()

    def wait_for_response(request_id: int) -> bool:
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            if not selector.select(deadline - time.monotonic()):
                continue
            line = process.stdout.readline()
            if not line:
                break
            stdout_lines.append(line)
            try:
                response = json.loads(line)
            except json.JSONDecodeError:
                print(
                    f"stdout line is not JSON-RPC: {redact_secrets(line[:300], args.secret_env)!r}",
                    file=sys.stderr,
                )
                return False
            responses.append(response)
            if response.get("id") == request_id:
                return True
        return False

    try:
        send(requests[0])
        if not wait_for_response(1):
            raise RuntimeError("MCP initialize response timed out or was invalid")
        send(requests[1])
        send(requests[2])
        if not wait_for_response(2):
            raise RuntimeError("MCP tools/list response timed out or was invalid")
    except (BrokenPipeError, OSError, RuntimeError) as exc:
        process.kill()
        process.wait()
        print(str(exc), file=sys.stderr)
        print(
            redact_secrets(process.stderr.read()[-4000:], args.secret_env),
            file=sys.stderr,
        )
        return 1
    finally:
        selector.close()
    process.stdin.close()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        print("stdio MCP process did not exit after stdin closed", file=sys.stderr)
        return 1
    trailing_stdout = process.stdout.read()
    result_stdout = "".join(stdout_lines) + trailing_stdout
    result_stderr = process.stderr.read()
    for line in trailing_stdout.splitlines():
        if not line.strip():
            continue
        try:
            json.loads(line)
        except json.JSONDecodeError:
            print(
                f"stdout line is not JSON-RPC: {redact_secrets(line[:300], args.secret_env)!r}",
                file=sys.stderr,
            )
            return 1
    if process.returncode:
        print(
            f"container exited {process.returncode}; stderr follows:", file=sys.stderr
        )
        print(redact_secrets(result_stderr[-4000:], args.secret_env), file=sys.stderr)
        return 1
    by_id = {response.get("id"): response for response in responses if "id" in response}
    if 1 not in by_id or "result" not in by_id[1]:
        print("MCP initialize response missing or invalid", file=sys.stderr)
        return 1
    tools = by_id.get(2, {}).get("result", {}).get("tools")
    if not isinstance(tools, list) or not tools:
        print("tools/list returned no tools", file=sys.stderr)
        return 1
    names = {tool.get("name") for tool in tools if isinstance(tool, dict)}
    missing = sorted(set(args.expected_tool) - names)
    if missing:
        print(f"tools/list missing expected tools: {missing}", file=sys.stderr)
        return 1
    for item in args.secret_env:
        _, _, value = item.partition("=")
        if value and (value in result_stdout or value in result_stderr):
            print(
                "configured environment value leaked to stdio output", file=sys.stderr
            )
            return 1
    print(f"stdio MCP conformance passed: initialize + tools/list ({len(tools)} tools)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
