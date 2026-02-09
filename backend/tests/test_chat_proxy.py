import json

import httpx

from app import models
from app.api.chat_proxy import (
    _build_upstream_paths,
    _rewrite_payload_for_upstream,
    _rewrite_query_for_upstream,
    _should_try_fallback_path,
)


class _RequestStub:
    def __init__(self, content_type: str) -> None:
        self.headers = {"content-type": content_type}


def _agent() -> models.Agent:
    return models.Agent(
        proxy_id="proxy-123",
        upstream_token="token-abc",
        upstream_base_url="https://mk-ee.fit2cloud.cn",
        url="http://localhost:5173/chat/proxy-123",
    )


def test_build_upstream_paths_with_empty_rest() -> None:
    agent = _agent()
    assert _build_upstream_paths(agent, "") == ["/chat/token-abc"]


def test_build_upstream_paths_with_rest() -> None:
    agent = _agent()
    assert _build_upstream_paths(agent, "profile/access_token=proxy-123") == [
        "/chat/profile/access_token=proxy-123",
        "/chat/token-abc/profile/access_token=proxy-123",
    ]


def test_rewrite_query_replaces_token_keys_and_proxy_id_values() -> None:
    agent = _agent()
    query = "access_token=foo&acess_token=bar&access-token=baz&id=proxy-123&x=1"
    rewritten = _rewrite_query_for_upstream(agent, query)
    assert rewritten == (
        "access_token=token-abc&acess_token=token-abc&access-token=token-abc"
        "&id=token-abc&x=1"
    )


def test_rewrite_json_payload_replaces_nested_token_keys() -> None:
    agent = _agent()
    request = _RequestStub("application/json")
    payload = json.dumps(
        {
            "access_token": "foo",
            "nested": {"acess_token": "bar", "access-token": "baz"},
            "id": "proxy-123",
            "other": "keep",
        }
    ).encode("utf-8")

    rewritten = _rewrite_payload_for_upstream(agent, request, payload)
    data = json.loads(rewritten.decode("utf-8"))

    assert data["access_token"] == "token-abc"
    assert data["nested"]["acess_token"] == "token-abc"
    assert data["nested"]["access-token"] == "token-abc"
    assert data["id"] == "token-abc"
    assert data["other"] == "keep"


def test_rewrite_form_payload_replaces_token_keys_and_proxy_id_values() -> None:
    agent = _agent()
    request = _RequestStub("application/x-www-form-urlencoded")
    payload = b"access_token=foo&acess_token=bar&access-token=baz&id=proxy-123"

    rewritten = _rewrite_payload_for_upstream(agent, request, payload)

    assert rewritten.decode("utf-8") == (
        "access_token=token-abc&acess_token=token-abc&access-token=token-abc&id=token-abc"
    )


def test_should_try_fallback_path_for_http_status() -> None:
    response = httpx.Response(404, text="not found")
    assert _should_try_fallback_path(response) is True


def test_should_try_fallback_path_for_json_code_not_success() -> None:
    response = httpx.Response(
        200,
        headers={"content-type": "application/json"},
        json={"code": 500, "message": "access_token invalid"},
    )
    assert _should_try_fallback_path(response) is True


def test_should_not_try_fallback_path_for_json_success() -> None:
    response = httpx.Response(
        200,
        headers={"content-type": "application/json"},
        json={"code": 200, "data": {}},
    )
    assert _should_try_fallback_path(response) is False

