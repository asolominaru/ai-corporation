#!/usr/bin/env python3
"""
Approval bot для Founder AI OS (v2, после проверки K-01/K-02).

Гарантии:
- решения принимает ТОЛЬКО владелец (OWNER_USER_ID из .env);
- адрес доставки (chat_id) регистрируется один раз с сообщения владельца
  и никогда не перезаписывается чужим сообщением;
- запрос существует, pending, не просрочен — иначе отказ;
- одно решение на запрос: pending → decided ровно один раз;
- callback сверяется с from.id, chat.id и набором кнопок запроса;
- всё пишется в append-only журнал с hash-chain (включая отказы).

Хранилище: approvals.jsonl (журнал), requests.json (реестр запросов),
state.json (offset + chat_id).
"""
import json, os, sys, time, urllib.request, urllib.parse, hashlib, datetime, uuid
import fcntl
from contextlib import contextmanager

BASE = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.join(BASE, ".env")
LOG = os.path.join(BASE, "approvals.jsonl")
STATE = os.path.join(BASE, "state.json")
REQUESTS = os.path.join(BASE, "requests.json")

DEFAULT_TTL_HOURS = 48

# Постоянная неисправность: столько подряд падений poll → exit 1,
# чтобы cron-обвязка/мониторинг видели отказ, а не «тихий» exit 0.
MAX_CONSECUTIVE_ERRORS = 3


def load_env():
    env = {}
    with open(ENV) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                env[k] = v
    return env


def _load_token():
    return load_env()["TELEGRAM_BOT_TOKEN"]


def _load_owner_id():
    raw = load_env().get("OWNER_USER_ID", "")
    if not raw:
        raise RuntimeError("OWNER_USER_ID не задан в .env — бот не может "
                           "проверять личность владельца и не запускается")
    return int(raw)


def call(method, soft=False, **params):
    payload = json.dumps(params).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{_load_token()}/{method}",
        data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.load(r)
    except Exception as e:
        if soft:
            return {"_error": str(e)}
        raise
    if not res.get("ok"):
        if soft:
            return {"_error": str(res)}
        raise RuntimeError(f"Telegram API error: {res}")
    return res["result"]


def _utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def _load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def _save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


def load_state():
    return _load_json(STATE, {"offset": 0, "chat_id": None})


def save_state(s):
    _save_json(STATE, s)


def load_requests():
    """Реестр запросов. При первом запуске восстанавливается из журнала
    (миграция v1 → v2): request_sent → pending/решённые по decision."""
    reqs = _load_json(REQUESTS, None)
    if reqs is not None:
        return reqs
    reqs = {}
    if os.path.exists(LOG):
        with open(LOG) as f:
            for line in f:
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                rid = e.get("request_id")
                if not rid:
                    continue
                if e.get("type") == "request_sent":
                    created = e.get("ts") or _utcnow().isoformat()
                    reqs[rid] = {
                        "request_id": rid,
                        "title": e.get("title"),
                        "body": e.get("body"),
                        "options": e.get("options") or [],
                        "artifact_sha256": e.get("artifact_sha256"),
                        "status": "pending",
                        "created_at": created,
                        "expires_at": _expiry_from(created, DEFAULT_TTL_HOURS),
                        "decision": None, "decided_by": None, "decided_at": None,
                    }
                elif e.get("type") == "decision" and rid in reqs:
                    reqs[rid].update({
                        "status": "decided",
                        "decision": e.get("decision"),
                        "decided_by": str(e.get("by")),
                        "decided_at": e.get("ts"),
                    })
    save_requests(reqs)
    return reqs


def save_requests(reqs):
    _save_json(REQUESTS, reqs)


