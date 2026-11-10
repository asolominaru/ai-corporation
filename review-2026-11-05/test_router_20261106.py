"""Offline defect reproductions; all provider calls stubbed, no real keys/network."""
import os
os.environ['MODEL_ROUTER_DATABASE_URL']='sqlite:///:memory:'
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db import Base,get_db
from app.main import app
from app import budget,providers
from app.models import BudgetLedger

@pytest.fixture
def env():
    eng=create_engine('sqlite:///:memory:',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(eng)
    S=sessionmaker(bind=eng)
    def override():
        with S() as db: yield db
    app.dependency_overrides[get_db]=override
    with TestClient(app) as c: yield c,S
    app.dependency_overrides.clear()

def register(c,endpoint=None):
    body={'provider':'openai','model_name':'offline-review-only','tier':'mid','input_price_usd':1,'output_price_usd':1,'privacy_class':'public'}
    if endpoint: body['endpoint_config']={'base_url':endpoint}
    r=c.post('/models',json=body)
    assert r.status_code==201,r.text

def request(c):
    return c.post('/complete',json={'tenant_id':'invented-tenant','task_id':'invented-task','task_type':'writing_ux','messages':[{'role':'user','content':'offline test'}],'task_budget_max_usd':1,'est_tokens_in':100,'max_tokens_out':100})

def test_untrusted_client_defines_task_and_budget(env,monkeypatch):
    c,S=env;register(c)
    monkeypatch.setattr(providers,'chat',lambda *a:providers.ChatResult('stub',100,100,1))
    r=request(c)
    assert r.status_code==200,r.text

def test_unauthenticated_endpoint_can_receive_provider_credential(env,monkeypatch):
    c,S=env; register(c,'https://untrusted.invalid/v1')
    monkeypatch.setenv('OPENAI_API_KEY','SYNTHETIC-NOT-A-REAL-KEY')
    captured=[]
    class Response:
        status_code=200
        def json(self):return {'choices':[{'message':{'content':'stub'}}],'usage':{'prompt_tokens':100,'completion_tokens':100}}
    class OfflineClient:
        def __init__(self,*a,**k):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def post(self,url,**kwargs):captured.append((url,kwargs['headers']));return Response()
    monkeypatch.setattr(providers.httpx,'Client',OfflineClient)
    r=request(c);assert r.status_code==200,r.text
    assert captured==[('https://untrusted.invalid/v1/chat/completions',{'Authorization':'Bearer SYNTHETIC-NOT-A-REAL-KEY'})]

def test_cross_month_settlement_leaves_reserve_and_loses_spending(env,monkeypatch):
    c,S=env
    monkeypatch.setattr(budget,'_periods',lambda:[('day','2026-11-30',15),('month','2026-11',280)])
    with S() as db:
        reserve=budget.reserve(db,tenant_id='T',task_id='A',amount_usd=1);db.commit()
        monkeypatch.setattr(budget,'_periods',lambda:[('day','2026-12-01',15),('month','2026-12',280)])
        budget.commit(db,reserve,0.8);db.commit();db.expire_all()
        rows=db.execute(select(BudgetLedger)).scalars().all()
        assert len(rows)==2
        assert all(float(r.reserved_usd)==1 and float(r.spent_usd)==0 for r in rows)
        assert reserve.status=='committed'

def test_actual_cost_can_exceed_task_and_day_budget(env,monkeypatch):
    c,S=env;register(c)
    monkeypatch.setattr(providers,'chat',lambda *a:providers.ChatResult('stub',20000000,100,1))
    r=request(c);assert r.status_code==200,r.text
    assert r.json()['task_spent_usd']>20
    assert c.get('/budget/invented-tenant').json()['day']['spent_usd']>15

def test_overlapping_calls_exceed_task_cap(env,monkeypatch):
    c,S=env;register(c)
    body={'tenant_id':'T','task_id':'A','task_type':'writing_ux','messages':[],'task_budget_max_usd':0.00031,'est_tokens_in':100,'max_tokens_out':100}
    entered=[]
    def overlap(*a):
        if not entered:
            entered.append(True)
            inner=c.post('/complete',json=body)
            assert inner.status_code==200,inner.text
        return providers.ChatResult('stub',100,100,1)
    monkeypatch.setattr(providers,'chat',overlap)
    outer=c.post('/complete',json=body)
    assert outer.status_code==200,outer.text
    actual=sum(x['cost_usd'] for x in c.get('/usage',params={'tenant_id':'T','task_id':'A'}).json())
    assert actual>body['task_budget_max_usd']
