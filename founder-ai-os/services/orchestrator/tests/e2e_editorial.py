"""E2E-скрипт (п.3–4 повторной проверки 06.11.2026): пилот редакции
«Сила малых групп» на заглушках + негативные сценарии.

Запускается ОТДЕЛЬНЫМ процессом (см. test_e2e_editorial.py): env и
пакет `app` оркестратора не должны конфликтовать с остальными тестами.

Цепочка: тема → источники → черновик (через model-router, единственный
путь к моделям) → независимая проверка (другая роль, другая модель —
avoid_model_id) → замечания → версия 2 → решение владельца через
Telegram-мост по точной версии артефакта → accepted материал в
content-addressed хранилище.

Негативные сценарии (п.5): «владелец отклонил», «материал изменён»,
«бюджет исчерпан», «приложение перезапущено».

Сеть и платные вызовы не используются: router поднят in-process
(ASGI transport), providers.chat подменён заглушкой.
"""
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

TMP = Path(tempfile.mkdtemp(prefix="faios-e2e-"))

os.environ["ORCHESTRATOR_DATABASE_URL"] = f"sqlite:///{TMP}/orch.db"
os.environ["ORCHESTRATOR_OWNER_IDS"] = "owner-1"
os.environ["ORCHESTRATOR_TOKENS"] = json.dumps({
    "tok-admin": {"actor": "admin-1", "role": "admin"},
    "tok-orch": {"actor": "orch-1", "role": "orchestrator"},
    "tok-owner": {"actor": "owner-1", "role": "owner"},
    "tok-writer": {"actor": "smg-writer", "role": "agent"},
    "tok-critic": {"actor": "quality-critic", "role": "agent"},
})
os.environ["APPROVAL_REGISTRY_PATH"] = str(TMP / "requests.json")
os.environ["ARTIFACT_DIR"] = str(TMP / "artifacts")

os.environ["MODEL_ROUTER_DATABASE_URL"] = f"sqlite:///{TMP}/router.db"
os.environ["MODEL_ROUTER_TOKEN"] = "tok-router-orch"
os.environ["ROUTER_TOKENS"] = json.dumps({
    "tok-router-admin": {"actor": "router-admin", "role": "admin"},
    "tok-router-orch": {"actor": "orch-1", "role": "orchestrator"},
})

# Пакет `app` оркестратора — из корня сервиса (скрипт запускают оттуда).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from fastapi.testclient import TestClient

from app.main import app as orch_app
from app.db import Base as OrchBase, engine as orch_engine
from app import bridge, modelclient

# Router — отдельный пакет с тем же именем `app`; грузим как router_app,
# чтобы его относительные импорты разрешались корректно.
ROUTER_APP_DIR = Path(__file__).resolve().parents[2] / "model-router" / "app"
spec = importlib.util.spec_from_file_location(
    "router_app", ROUTER_APP_DIR / "__init__.py",
    submodule_search_locations=[str(ROUTER_APP_DIR)])
router_pkg = importlib.util.module_from_spec(spec)
sys.modules["router_app"] = router_pkg
spec.loader.exec_module(router_pkg)
router_db = importlib.import_module("router_app.db")
router_main = importlib.import_module("router_app.main")
router_providers = importlib.import_module("router_app.providers")