@contextmanager
def locked_requests():
    """Атомарное read-modify-write реестра под fcntl.flock.

    Закрывает гонку процессов, отмеченную повторной проверкой: бот (cron)
    и orchestrator (bridge) пишут requests.json конкурентно. Тот же
    протокол реализован в services/orchestrator/app/bridge.py.
    """
    with open(REQUESTS + ".lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        reqs = load_requests()
        yield reqs
        save_requests(reqs)


def _expiry_from(created_iso, ttl_hours):
    try:
        created = datetime.datetime.fromisoformat(created_iso)
    except (ValueError, TypeError):
        created = _utcnow()
    if created.tzinfo is None:
        created = created.replace(tzinfo=datetime.timezone.utc)
    return (created + datetime.timedelta(hours=ttl_hours)).isoformat()


def log_event(event):
    event = dict(event)
    event["ts"] = _utcnow().isoformat()
    prev = ""
    if os.path.exists(LOG):
        with open(LOG) as f:
            lines = f.read().strip().splitlines()
        if lines:
            prev = json.loads(lines[-1]).get("hash", "")
    payload = json.dumps(event, sort_keys=True, ensure_ascii=False)
    event["prev_hash"] = prev
    event["hash"] = hashlib.sha256((prev + payload).encode()).hexdigest()
    with open(LOG, "a") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def send(chat_id, title, body, request_id=None, options=None,
         artifact_sha256=None, ttl_hours=DEFAULT_TTL_HOURS):
    """options — список кнопок. callback_data: <request_id>:<idx>.
    artifact_sha256 привязывает решение к конкретной версии артефакта."""
    request_id = request_id or str(uuid.uuid4())[:8]
    options = options or ["Согласовать", "Отклонить"]
    buttons = [[{"text": opt, "callback_data": f"{request_id}:{i}"}]
               for i, opt in enumerate(options)]
    buttons.append([{"text": "📄 Подробнее", "callback_data": f"{request_id}:details"}])
    text = f"🔔 *Запрос на согласование* `{request_id}`\n\n*{title}*\n\n{body}"
    res = call("sendMessage", chat_id=chat_id, text=text, parse_mode="Markdown",
               reply_markup={"inline_keyboard": buttons})
    with locked_requests() as reqs:
        now = _utcnow()
        reqs[request_id] = {
            "request_id": request_id, "title": title, "body": body,
            "options": options, "artifact_sha256": artifact_sha256,
            "status": "pending",
            "created_at": now.isoformat(),
            "expires_at": _expiry_from(now.isoformat(), ttl_hours),
            "message_chat_id": chat_id,
            "message_id": (res or {}).get("message_id"),
            "decision": None, "decided_by": None, "decided_at": None,
        }
    log_event({"type": "request_sent", "request_id": request_id,
               "title": title, "body": body, "options": options,
               "artifact_sha256": artifact_sha256})
    print(f"sent request {request_id}")
    return request_id


def _reject(cb, chat_id, rid, reason, by):
    call("answerCallbackQuery", soft=True, callback_query_id=cb["id"],
         text=f"Отклонено: {reason}", show_alert=True)
    log_event({"type": "decision_rejected", "request_id": rid,
               "reason": reason, "by": str(by)})


def deliver_outbox(state):
    """Доставка запросов, созданных orchestrator'ом (п.3): source=orchestrator,
    message_id ещё нет. Telegram-вызов — только здесь, внутри блокировки
    реестра (полл короткий, конкуренция — один cron в минуту + bridge).
    Возвращает число доставленных."""
    chat_id = state.get("chat_id")
    if not chat_id:
        return 0
    delivered = 0
    with locked_requests() as reqs:
        for rid, req in reqs.items():
            if req.get("source") != "orchestrator":
                continue
            if req.get("status") != "pending" or req.get("message_id"):
                continue
            options = req.get("options") or ["Согласовать", "Отклонить"]
            buttons = [[{"text": opt, "callback_data": f"{rid}:{i}"}]
                       for i, opt in enumerate(options)]
            buttons.append([{"text": "📄 Подробнее",
                             "callback_data": f"{rid}:details"}])
            text = (f"🔔 *Запрос на согласование* `{rid[:8]}`\n\n"
                    f"*{req.get('title') or rid}*\n\n{req.get('body') or ''}")
            res = call("sendMessage", soft=True, chat_id=chat_id, text=text,
                       parse_mode="Markdown",
                       reply_markup={"inline_keyboard": buttons})
            if res.get("_error"):
                log_event({"type": "delivery_failed", "request_id": rid,
                           "error": str(res["_error"])[:200]})
                continue  # следующий poll повторит
            req["message_chat_id"] = chat_id
            req["message_id"] = res.get("message_id")
            log_event({"type": "request_delivered", "request_id": rid,
                       "chat_id": chat_id,
                       "message_id": req["message_id"]})
            delivered += 1
    return delivered


def sweep_expired():
    """Просроченные pending → expired без ожидания клика владельца —
    bridge orchestrator'а увидит expired при sync."""
    now = _utcnow()
    expired = []
    with locked_requests() as reqs:
        for rid, req in reqs.items():
            if req.get("status") != "pending":
                continue
            exp_raw = req.get("expires_at")
            if not exp_raw:
                continue
            try:
                exp = datetime.datetime.fromisoformat(exp_raw)
            except ValueError:
                continue
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=datetime.timezone.utc)
            if now > exp:
                req["status"] = "expired"
                expired.append(rid)
    for rid in expired:
        log_event({"type": "request_expired", "request_id": rid})
    return expired


