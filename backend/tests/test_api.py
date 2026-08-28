"""API-level tests for health, config errors, validation and SSE assembly."""


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_chat_requires_api_key(client, set_key):
    set_key(None)
    r = client.post("/api/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 500
    assert "OPENROUTER_API_KEY" in r.json()["detail"]


def test_chat_validates_empty_messages(client):
    assert client.post("/api/chat", json={"messages": []}).status_code == 422


def test_chat_streams_sources_and_tokens(client, set_key, monkeypatch):
    set_key("sk-test-key")

    async def fake_stream(messages, settings):
        yield {"type": "delta", "content": "Hello there"}
        yield {"type": "done", "finish_reason": "stop"}

    monkeypatch.setattr("app.routers.chat.stream_completion", fake_stream)

    with client.stream(
        "POST", "/api/chat",
        json={"messages": [{"role": "user", "content": "villas in dubai"}]},
    ) as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]
        body = "".join(chunk for chunk in r.iter_text())

    assert '"type": "sources"' in body
    assert "Hello there" in body
    assert '"type": "done"' in body
