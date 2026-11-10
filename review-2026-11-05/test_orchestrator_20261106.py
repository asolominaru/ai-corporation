"""Offline defect reproductions: passing test means defect still present."""
from test_api import client, _bootstrap, _task_payload, OWNER

def setup_task(c, artifact=None):
    t,p,e,r=_bootstrap(c)
    task=c.post('/tasks',json=_task_payload(t,p,r,requires_human_approval=['high_risk_deploy'])).json()['task_id']
    assert c.post(f'/tasks/{task}/submit').status_code==200
    assert c.post(f'/tasks/{task}/claim',json={'agent_id':e}).status_code==200
    body={'agent_id':e,'report':{},'cost_usd':0.1}
    if artifact: body['artifact_sha256']=artifact
    assert c.post(f'/tasks/{task}/report',json=body).status_code==200
    return t,task,e,r

def approve(c,t,task,payload):
    aid=c.post('/approvals',json={'tenant_id':t,'task_id':task,'type':'high_risk_deploy','payload':payload}).json()['approval_id']
    # No authentication headers/cookies; claimed owner comes from JSON only.
    assert c.post(f'/approvals/{aid}/decide',json={'decided_by':OWNER,'decision':'approved'}).status_code==200

def finish(c,task,r):
    assert c.post(f'/tasks/{task}/review',json={'reviewer_id':r,'verdict':'approve'}).status_code==200
    res=c.post(f'/tasks/{task}/complete',json={'ci_passed':True,'ci_evidence':'invented-not-a-CI-run'})
    assert res.status_code==200,res.text
    assert res.json()['status']=='completed'

def test_spoof_owner_reviewer_and_ci(client):
    t,task,e,r=setup_task(client,'ab'*32)
    approve(client,t,task,{'artifact_sha256':'ab'*32})
    finish(client,task,r)

def test_missing_artifact_hash_bypasses_version_binding(client):
    t,task,e,r=setup_task(client)
    approve(client,t,task,{})
    finish(client,task,r)

def test_rework_keeps_old_approved_hash_when_report_omits_hash(client):
    t,task,e,r=setup_task(client,'ab'*32)
    approve(client,t,task,{'artifact_sha256':'ab'*32})
    assert client.post(f'/tasks/{task}/review',json={'reviewer_id':r,'verdict':'request_changes','findings':[]}).status_code==200
    assert client.post(f'/tasks/{task}/claim',json={'agent_id':e}).status_code==200
    assert client.post(f'/tasks/{task}/report',json={'agent_id':e,'report':{'WHAT_CHANGED':'new replacement output'},'cost_usd':0.1}).status_code==200
    finish(client,task,r)
