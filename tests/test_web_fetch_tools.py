from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import socket
import threading

import pytest

from atomic_agent.models import AgentAction, AgentActionType
from atomic_agent.web_fetch_tools import (
    NetworkAllowRule,
    NetworkPolicy,
    WebFetchToolConfig,
    WebFetchToolConfigError,
    WebFetchToolResult,
    WebFetchTools,
    execute_web_fetch_action,
)


class RecordingHandler(BaseHTTPRequestHandler):
    response_status = 200
    response_reason = "OK"
    response_body = b"ok"
    response_content_type = "text/plain; charset=utf-8"
    response_headers = {}
    delay_seconds = 0.0
    request_paths = []

    def do_GET(self):
        if self.delay_seconds:
            import time

            time.sleep(self.delay_seconds)
        self.__class__.request_paths.append(self.path)
        self.send_response(self.response_status, self.response_reason)
        if self.response_content_type is not None:
            self.send_header("Content-Type", self.response_content_type)
        for name, value in self.response_headers.items():
            self.send_header(name, value)
        self.end_headers()
        try:
            self.wfile.write(self.response_body)
        except BrokenPipeError:
            pass

    def log_message(self, format, *args):
        return


@pytest.fixture
def local_http_server():
    class Handler(RecordingHandler):
        response_status = 200
        response_reason = "OK"
        response_body = b"ok"
        response_content_type = "text/plain; charset=utf-8"
        response_headers = {}
        delay_seconds = 0.0
        request_paths = []

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, Handler
    finally:
        server.shutdown()
        thread.join(timeout=2.0)
        server.server_close()


def unused_local_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def allow_rule(port, path_prefix="/"):
    return NetworkAllowRule(
        rule_id="local-test",
        scheme="http",
        host="127.0.0.1",
        port=port,
        path_prefix=path_prefix,
    )


def make_tools(port, max_response_bytes=4096, timeout_seconds=2.0, path_prefix="/"):
    return WebFetchTools(
        NetworkPolicy((allow_rule(port, path_prefix=path_prefix),)),
        WebFetchToolConfig(timeout_seconds=timeout_seconds, max_response_bytes=max_response_bytes),
    )


def test_web_fetch_tool_result_success_has_no_error_fields():
    result = WebFetchToolResult(
        ok=True,
        tool="web_fetch",
        url="https://example.com/docs",
        data={"status_code": 200},
    )

    assert result.error_kind is None
    assert result.error_message is None


def test_web_fetch_tool_result_success_rejects_error_fields():
    with pytest.raises(ValueError):
        WebFetchToolResult(
            ok=True,
            tool="web_fetch",
            url="https://example.com/docs",
            data={"status_code": 200},
            error_kind="permission_denied",
            error_message="denied",
        )


def test_web_fetch_tool_result_failure_requires_error_fields():
    with pytest.raises(ValueError):
        WebFetchToolResult(ok=False, tool="web_fetch", url="https://example.com/docs", data={})


@pytest.mark.parametrize(
    "config",
    [
        WebFetchToolConfig(timeout_seconds=0.0, max_response_bytes=100),
        WebFetchToolConfig(timeout_seconds=-1.0, max_response_bytes=100),
        WebFetchToolConfig(timeout_seconds=True, max_response_bytes=100),
        WebFetchToolConfig(timeout_seconds=1.0, max_response_bytes=0),
        WebFetchToolConfig(timeout_seconds=1.0, max_response_bytes=True),
    ],
)
def test_web_fetch_tools_rejects_invalid_config(config):
    with pytest.raises(WebFetchToolConfigError):
        WebFetchTools(NetworkPolicy(()), config)


@pytest.mark.parametrize(
    "rule",
    [
        NetworkAllowRule(rule_id="", scheme="http", host="example.com", port=None, path_prefix="/"),
        NetworkAllowRule(rule_id="bad id", scheme="http", host="example.com", port=None, path_prefix="/"),
        NetworkAllowRule(rule_id="rule", scheme="ftp", host="example.com", port=None, path_prefix="/"),
        NetworkAllowRule(rule_id="rule", scheme="http", host="", port=None, path_prefix="/"),
        NetworkAllowRule(rule_id="rule", scheme="http", host="example.com", port=0, path_prefix="/"),
        NetworkAllowRule(rule_id="rule", scheme="http", host="example.com", port=65536, path_prefix="/"),
        NetworkAllowRule(rule_id="rule", scheme="http", host="example.com", port=True, path_prefix="/"),
        NetworkAllowRule(rule_id="rule", scheme="http", host="example.com", port=None, path_prefix="docs"),
    ],
)
def test_network_policy_rejects_invalid_rules(rule):
    with pytest.raises(WebFetchToolConfigError):
        NetworkPolicy((rule,))


