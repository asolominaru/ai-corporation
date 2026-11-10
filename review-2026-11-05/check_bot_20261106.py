import importlib.util,tempfile,pathlib,json,datetime
src=pathlib.Path('/Users/solominaag/КОРПОРАЦИЯ/KIMI  КОРПОРАЦИЯ/КОРПОРАЦИЯ/approval-bot/approvals.py')
spec=importlib.util.spec_from_file_location('bot',src);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
with tempfile.TemporaryDirectory() as d:
 for name,fn in [('LOG','log.jsonl'),('STATE','state.json'),('REQUESTS','requests.json')]:setattr(b,name,str(pathlib.Path(d)/fn))
 b._load_owner_id=lambda:111
 b.save_state({'offset':0,'chat_id':111})
 future=(b._utcnow()+datetime.timedelta(hours=1)).isoformat();past=(b._utcnow()-datetime.timedelta(hours=1)).isoformat()
 b.save_requests({k:{'status':'pending','options':['yes','no'],'expires_at':exp} for k,exp in [('r',future),('expired',past)]})
 updates=[]
 b.call=lambda method,**kw:updates if method=='getUpdates' else {}
 def callback(i,by,rid,action):return {'update_id':i,'callback_query':{'id':str(i),'from':{'id':by},'message':{'chat':{'id':111}},'data':rid+':'+action}}
 updates[:]=[{'update_id':1,'message':{'from':{'id':999},'chat':{'id':999}}},callback(2,999,'r','0')];b.poll()
 assert b.load_state()['chat_id']==111 and b.load_requests()['r']['status']=='pending'
 updates[:]=[callback(3,111,'r','0'),callback(4,111,'r','1'),callback(5,111,'unknown','0'),callback(6,111,'expired','0')];b.poll()
 ev=[json.loads(x) for x in pathlib.Path(b.LOG).read_text().splitlines()]
 assert len([e for e in ev if e['type']=='decision'])==1
 assert b.load_requests()['expired']['status']=='expired'
 print(json.dumps({'foreign_chat_rejected':True,'foreign_decision_rejected':True,'owner_decision_accepted_once':True,'sequential_replay_rejected':True,'unknown_request_rejected':True,'expired_request_rejected':True}))
