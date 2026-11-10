#!/usr/bin/env python3
"""Офлайн-тесты approval-bot v2 (K-01/K-02). Сеть и .env не используются:
TOKEN и OWNER подменяются, call() — заглушка. Регрессии против сценариев
review-2026-11-05/check_approval_bot.py — теперь ожидаем ОТКАЗЫ."""
import ast
import importlib.util
import json
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
OWNER = 111
STRANGER = 222


def load_bot(tmp, env_text="TELEGRAM_BOT_TOKEN=fake\nOWNER_USER_ID=111\n"):
    """Загружает approvals.py в изоляции: свои STATE/LOG/REQUESTS, фиктивный env."""
    (tmp / ".env").write_text(env_text)
    spec = importlib.util.spec_from_file_location("approvals", BASE / "approvals.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.ENV = str(tmp / ".env")
    mod.STATE = str(tmp / "state.json")
    mod.LOG = str(tmp / "log.jsonl")
    mod.REQUESTS = str(tmp / "requests.json")
    return mod


def make_poll(mod, updates, owner_chat=111):
    mod.save_state({"offset": 0, "chat_id": owner_chat})
    mod.save_requests({
        "req1": {
            "request_id": "req1", "title": "T", "body": "B",
            "options": ["approve", "reject"], "artifact_sha256": None,
            "status": "pending",
            "created_at": "2026-11-05T00:00:00+00:00",
            "expires_at": "2099-01-01T00:00:00+00:00",
            "decision": None, "decided_by": None, "decided_at": None,
        }
    })
    sent = []

    def fake_call(method, soft=False, **params):
        sent.append((method, params))
        if method == "getUpdates":
            return updates
        return {"message_id": 1}

    mod.call = fake_call
    return sent


def events(mod):
    p = Path(mod.LOG)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines()]


def decisions(mod):
    return [e for e in events(mod) if e["type"] == "decision"]


def rejected(mod):
    return [e for e in events(mod) if e["type"] == "decision_rejected"]


# --- K-01: чужое сообщение не меняет адрес, чужой callback не решает --------

def test_foreign_message_does_not_reregister_chat():
    with tempfile.TemporaryDirectory() as d:
        mod = load_bot(Path(d))
        updates = [
            {"update_id": 1, "message": {"chat": {"id": STRANGER},
                                         "from": {"id": STRANGER}, "text": "/start"}},
        ]
        make_poll(mod, updates)
        mod.poll()
        assert mod.load_state()["chat_id"] == OWNER, "chat_id перезаписан чужим!"
        assert any(e["type"] == "foreign_message_ignored" for e in events(mod))


def test_foreign_callback_rejected():
    with tempfile.TemporaryDirectory() as d:
        mod = load_bot(Path(d))
        updates = [
            {"update_id": 2, "callback_query": {"id": "cb1",
                "from": {"id": STRANGER},
                "message": {"chat": {"id": STRANGER}}, "data": "req1:0"}},
        ]
        make_poll(mod, updates)
        mod.poll()
        assert decisions(mod) == [], "чужой callback записан как решение!"
        assert any(e["reason"] == "не владелец канала согласований"
                   for e in rejected(mod))


# --- K-02: одно решение, неизвестные и просроченные запросы отклоняются -----

def test_double_decision_rejected():
    with tempfile.TemporaryDirectory() as d:
        mod = load_bot(Path(d))
        updates = [
            {"update_id": 1, "callback_query": {"id": "cb1",
                "from": {"id": OWNER}, "message": {"chat": {"id": OWNER}},
                "data": "req1:0"}},
            {"update_id": 2, "callback_query": {"id": "cb2",
                "from": {"id": OWNER}, "message": {"chat": {"id": OWNER}},
                "data": "req1:1"}},
        ]
        make_poll(mod, updates)
        mod.poll()
        assert len(decisions(mod)) == 1, "приняты два решения по одному запросу!"
        assert any("уже" in e["reason"] for e in rejected(mod))


def test_unknown_request_rejected():
    with tempfile.TemporaryDirectory() as d:
        mod = load_bot(Path(d))
        updates = [
            {"update_id": 1, "callback_query": {"id": "cb1",
                "from": {"id": OWNER}, "message": {"chat": {"id": OWNER}},
                "data": "unknown:0"}},
        ]
        make_poll(mod, updates)
        mod.poll()
        assert decisions(mod) == []
        assert any(e["reason"] == "неизвестный запрос" for e in rejected(mod))


def test_expired_request_rejected():
    with tempfile.TemporaryDirectory() as d:
        mod = load_bot(Path(d))
        updates = [
            {"update_id": 1, "callback_query": {"id": "cb1",
                "from": {"id": OWNER}, "message": {"chat": {"id": OWNER}},
                "data": "req1:0"}},
        ]
        make_poll(mod, updates)
        reqs = mod.load_requests()
        reqs["req1"]["expires_at"] = "2020-01-01T00:00:00+00:00"
        mod.save_requests(reqs)
        mod.poll()
        assert decisions(mod) == []
        assert any("истёк" in e["reason"] for e in rejected(mod))
        assert mod.load_requests()["req1"]["status"] == "expired"


def test_invalid_option_rejected():
    with tempfile.TemporaryDirectory() as d:
        mod = load_bot(Path(d))
        updates = [
            {"update_id": 1, "callback_query": {"id": "cb1",
                "from": {"id": OWNER}, "message": {"chat": {"id": OWNER}},
                "data": "req1:9"}},
        ]
        make_poll(mod, updates)
        mod.poll()
        assert decisions(mod) == []
        assert any(e["reason"] == "неизвестное действие" for e in rejected(mod))


