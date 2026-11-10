"""Offline findings reproductions. Copy into the temporary service tests directory.
Uses its existing in-memory fixture, never the user's dev.db or any network API.
These tests PASS when the reviewed defect is reproduced, not when it is fixed.
"""
from test_api import client, _bootstrap, _task_payload
from app.main import app
from app.db import get_db
from app.models import AuditLog, Approval
from sqlalchemy import select
from datetime import datetime, timezone, timedelta


def test_completion_bypasses_report_reviewer_and_owner(client):
    t,p,e,r = _bootstrap(client)
    task = client.post('/tasks', json=_task_payload(t,p,r,requires_human_approval=['high_risk_deploy'])).json()['task_id']
    for status in ['queued','running','review','approved','completed']:
        res = client.post(f'/tasks/{task}/transition',json={'to':status,'actor_type':'agent','actor_id':e,'ci_passed':True})
        assert res.status_code == 200, res.text
    assert client.get(f'/tasks/{task}').json()['status']=='completed'
    # No claim, report, reviewer verdict, CI evidence or owner approval was submitted.


def test_project_and_executor_can_belong_to_another_tenant(client):
    t,p,e,r = _bootstrap(client)
    other=client.post('/tenants',json={'name':'Other','slug':'other'}).json()['id']
    res=client.post('/tasks',json=_task_payload(other,p,r))
    assert res.status_code==201,res.text
    task=res.json()['task_id']
    client.post(f'/tasks/{task}/transition',json={'to':'queued','actor_type':'agent','actor_id':e})
    assert client.post(f'/tasks/{task}/claim',json={'agent_id':e}).status_code==200


def test_negative_cost_is_accepted(client):
    t,p,e,r = _bootstrap(client)
    task=client.post('/tasks',json=_task_payload(t,p,r)).json()['task_id']
    client.post(f'/tasks/{task}/transition',json={'to':'queued','actor_type':'agent','actor_id':e})
    client.post(f'/tasks/{task}/claim',json={'agent_id':e})
    res=client.post(f'/tasks/{task}/report',json={'agent_id':e,'report':{},'cost_usd':-100,'tokens_in':-10})
    assert res.status_code==200,res.text
    assert res.json()['status']=='review'


def test_cumulative_cost_exceeds_task_budget_without_block(client):
    t,p,e,r = _bootstrap(client)
    task=client.post('/tasks',json=_task_payload(t,p,r,budget={'max_usd':0.5})).json()['task_id']
    client.post(f'/tasks/{task}/transition',json={'to':'queued','actor_type':'agent','actor_id':e})
    client.post(f'/tasks/{task}/claim',json={'agent_id':e})
    res=client.post(f'/tasks/{task}/report',json={'agent_id':e,'report':{},'cost_usd':0.4})
    assert res.json()['status']=='review'
    client.post(f'/tasks/{task}/transition',json={'to':'rework','actor_type':'agent','actor_id':r})
    assert client.post(f'/tasks/{task}/claim',json={'agent_id':e}).status_code==200
    res=client.post(f'/tasks/{task}/report',json={'agent_id':e,'report':{},'cost_usd':0.4})
    assert res.json()['status']=='review'  # Total 0.8 > 0.5.


def test_expired_approval_accepts_unverified_decider(client):
    t,*_ = _bootstrap(client)
    aid=client.post('/approvals',json={'tenant_id':t,'type':'high_risk_deploy'}).json()['approval_id']
    gen=app.dependency_overrides[get_db]()
    db=next(gen)
    try:
        db.get(Approval,aid).expires_at=datetime.now(timezone.utc)-timedelta(days=1)
        db.commit()
    finally:gen.close()
    res=client.post(f'/approvals/{aid}/decide',json={'decision':'approved','decided_by':'unverified-caller'})
    assert res.status_code==200,res.text
    assert res.json()['status']=='approved'


def test_audit_actor_and_action_can_change_without_hash_failure(client):
    t,p,e,r = _bootstrap(client)
    client.post('/tasks',json=_task_payload(t,p,r))
    gen=app.dependency_overrides[get_db]()
    db=next(gen)
    try:
        row=db.execute(select(AuditLog).where(AuditLog.tenant_id==t)).scalars().first()
        row.actor_id='changed-actor'
        row.action='changed-action'
        db.commit()
    finally:gen.close()
    assert client.get('/audit/verify',params={'tenant_id':t}).json()['chain_valid'] is True
