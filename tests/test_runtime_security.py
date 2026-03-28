import pytest

from percival_osm_mcp.server import _is_loopback_host, _validate_http_runtime_security


def test_is_loopback_host_values() -> None:
    assert _is_loopback_host("127.0.0.1") is True
    assert _is_loopback_host("localhost") is True
    assert _is_loopback_host("::1") is True
    assert _is_loopback_host("0.0.0.0") is False


def test_validate_http_security_rejects_remote_without_flag() -> None:
    with pytest.raises(ValueError, match="allow-remote-http"):
        _validate_http_runtime_security(
            mode="sse",
            host="0.0.0.0",
            allow_remote_http=False,
            auth_token=None,
            auth_token_env="MCP_OSM_AUTH_TOKEN",
        )


def test_validate_http_security_rejects_remote_without_token() -> None:
    with pytest.raises(ValueError, match="requires authentication"):
        _validate_http_runtime_security(
            mode="streamable-http",
            host="0.0.0.0",
            allow_remote_http=True,
            auth_token=None,
            auth_token_env="MCP_OSM_AUTH_TOKEN",
        )


def test_validate_http_security_accepts_remote_with_token() -> None:
    _validate_http_runtime_security(
        mode="streamable-http",
        host="0.0.0.0",
        allow_remote_http=True,
        auth_token="token",
        auth_token_env="MCP_OSM_AUTH_TOKEN",
    )