def test_owner_happy_path():
    with tempfile.TemporaryDirectory() as d:
        mod = load_bot(Path(d))
        updates = [
            {"update_id": 1, "callback_query": {"id": "cb1",
                "from": {"id": OWNER}, "message": {"chat": {"id": OWNER}},
                "data": "req1:0"}},
        ]
        make_poll(mod, updates)
        mod.poll()
        dcs = decisions(mod)
        assert len(dcs) == 1 and dcs[0]["decision"] == "approve"
        assert mod.load_requests()["req1"]["status"] == "decided"


def test_owner_registration_only_once():
    with tempfile.TemporaryDirectory() as d:
        mod = load_bot(Path(d))
        mod.save_state({"offset": 0, "chat_id": None})
        mod.save_requests({})
        updates = [
            {"update_id": 1, "message": {"chat": {"id": STRANGER},
                                         "from": {"id": STRANGER}, "text": "/start"}},
            {"update_id": 2, "message": {"chat": {"id": OWNER},
                                         "from": {"id": OWNER}, "text": "/start"}},
        ]
        mod.call = lambda m, soft=False, **p: [] if m == "getUpdates" else {}
        # getUpdates должен вернуть updates один раз
        calls = {"n": 0}

        def fake(method, soft=False, **p):
            if method == "getUpdates" and calls["n"] == 0:
                calls["n"] += 1
                return updates
            return {}

        mod.call = fake
        mod.poll()
        assert mod.load_state()["chat_id"] == OWNER


def test_no_owner_id_fails_closed():
    with tempfile.TemporaryDirectory() as d:
        mod = load_bot(Path(d), env_text="TELEGRAM_BOT_TOKEN=fake\n")
        try:
            mod.poll()
        except RuntimeError as e:
            assert "OWNER_USER_ID" in str(e)
        else:
            raise AssertionError("бот запустился без OWNER_USER_ID")


# --- Мост orchestrator → бот (п.3) -------------------------------------------

def _orch_request(rid, **over):
    req = {
        "request_id": rid, "source": "orchestrator",
        "title": "public_statement: статья", "body": "Тип: public_statement",
        "options": ["Согласовать", "Отклонить"],
        "decision_map": {"Согласовать": "approved", "Отклонить": "rejected"},
        "artifact_sha256": "ab" * 32, "status": "pending",
        "created_at": "2026-11-06T00:00:00+00:00",
        "expires_at": "2099-01-01T00:00:00+00:00",
        "message_chat_id": None, "message_id": None,
        "decision": None, "decided_by": None, "decided_at": None,
    }
    req.update(over)
    return req


def test_deliver_outbox_sends_orchestrator_request_once():
    with tempfile.TemporaryDirectory() as d:
        mod = load_bot(Path(d))
        mod.save_state({"offset": 0, "chat_id": 111})
        mod.save_requests({"orch-req-1": _orch_request("orch-req-1")})
        sent = []

        def fake(method, soft=False, **p):
            sent.append((method, p))
            return {"message_id": 555}

        mod.call = fake
        assert mod.deliver_outbox(mod.load_state()) == 1
        req = mod.load_requests()["orch-req-1"]
        assert req["message_id"] == 555 and req["message_chat_id"] == 111
        assert any(e["type"] == "request_delivered" for e in events(mod))
        # повторная доставка не шлёт дубликат
        assert mod.deliver_outbox(mod.load_state()) == 0
        assert len([m for m, _ in sent if m == "sendMessage"]) == 1


def test_deliver_outbox_ignores_local_and_decided():
    with tempfile.TemporaryDirectory() as d:
        mod = load_bot(Path(d))
        mod.save_state({"offset": 0, "chat_id": 111})
        local = _orch_request("local-1")
        local.pop("source")  # обычный запрос бота — не outbox
        mod.save_requests({
            "local-1": local,
            "orch-decided": _orch_request("orch-decided", status="decided"),
        })
        mod.call = lambda method, soft=False, **p: {"message_id": 1}
        assert mod.deliver_outbox(mod.load_state()) == 0
        assert mod.load_requests()["local-1"]["message_id"] is None


def test_deliver_outbox_waits_for_chat_registration():
    with tempfile.TemporaryDirectory() as d:
        mod = load_bot(Path(d))
        mod.save_state({"offset": 0, "chat_id": None})
        mod.save_requests({"orch-req-2": _orch_request("orch-req-2")})
        mod.call = lambda method, soft=False, **p: {"message_id": 1}
        assert mod.deliver_outbox(mod.load_state()) == 0
        assert mod.load_requests()["orch-req-2"]["message_id"] is None


def test_sweep_expired_marks_overdue_pending():
    with tempfile.TemporaryDirectory() as d:
        mod = load_bot(Path(d))
        mod.save_requests({
            "old": _orch_request("old", expires_at="2020-01-01T00:00:00+00:00"),
            "fresh": _orch_request("fresh"),
        })
        expired = mod.sweep_expired()
        reqs = mod.load_requests()
        assert expired == ["old"]
        assert reqs["old"]["status"] == "expired"
        assert reqs["fresh"]["status"] == "pending"
        assert any(e["type"] == "request_expired" for e in events(mod))


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} offline tests passed")