def test_network_policy_allows_matching_url():
    policy = NetworkPolicy((NetworkAllowRule("docs", "https", "Example.COM", None, "/docs"),))

    decision = policy.decide("https://example.com/docs/index.html?x=1")

    assert decision.decision == "allow"
    assert decision.matched_rule_id == "docs"
    assert decision.reason == "network target allowed by rule docs"


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not a url",
        "ftp://example.com/docs",
        "https:///docs",
        "https://user:pass@example.com/docs",
        "https://example.com/docs#fragment",
        "https://example.com:444/docs",
        "https://other.example.com/docs",
        "https://example.com/private",
        "http://example.com/docs",
    ],
)
def test_network_policy_denies_unmatched_or_invalid_url(url):
    policy = NetworkPolicy((NetworkAllowRule("docs", "https", "example.com", None, "/docs"),))

    decision = policy.decide(url)

    assert decision.decision == "deny"
    assert decision.matched_rule_id is None
    assert decision.reason


def test_network_policy_empty_rules_denies_all():
    decision = NetworkPolicy(()).decide("https://example.com/docs")

    assert decision.decision == "deny"
    assert decision.reason == "network target is not allowed by network policy"


def test_fetch_url_gets_allowed_local_http_response(local_http_server):
    server, handler = local_http_server
    handler.response_body = "hello".encode("utf-8")
    handler.response_content_type = "text/plain; charset=utf-8"
    tools = make_tools(server.server_port)

    result = tools.fetch_url(f"http://127.0.0.1:{server.server_port}/docs?x=1")

    assert result.ok is True
    assert result.tool == "web_fetch"
    assert result.url == f"http://127.0.0.1:{server.server_port}/docs?x=1"
    assert result.data["url"] == result.url
    assert result.data["method"] == "GET"
    assert result.data["status_code"] == 200
    assert result.data["reason"] == "OK"
    assert result.data["content_type"] == "text/plain; charset=utf-8"
    assert result.data["body"] == "hello"
    assert result.data["body_sha256"] == "sha256:" + hashlib.sha256(b"hello").hexdigest()
    assert result.data["body_size_bytes"] == 5
    assert result.data["body_truncated"] is False
    assert result.data["body_decoded_with_replacement"] is False
    assert result.data["matched_rule_id"] == "local-test"
    assert result.data["timeout_seconds"] == 2.0
    assert result.data["max_response_bytes"] == 4096
    assert handler.request_paths == ["/docs?x=1"]


@pytest.mark.parametrize("status_code", [301, 404, 500])
def test_fetch_url_treats_http_status_as_completed_response(local_http_server, status_code):
    server, handler = local_http_server
    handler.response_status = status_code
    handler.response_reason = "Status"
    handler.response_body = f"status {status_code}".encode("utf-8")
    tools = make_tools(server.server_port)

    result = tools.fetch_url(f"http://127.0.0.1:{server.server_port}/status")

    assert result.ok is True
    assert result.data["status_code"] == status_code
    assert result.data["body"] == f"status {status_code}"
    assert handler.request_paths == ["/status"]


def test_fetch_url_truncates_body_and_hashes_stored_bytes(local_http_server):
    server, handler = local_http_server
    handler.response_body = b"abcdef"
    tools = make_tools(server.server_port, max_response_bytes=4)

    result = tools.fetch_url(f"http://127.0.0.1:{server.server_port}/large")

    assert result.ok is True
    assert result.data["body"] == "abcd"
    assert result.data["body_size_bytes"] == 4
    assert result.data["body_sha256"] == "sha256:" + hashlib.sha256(b"abcd").hexdigest()
    assert result.data["body_truncated"] is True


def test_fetch_url_records_decode_replacement_for_non_utf8_body(local_http_server):
    server, handler = local_http_server
    handler.response_body = b"\xff"
    tools = make_tools(server.server_port)

    result = tools.fetch_url(f"http://127.0.0.1:{server.server_port}/binary")

    assert result.ok is True
    assert result.data["body"] == "�"
    assert result.data["body_decoded_with_replacement"] is True


def test_fetch_url_denies_unallowed_url_without_request(local_http_server):
    server, handler = local_http_server
    tools = WebFetchTools(
        NetworkPolicy((NetworkAllowRule("other", "http", "127.0.0.1", server.server_port, "/allowed"),)),
        WebFetchToolConfig(timeout_seconds=2.0, max_response_bytes=4096),
    )

    result = tools.fetch_url(f"http://127.0.0.1:{server.server_port}/denied")

    assert result.ok is False
    assert result.error_kind == "permission_denied"
    assert result.data == {}
    assert handler.request_paths == []


