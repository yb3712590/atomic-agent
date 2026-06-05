from dataclasses import dataclass
import hashlib
import socket
import re
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import SplitResult, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from atomic_agent.models import AgentAction, AgentActionType


_RULE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]+$")
_ALLOWED_SCHEMES = {"http", "https"}
_DEFAULT_PORTS = {"http": 80, "https": 443}


@dataclass(frozen=True)
class NetworkAllowRule:
    rule_id: str
    scheme: str
    host: str
    port: int | None
    path_prefix: str


@dataclass(frozen=True)
class NetworkDecision:
    decision: Literal["allow", "deny"]
    reason: str
    matched_rule_id: str | None = None


@dataclass(frozen=True)
class WebFetchToolConfig:
    timeout_seconds: float
    max_response_bytes: int


@dataclass(frozen=True)
class WebFetchToolResult:
    ok: bool
    tool: str
    url: str | None
    data: dict[str, Any]
    error_kind: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if self.ok and (self.error_kind is not None or self.error_message is not None):
            raise ValueError("successful WebFetchToolResult must not include error fields")
        if not self.ok and (not self.error_kind or not self.error_message):
            raise ValueError("failed WebFetchToolResult requires error_kind and error_message")


class WebFetchToolConfigError(ValueError):
    pass


class NetworkPolicy:
    def __init__(self, rules: tuple[NetworkAllowRule, ...]):
        if not isinstance(rules, tuple):
            raise WebFetchToolConfigError("network policy rules must be a tuple")
        self.rules = tuple(self._normalize_rule(rule) for rule in rules)

    def decide(self, url: str) -> NetworkDecision:
        split_or_error = self._split_url(url)
        if isinstance(split_or_error, str):
            return NetworkDecision("deny", split_or_error)
        split = split_or_error
        scheme = split.scheme.lower()
        host = split.hostname.lower() if split.hostname is not None else ""
        try:
            port = split.port if split.port is not None else _DEFAULT_PORTS[scheme]
        except ValueError:
            return NetworkDecision("deny", "url port is invalid")
        path = split.path or "/"
        for rule in self.rules:
            rule_port = rule.port if rule.port is not None else _DEFAULT_PORTS[rule.scheme]
            if scheme == rule.scheme and host == rule.host and port == rule_port and path.startswith(rule.path_prefix):
                return NetworkDecision(
                    "allow",
                    f"network target allowed by rule {rule.rule_id}",
                    matched_rule_id=rule.rule_id,
                )
        return NetworkDecision("deny", "network target is not allowed by network policy")

    def _split_url(self, url: str) -> SplitResult | str:
        if not isinstance(url, str) or url == "":
            return "url must be a non-empty string"
        split = urlsplit(url)
        scheme = split.scheme.lower()
        if scheme not in _ALLOWED_SCHEMES:
            return "url scheme must be http or https"
        if split.hostname is None or split.hostname == "":
            return "url host is required"
        if split.username is not None or split.password is not None:
            return "url must not include userinfo"
        if split.fragment:
            return "url fragment is not allowed"
        try:
            split.port
        except ValueError:
            return "url port is invalid"
        return split

    def _normalize_rule(self, rule: NetworkAllowRule) -> NetworkAllowRule:
        if not isinstance(rule, NetworkAllowRule):
            raise WebFetchToolConfigError("network allow rule must be a NetworkAllowRule")
        if not isinstance(rule.rule_id, str) or not _RULE_ID_PATTERN.fullmatch(rule.rule_id):
            raise WebFetchToolConfigError("network rule_id must be a non-empty stable identifier")
        if not isinstance(rule.scheme, str) or rule.scheme.lower() not in _ALLOWED_SCHEMES:
            raise WebFetchToolConfigError("network rule scheme must be http or https")
        if not isinstance(rule.host, str) or rule.host == "":
            raise WebFetchToolConfigError("network rule host must be a non-empty string")
        if rule.port is not None:
            if not isinstance(rule.port, int) or isinstance(rule.port, bool) or rule.port < 1 or rule.port > 65535:
                raise WebFetchToolConfigError("network rule port must be between 1 and 65535")
        if not isinstance(rule.path_prefix, str) or not rule.path_prefix.startswith("/"):
            raise WebFetchToolConfigError("network rule path_prefix must start with /")
        return NetworkAllowRule(
            rule_id=rule.rule_id,
            scheme=rule.scheme.lower(),
            host=rule.host.lower(),
            port=rule.port,
            path_prefix=rule.path_prefix,
        )


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class WebFetchTools:
    def __init__(self, policy: NetworkPolicy, config: WebFetchToolConfig):
        if not isinstance(policy, NetworkPolicy):
            raise WebFetchToolConfigError("policy must be a NetworkPolicy")
        self.policy = policy
        self.config = config
        self._validate_config()
        self._opener = build_opener(NoRedirectHandler, ProxyHandler({}))

    def _validate_config(self) -> None:
        if not self._is_positive_number(self.config.timeout_seconds):
            raise WebFetchToolConfigError("timeout_seconds must be positive")
        if (
            not isinstance(self.config.max_response_bytes, int)
            or isinstance(self.config.max_response_bytes, bool)
            or self.config.max_response_bytes <= 0
        ):
            raise WebFetchToolConfigError("max_response_bytes must be a positive integer")

    def _is_positive_number(self, value: object) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0

    def fetch_url(self, url: str, method: str = "GET") -> WebFetchToolResult:
        if method != "GET":
            return WebFetchToolResult(
                ok=False,
                tool="web_fetch",
                url=url if isinstance(url, str) else None,
                data={},
                error_kind="invalid_input",
                error_message="web_fetch only supports method GET",
            )
        decision = self.policy.decide(url)
        if decision.decision != "allow":
            return WebFetchToolResult(
                ok=False,
                tool="web_fetch",
                url=url if isinstance(url, str) else None,
                data={},
                error_kind="permission_denied",
                error_message=decision.reason,
            )
        request = Request(url, method="GET")
        try:
            with self._opener.open(request, timeout=self.config.timeout_seconds) as response:
                return self._completed_response(url, method, response, decision)
        except HTTPError as error:
            return self._completed_response(url, method, error, decision)
        except TimeoutError as error:
            return self._failed_result(url, "timeout", str(error) or "web_fetch timed out")
        except socket.timeout as error:
            return self._failed_result(url, "timeout", str(error) or "web_fetch timed out")
        except URLError as error:
            reason = error.reason
            if isinstance(reason, TimeoutError | socket.timeout):
                return self._failed_result(url, "timeout", str(reason) or "web_fetch timed out")
            return self._failed_result(url, "fetch_failed", str(reason) or str(error))
        except OSError as error:
            return self._failed_result(url, "fetch_failed", str(error))

    def _completed_response(
        self,
        url: str,
        method: str,
        response: Any,
        decision: NetworkDecision,
    ) -> WebFetchToolResult:
        body = response.read(self.config.max_response_bytes + 1)
        body_truncated = len(body) > self.config.max_response_bytes
        stored_body = body[: self.config.max_response_bytes]
        text = stored_body.decode("utf-8", errors="replace")
        body_decoded_with_replacement = "�" in text
        reason = getattr(response, "reason", None) or None
        data = {
            "url": url,
            "method": method,
            "status_code": response.status,
            "reason": reason,
            "content_type": response.headers.get("Content-Type") or None,
            "body": text,
            "body_sha256": "sha256:" + hashlib.sha256(stored_body).hexdigest(),
            "body_size_bytes": len(stored_body),
            "body_truncated": body_truncated,
            "body_decoded_with_replacement": body_decoded_with_replacement,
            "matched_rule_id": decision.matched_rule_id,
            "timeout_seconds": self.config.timeout_seconds,
            "max_response_bytes": self.config.max_response_bytes,
        }
        return WebFetchToolResult(ok=True, tool="web_fetch", url=url, data=data)

    def _failed_result(self, url: str, error_kind: str, error_message: str) -> WebFetchToolResult:
        return WebFetchToolResult(
            ok=False,
            tool="web_fetch",
            url=url if isinstance(url, str) else None,
            data={},
            error_kind=error_kind,
            error_message=error_message,
        )


def execute_web_fetch_action(action: AgentAction, tools: WebFetchTools) -> WebFetchToolResult:
    if action.action != AgentActionType.WEB_FETCH:
        return WebFetchToolResult(
            ok=False,
            tool=action.action.value,
            url=None,
            data={},
            error_kind="unsupported_action",
            error_message="Unsupported web fetch action.",
        )
    return tools.fetch_url(url=action.input["url"], method=action.input.get("method", "GET"))
