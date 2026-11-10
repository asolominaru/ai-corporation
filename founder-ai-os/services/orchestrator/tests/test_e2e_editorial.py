"""Pytest-обёртка: E2E-пилот редакции гоняется отдельным процессом —
env и пакет `app` оркестратора не должны конфликтовать с остальными
тестами (см. e2e_editorial.py)."""
import subprocess
import sys
from pathlib import Path


def test_e2e_editorial_pilot():
    script = Path(__file__).parent / "e2e_editorial.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True,
        cwd=Path(__file__).resolve().parents[1],  # корень services/orchestrator
        timeout=120)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
    assert result.returncode == 0, "E2E-пилот упал, см. вывод выше"