def test_fetch_url_ignores_environment_proxy(monkeypatch, local_http_server):
    server, handler = local_http_server
    proxy_port = unused_local_port()
    monkeypatch.setenv("http_proxy", f"http://127.0.0.1:{proxy_port}")
    monkeypatch.setenv("HTTP_PROXY", f"http://127.0.0.1:{proxy_port}")
    monkeypatch.setenv("no_proxy", "")
    monkeypatch.setenv("NO_PROXY", "")
    original_getaddrinfo = socket.getaddrinfo

    def resolve_allowed_test_to_localhost(host, port, *args, **kwargs):
        if host == "allowed.test":
            return original_getaddrinfo("127.0.0.1", port, *args, **kwargs)
        return original_getaddrinfo(host, port, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", resolve_allowed_test_to_localhost)
    tools = WebFetchTools(
        NetworkPolicy((NetworkAllowRule("dns-test", "http", "allowed.test", server.server_port, "/"),)),
        WebFetchToolConfig(timeout_seconds=2.0, max_response_bytes=4096),
    )

    result = tools.fetch_url(f"http://allowed.test:{server.server_port}/proxy-bypass")

    assert result.ok is True
    assert result.data["body"] == "ok"
    assert handler.request_paths == ["/proxy-bypass"]


@pytest.mark.parametrize("method", ["POST", "", 123])
def test_fetch_url_rejects_unsupported_method(local_http_server, method):
    server, handler = local_http_server
    tools = make_tools(server.server_port)

    result = tools.fetch_url(f"http://127.0.0.1:{server.server_port}/docs", method=method)

    assert result.ok is False
    assert result.error_kind == "invalid_input"
    assert result.data == {}
    assert handler.request_paths == []


def test_fetch_url_returns_connection_failure_for_allowed_unreachable_port():
    port = unused_local_port()
    tools = make_tools(port, timeout_seconds=0.2)

    result = tools.fetch_url(f"http://127.0.0.1:{port}/docs")

    assert result.ok is False
    assert result.error_kind == "fetch_failed"
    assert result.data == {}


def test_fetch_url_times_out(local_http_server):
    server, handler = local_http_server
    handler.delay_seconds = 0.3
    tools = make_tools(server.server_port, timeout_seconds=0.05)

    result = tools.fetch_url(f"http://127.0.0.1:{server.server_port}/slow")

    assert result.ok is False
    assert result.error_kind == "timeout"
    assert result.data == {}


def test_fetch_url_does_not_follow_redirect(local_http_server):
    server, handler = local_http_server
    handler.response_status = 301
    handler.response_reason = "Moved Permanently"
    handler.response_headers = {"Location": "/redirect-target"}
    handler.response_body = b"redirect"
    tools = make_tools(server.server_port)

    result = tools.fetch_url(f"http://127.0.0.1:{server.server_port}/redirect-source")

    assert result.ok is True
    assert result.data["status_code"] == 301
    assert result.data["body"] == "redirect"
    assert handler.request_paths == ["/redirect-source"]


def test_fetch_url_records_none_for_missing_content_type_and_empty_reason(local_http_server):
    server, handler = local_http_server
    handler.response_status = 200
    handler.response_reason = ""
    handler.response_content_type = None
    handler.response_body = b"no metadata"
    tools = make_tools(server.server_port)

    result = tools.fetch_url(f"http://127.0.0.1:{server.server_port}/metadata")

    assert result.ok is True
    assert result.data["content_type"] is None
    assert result.data["reason"] is None


def test_execute_web_fetch_action_dispatches_web_fetch(local_http_server):
    server, handler = local_http_server
    handler.response_body = b"dispatch"
    tools = make_tools(server.server_port)
    action = AgentAction(
        action_id="step-web",
        action=AgentActionType.WEB_FETCH,
        reason_summary="Fetch allowed URL.",
        input={"url": f"http://127.0.0.1:{server.server_port}/dispatch"},
    )

    result = execute_web_fetch_action(action, tools)

    assert result.ok is True
    assert result.tool == "web_fetch"
    assert result.data["body"] == "dispatch"
    assert handler.request_paths == ["/dispatch"]


def test_execute_web_fetch_action_rejects_non_web_fetch_action(local_http_server):
    server, handler = local_http_server
    tools = make_tools(server.server_port)
    action = AgentAction(
        action_id="step-read",
        action=AgentActionType.READ_FILE,
        reason_summary="Read a file.",
        input={"path": "README.md"},
    )

    result = execute_web_fetch_action(action, tools)

    assert result.ok is False
    assert result.tool == "read_file"
    assert result.url is None
    assert result.error_kind == "unsupported_action"
    assert result.data == {}
    assert handler.request_paths == []