def poll():
    owner_id = _load_owner_id()
    state = load_state()
    updates = call("getUpdates", offset=state["offset"], timeout=0)

    for u in updates:
        state["offset"] = max(state["offset"], u["update_id"] + 1)

        # Регистрация адреса доставки — только сообщением владельца,
        # один раз. Чужие сообщения адрес не меняют (K-01).
        msg = u.get("message")
        if msg and msg.get("chat"):
            sender = (msg.get("from") or {}).get("id")
            if sender == owner_id and not state.get("chat_id"):
                state["chat_id"] = msg["chat"]["id"]
                log_event({"type": "chat_registered", "chat_id": state["chat_id"],
                           "by_owner": str(sender)})
                call("sendMessage", soft=True, chat_id=state["chat_id"],
                     text="✅ Канал согласований подключён. Запросы будут приходить сюда.")
            elif sender != owner_id:
                log_event({"type": "foreign_message_ignored",
                           "from_id": str(sender)})

        cb = u.get("callback_query")
        if not cb:
            continue
        data = cb.get("data", "")
        by_user = (cb.get("from") or {}).get("id")
        cb_chat = ((cb.get("message") or {}).get("chat") or {}).get("id")

        # K-01: решение принимает только владелец и только в его чате.
        if by_user != owner_id or cb_chat != state.get("chat_id"):
            _reject(cb, cb_chat, data, "не владелец канала согласований", by_user)
            continue

        call("answerCallbackQuery", soft=True, callback_query_id=cb["id"])

        if ":" not in data:
            continue
        rid, action = data.split(":", 1)

        # Чтение-решение-запись — под эксклюзивной блокировкой реестра
        # (гонка процессов закрыта flock, см. locked_requests).
        with locked_requests() as reqs:
            req = reqs.get(rid)

            # K-02: неизвестный запрос → отказ.
            if req is None:
                _reject(cb, cb_chat, rid, "неизвестный запрос", by_user)
                continue

            if action == "details":
                call("sendMessage", soft=True, chat_id=cb_chat,
                     text=f"📄 *{req.get('title') or rid}*\n\n{req.get('body') or 'нет данных'}",
                     parse_mode="Markdown")
                log_event({"type": "details_viewed", "request_id": rid,
                           "by": str(by_user)})
                continue

            # K-02: повторное решение → отказ.
            if req["status"] != "pending":
                _reject(cb, cb_chat, rid, f"запрос уже {req['status']}", by_user)
                continue

            # K-02: просроченный запрос → отказ + фиксация expiry.
            exp = datetime.datetime.fromisoformat(req["expires_at"])
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=datetime.timezone.utc)
            if _utcnow() > exp:
                req["status"] = "expired"
                _reject(cb, cb_chat, rid, "срок запроса истёк", by_user)
                continue

            # Проверка допустимого действия: индекс в пределах кнопок запроса.
            if not (action.isdigit() and int(action) < len(req["options"])):
                _reject(cb, cb_chat, rid, "неизвестное действие", by_user)
                continue

            label = req["options"][int(action)]
            # Двойной клик отсечён проверкой pending выше; запись — при выходе
            # из блока locked_requests (tmp+replace под flock).
            req.update({"status": "decided", "decision": label,
                        "decided_by": str(by_user),
                        "decided_at": _utcnow().isoformat()})
            log_event({"type": "decision", "request_id": rid, "decision": label,
                       "by": str(by_user), "title": req.get("title"),
                       "artifact_sha256": req.get("artifact_sha256")})
            call("sendMessage", soft=True, chat_id=cb_chat,
                 text=f"✍️ Решение зафиксировано: *{label}* — `{rid}`",
                 parse_mode="Markdown")
            print(f"decision {rid}: {label} by {by_user}")

    save_state(state)
    # Исходящие запросы orchestrator'а и sweep просроченных — после обработки
    # входящих, чтобы chat_id успел зарегистрироваться в этом же полле.
    deliver_outbox(state)
    sweep_expired()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "poll"
    if cmd == "poll":
        try:
            poll()
        except Exception as e:
            # Единичный сбой (сеть) не роняет cron-цикл: exit 0, повтор через
            # минуту. Но ПОСТОЯННАЯ неисправность обязана быть видимой:
            # после MAX_CONSECUTIVE_ERRORS подряд — exit 1 (п. «бот» проверки).
            state = _load_json(STATE, {"offset": 0, "chat_id": None})
            state["consecutive_errors"] = state.get("consecutive_errors", 0) + 1
            _save_json(STATE, state)
            print(f"poll error ({state['consecutive_errors']}/{MAX_CONSECUTIVE_ERRORS}): "
                  f"{type(e).__name__}: {e}", file=sys.stderr)
            sys.exit(1 if state["consecutive_errors"] >= MAX_CONSECUTIVE_ERRORS else 0)
        else:
            state = _load_json(STATE, {"offset": 0, "chat_id": None})
            if state.get("consecutive_errors"):
                state["consecutive_errors"] = 0
                _save_json(STATE, state)
    elif cmd == "send":
        # send "title" "body" ["Кнопка 1,Кнопка 2,Кнопка 3"] [artifact_sha256]
        title, body = sys.argv[2], sys.argv[3].replace("\\n", "\n")
        options = sys.argv[4].split(",") if len(sys.argv) > 4 else None
        artifact = sys.argv[5] if len(sys.argv) > 5 else None
        state = load_state()
        if not state.get("chat_id"):
            print("chat_id неизвестен: владелец должен написать боту /start",
                  file=sys.stderr)
            sys.exit(1)
        send(state["chat_id"], title, body, options=options,
             artifact_sha256=artifact)
    elif cmd == "whoami":
        print(load_state())
    elif cmd == "list":
        for rid, r in load_requests().items():
            print(f"{rid}\t{r['status']}\t{r.get('title')}")