def fake_chat(model, messages, max_tokens=2000):
    """Бесплатная заглушка модели. Текст зависит от промпта, поэтому
    v1 и v2 артефакта различаются, а хеши — честные."""
    prompt = messages[-1]["content"] if messages else ""
    text = (f"# Материал редакции\n\nМодель: {model.model_name}\n\n"
            f"Ответ на запрос:\n{prompt}")
    return router_providers.ChatResult(
        text=text, tokens_in=len(prompt) // 4 or 10,
        tokens_out=len(text) // 4 or 10, latency_ms=3)


router_providers.chat = fake_chat  # сеть не используется

H_ADMIN = {"Authorization": "Bearer tok-admin"}
H_ORCH = {"Authorization": "Bearer tok-orch"}
H_WRITER = {"Authorization": "Bearer tok-writer"}
H_CRITIC = {"Authorization": "Bearer tok-critic"}
HR_ADMIN = {"Authorization": "Bearer tok-router-admin"}
HR_ORCH = {"Authorization": "Bearer tok-router-orch"}

WRITER = "smg-writer"
CRITIC = "quality-critic"
REGISTRY = os.environ["APPROVAL_REGISTRY_PATH"]
ARTIFACTS = Path(os.environ["ARTIFACT_DIR"])

CHECKS = []


def check(name, cond, detail=""):
    CHECKS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'} {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        raise AssertionError(f"{name}: {detail}")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def new_task(w, **over):
    payload = {
        "tenant_id": w.tenant_id, "project_id": w.project_id,
        "department": "content",
        "goal": "Статья «Сила малых групп»: как 5 человек обгоняют отдел",
        "why": "Редакция — P1 по утверждённому порядку MVP, материал ведёт в воронку",
        "expected_output": {"type": "document",
                            "description": "Статья 1500–2500 знаков с карточкой и источниками"},
        "acceptance_criteria": [
            {"type": "human_review",
             "description": "Есть ссылки на источники и карточка материала"},
        ],
        "reviewer": CRITIC,
        "budget": {"max_usd": 0.5},
        "requires_human_approval": ["public_statement"],
    }
    payload.update(over)
    r = w.orch.post("/tasks", json=payload, headers=H_ORCH)
    assert r.status_code == 201, r.text
    task_id = r.json()["task_id"]
    assert w.orch.post(f"/tasks/{task_id}/submit", headers=H_ORCH).status_code == 200
    return task_id


def run_draft(w, task_id, prompt):
    """Ход агента: claim → вызов модели ЧЕРЕЗ router → report с артефактом."""
    r = w.orch.post(f"/tasks/{task_id}/claim", json={}, headers=H_WRITER)
    assert r.status_code == 200, r.text
    resp = modelclient.complete(
        tenant_id=w.tenant_id, task_id=task_id, task_type="writing_ux",
        messages=[{"role": "user", "content": prompt}],
        task_budget_max_usd=0.5, client=w.router)
    text = resp["text"]
    r = w.orch.post(f"/tasks/{task_id}/report", json={
        "report": {"WHAT_CHANGED": "черновик", "TEST_RESULTS": "n/a",
                   "FILES_CHANGED": [], "RISKS": "—", "KNOWN_ISSUES": "—",
                   "NEXT_STEP": "review"},
        "artifact_sha256": sha(text), "artifact_text": text,
        "cost_usd": resp["usage"]["cost_usd"],
        "tokens_in": resp["usage"]["tokens_in"],
        "tokens_out": resp["usage"]["tokens_out"]}, headers=H_WRITER)
    assert r.status_code == 200, r.text
    assert r.json()["artifact_stored"] is True
    return resp, text


def owner_decision(request_id, label):
    """Эмулирует нажатие кнопки владельцем в боте: запись решения в реестр
    под тем же flock-протоколом."""
    with bridge.locked_registry(REGISTRY) as registry:
        req = registry[request_id]
        req.update({"status": "decided", "decision": label,
                    "decided_by": "owner-1",
                    "decided_at": "2026-11-06T12:00:00+00:00"})


def scenario_pilot(w):
    task_id = new_task(w)

    # 1. Черновик v1 — вызов модели ТОЛЬКО через router.
    resp1, draft_v1 = run_draft(
        w, task_id, "Тема: Сила малых групп. Источники: 3 интервью клиентов.")
    check("черновик получен через router", resp1["model"] in ("writer-stub", "critic-stub"))
    check("расход зарезервирован и списан router'ом", resp1["task_spent_usd"] > 0)
    t = w.orch.get(f"/tasks/{task_id}", headers=H_ORCH).json()
    check("задача в review, версия v1 привязана",
          t["status"] == "review" and t["artifact_sha256"] == sha(draft_v1))

    # 2. Независимая проверка — другая роль; модель критика ≠ модели автора.
    critic_view = modelclient.complete(
        tenant_id=w.tenant_id, task_id=task_id, task_type="writing_ux",
        messages=[{"role": "user", "content": f"Проверь черновик:\n{draft_v1}"}],
        task_budget_max_usd=0.5, avoid_model_id=w.writer_model_id,
        client=w.router)
    check("проверка другой моделью (avoid_model_id)",
          critic_view["model"] == "critic-stub", critic_view["model"])
    r = w.orch.post(f"/tasks/{task_id}/review", json={
        "verdict": "request_changes",
        "findings": [{"severity": "major",
                      "issue": "Нет ссылок на источники — добавить"}]},
        headers=H_CRITIC)
    check("замечания → rework", r.json().get("status") == "rework", r.text)

    # 3. Доработка → версия 2 с новым хешем.
    _, draft_v2 = run_draft(
        w, task_id, "Тема: Сила малых групп. Источники: 3 интервью клиентов. "
                    "Добавь ссылки на источники [1][2][3].")
    check("v2 отличается от v1", sha(draft_v2) != sha(draft_v1))

    # 4. Reviewer принимает v2.
    r = w.orch.post(f"/tasks/{task_id}/review",
                    json={"verdict": "approve"}, headers=H_CRITIC)
    check("reviewer принял v2", r.json().get("status") == "approved", r.text)

    # 5. Публикация — отдельное действие по решению владельца.
    r = w.orch.post("/approvals", json={
        "tenant_id": w.tenant_id, "task_id": task_id, "type": "public_statement",
        "payload": {"artifact_sha256": sha(draft_v2)}}, headers=H_ORCH)
    check("approval создан и ушёл в Telegram-мост",
          r.status_code == 201 and r.json()["telegram_notified"] is True, r.text)
    approval_id = r.json()["approval_id"]

    with open(REGISTRY, encoding="utf-8") as f:
        entry = json.load(f)[approval_id]
    check("запрос в реестре бота: pending, привязан к v2",
          entry["source"] == "orchestrator" and entry["status"] == "pending"
          and entry["artifact_sha256"] == sha(draft_v2))
    check("доставка — зона cron-полла бота", entry["message_id"] is None)

    # 6. Владелец нажимает «Согласовать» → sync переносит решение.
    owner_decision(approval_id, "Согласовать")
    r = w.orch.post("/bridge/sync", headers=H_ORCH)
    check("решение применено",
          r.json()["applied"] == [{"approval_id": approval_id,
                                   "status": "approved", "decided_by": "owner-1"}],
          r.text)
    check("повторный sync — no-op",
          w.orch.post("/bridge/sync", headers=H_ORCH).json()["count"] == 0)

    # 7. Complete: все факты на месте (run, report, review, approval на v2).
    r = w.orch.post(f"/tasks/{task_id}/complete", json={}, headers=H_ORCH)
    check("задача completed", r.json().get("status") == "completed", r.text)

    # 8. Принятый материал сохранён: файл с именем-хешем и точным содержимым.
    stored = ARTIFACTS / sha(draft_v2)
    check("артефакт в content-addressed хранилище",
          stored.exists() and stored.read_text(encoding="utf-8") == draft_v2)

    # 9. Аудит-цепь цела; расходы видны и не превысили бюджет.
    check("аудит-цепь валидна",
          w.orch.get("/audit/verify", params={"tenant_id": w.tenant_id},
                     headers=H_ORCH).json()["chain_valid"] is True)
    usage = w.router.get("/usage", params={"tenant_id": w.tenant_id,
                                           "task_id": task_id},
                         headers=HR_ORCH).json()
    spent = sum(u["cost_usd"] for u in usage)
    check("расходы по задаче в ledger, ≤ бюджета", 0 < spent <= 0.5, str(spent))
    check("все вызовы успешны", all(u["success"] for u in usage))
    return task_id


def scenario_owner_rejection(w):
    task_id = new_task(w)
    _, draft = run_draft(w, task_id, "Тема: тестовый материал на отклонение.")
    r = w.orch.post(f"/tasks/{task_id}/review",
                    json={"verdict": "approve"}, headers=H_CRITIC)
    assert r.json()["status"] == "approved"
    r = w.orch.post("/approvals", json={
        "tenant_id": w.tenant_id, "task_id": task_id, "type": "public_statement",
        "payload": {"artifact_sha256": sha(draft)}}, headers=H_ORCH)
    approval_id = r.json()["approval_id"]

    owner_decision(approval_id, "Отклонить")
    applied = w.orch.post("/bridge/sync", headers=H_ORCH).json()["applied"]
    check("отклонение владельца применено", applied[0]["status"] == "rejected")

    r = w.orch.post(f"/tasks/{task_id}/complete", json={}, headers=H_ORCH)
    check("complete после отклонения — 409", r.status_code == 409)
    return task_id


def scenario_artifact_tamper(w):
    task_id = new_task(w)
    assert w.orch.post(f"/tasks/{task_id}/claim", json={},
                       headers=H_WRITER).status_code == 200
    r = w.orch.post(f"/tasks/{task_id}/report", json={
        "report": {"WHAT_CHANGED": "x"}, "artifact_sha256": sha("подлинный текст"),
        "artifact_text": "ПОДМЕНЁННЫЙ текст"}, headers=H_WRITER)
    check("подмена содержимого под чужим хешем — 422", r.status_code == 422)
    check("задача осталась в running",
          w.orch.get(f"/tasks/{task_id}", headers=H_ORCH).json()["status"] == "running")
    return task_id


def scenario_budget_exhaustion(w):
    task_id = new_task(w, budget={"max_usd": 0.001})
    try:
        modelclient.complete(
            tenant_id=w.tenant_id, task_id=task_id, task_type="writing_ux",
            messages=[{"role": "user", "content": "дорогой запрос"}],
            task_budget_max_usd=0.001, client=w.router)
    except modelclient.RouterError as e:
        check("платный вызов сверх бюджета — 402", e.status == 402, str(e))
    else:
        check("платный вызов сверх бюджета — 402", False, "вызов прошёл")
    return task_id


def scenario_restart(w, rejected_task_id):
    """Перезапуск: соединения сброшены, новый TestClient; состояние на диске."""
    orch_engine.dispose()
    router_db.engine.dispose()

    with TestClient(orch_app) as orch2:
        tasks = orch2.get("/tasks", params={"tenant_id": w.tenant_id},
                          headers=H_ORCH).json()
        check("после рестарта видны все задачи", len(tasks) == 4, str(len(tasks)))
        pilot = next(t for t in tasks if t["status"] == "completed")
        check("pilot-задача осталась completed", bool(pilot))

        # Мост работает после рестарта: новый approval → решение → sync.
        rejected = next(t for t in tasks if t["task_id"] == rejected_task_id)
        check("отклонённая задача сохранила статус",
              rejected["status"] == "approved")
        r = orch2.post("/approvals", json={
            "tenant_id": w.tenant_id, "task_id": rejected_task_id,
            "type": "public_statement",
            "payload": {"artifact_sha256": rejected["artifact_sha256"]}},
            headers=H_ORCH)
        check("мост публикует после рестарта",
              r.json()["telegram_notified"] is True, r.text)
        approval_id = r.json()["approval_id"]
        owner_decision(approval_id, "Согласовать")
        r = orch2.post("/bridge/sync", headers=H_ORCH)
        check("sync применяет решение после рестарта",
              r.json()["applied"][0]["status"] == "approved", r.text)

        check("аудит-цепь валидна после рестарта",
              orch2.get("/audit/verify", params={"tenant_id": w.tenant_id},
                        headers=H_ORCH).json()["chain_valid"] is True)


def main():
    OrchBase.metadata.create_all(orch_engine)
    router_db.Base.metadata.create_all(router_db.engine)
    # Router in-process: TestClient синхронно гоняет ASGI; lifespan не нужен —
    # таблицы созданы выше явно.
    router_http = TestClient(router_main.app)
    with TestClient(orch_app) as orch:
        tenant = orch.post("/tenants", json={"name": "Corp", "slug": "corp"},
                           headers=H_ADMIN).json()
        project = orch.post("/projects", json={
            "tenant_id": tenant["id"], "name": "Проявленность"},
            headers=H_ADMIN).json()
        orch.post("/agents", json={"tenant_id": tenant["id"], "role_code": "smg-writer",
                                   "name": "Писатель СМГ", "id": WRITER},
                  headers=H_ADMIN)
        orch.post("/agents", json={"tenant_id": tenant["id"], "role_code": "quality-critic",
                                   "name": "Критик", "id": CRITIC},
                  headers=H_ADMIN)
        w_model = router_http.post("/models", json={
            "provider": "openai", "model_name": "writer-stub", "tier": "mid",
            "input_price_usd": 1.0, "output_price_usd": 1.0,
            "privacy_class": "public"}, headers=HR_ADMIN)
        c_model = router_http.post("/models", json={
            "provider": "openai", "model_name": "critic-stub", "tier": "mid",
            "input_price_usd": 1.0, "output_price_usd": 1.0,
            "privacy_class": "public"}, headers=HR_ADMIN)
        assert w_model.status_code == 201 and c_model.status_code == 201, \
            (w_model.text, c_model.text)
        w = SimpleNamespace(
            orch=orch, router=router_http, tenant_id=tenant["id"],
            project_id=project["id"],
            writer_model_id=w_model.json()["id"],
            critic_model_id=c_model.json()["id"])

        print("== П.4: пилот редакции «Сила малых групп» ==")
        scenario_pilot(w)
        print("== П.5: владелец отклонил ==")
        rejected_id = scenario_owner_rejection(w)
        print("== П.5: материал изменён ==")
        scenario_artifact_tamper(w)
        print("== П.5: бюджет исчерпан ==")
        scenario_budget_exhaustion(w)
        print("== П.5: приложение перезапущено ==")
        scenario_restart(w, rejected_id)

    router_http.close()
    print(f"\n{len(CHECKS)} проверок E2E пройдено")


if __name__ == "__main__":
    main()
