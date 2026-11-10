import pytest

from app.statemachine import check_transition, TransitionError


def test_happy_path():
    s = check_transition("created", "queued", actor_type="orchestrator")
    s = check_transition(s, "running", actor_type="agent")
    s = check_transition(s, "review", actor_type="agent")
    s = check_transition(s, "approved", actor_type="agent")
    s = check_transition(s, "completed", actor_type="orchestrator",
                         expected_output_type="document")
    assert s.value == "completed"


def test_rework_loop():
    s = check_transition("review", "rework", actor_type="agent")
    s = check_transition(s, "running", actor_type="orchestrator")
    assert s.value == "running"


def test_blocked_then_queued():
    s = check_transition("running", "blocked", actor_type="orchestrator")
    s = check_transition(s, "queued", actor_type="orchestrator")
    assert s.value == "queued"


def test_cancel_only_human():
    with pytest.raises(TransitionError):
        check_transition("running", "cancelled", actor_type="agent")
    s = check_transition("running", "cancelled", actor_type="user")
    assert s.value == "cancelled"


def test_completed_requires_approved():
    with pytest.raises(TransitionError):
        check_transition("review", "completed", actor_type="orchestrator")


def test_completed_requires_review_step():
    with pytest.raises(TransitionError):
        check_transition("running", "completed", actor_type="orchestrator")


def test_code_requires_ci():
    with pytest.raises(TransitionError):
        check_transition("approved", "completed", actor_type="orchestrator",
                         expected_output_type="code_change", ci_passed=False)
    s = check_transition("approved", "completed", actor_type="orchestrator",
                         expected_output_type="code_change", ci_passed=True)
    assert s.value == "completed"


def test_terminal_states():
    for frm in ("completed", "cancelled"):
        with pytest.raises(TransitionError):
            check_transition(frm, "queued", actor_type="orchestrator")


def test_failed_requeue_only_human():
    with pytest.raises(TransitionError):
        check_transition("failed", "queued", actor_type="orchestrator")
    s = check_transition("failed", "queued", actor_type="user")
    assert s.value == "queued"


def test_illegal_skip():
    with pytest.raises(TransitionError):
        check_transition("created", "running", actor_type="orchestrator")
