import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent.parent  # founder-ai-os/

# Dev: SQLite. Prod: PostgreSQL 16 (+RLS), см. docs/DATABASE.md.
DATABASE_URL = os.getenv("ORCHESTRATOR_DATABASE_URL", f"sqlite:///{BASE_DIR}/dev.db")

TASK_SCHEMA_PATH = Path(
    os.getenv("TASK_SCHEMA_PATH", REPO_ROOT / "schemas" / "task.schema.json")
)

# Кто может принимать owner-решения (approve/reject, cancel, requeue).
# Список user_id через запятую. Пустой = owner-действия запрещены совсем.
OWNER_IDS = frozenset(
    x.strip() for x in os.getenv("ORCHESTRATOR_OWNER_IDS", "").split(",") if x.strip()
)

# Срок жизни approval-запроса по умолчанию (часы).
APPROVAL_TTL_HOURS = float(os.getenv("APPROVAL_TTL_HOURS", "48"))

# Путь к реестру approval-бота (requests.json). Пустой = Telegram-мост
# выключен: approval создаётся в БД, но владельцу не уходит.
APPROVAL_REGISTRY_PATH = os.getenv("APPROVAL_REGISTRY_PATH", "")

# Каталог content-addressed хранилища артефактов: файл <sha256> с содержимым,
# чей хеш совпадает с именем. Подмена содержимого невозможна без смены хеша.
ARTIFACT_DIR = Path(os.getenv("ARTIFACT_DIR", BASE_DIR / "data" / "artifacts"))
