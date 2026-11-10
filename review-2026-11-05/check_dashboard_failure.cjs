// Execute the actual hook with mocked React, time, and gateway. No network/model calls.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const app = path.resolve(__dirname, '../KIMI  КОРПОРАЦИЯ/КОРПОРАЦИЯ/app');
const ts = require(path.join(app, 'node_modules/typescript'));
const states = [], effects = [], intervals = [];
let clock = 0, modelCalls = 0;
const react = {
  useState(initial) {
    const i = states.length;
    states.push(typeof initial === 'function' ? initial() : initial);
    return [states[i], next => { states[i] = typeof next === 'function' ? next(states[i]) : next; }];
  },
  useRef: current => ({current}),
  useCallback: fn => fn,
  useEffect: fn => effects.push(fn),
};
const cache = {};
function load(file) {
  if (cache[file]) return cache[file].exports;
  const mod = {exports:{}}; cache[file] = mod;
  const code = ts.transpileModule(fs.readFileSync(file,'utf8'), {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
  const sandbox = {
    exports:mod.exports, module:mod,
    require(name) {
      if (name === 'react') return react;
      if (name === '@/lib/gateway') return {checkGateway:async()=>false,callAgent:async()=>{modelCalls++;return {ok:false,text:'offline simulated failure'};}};
      if (name.startsWith('@/')) return load(path.join(app,'src',name.slice(2)+'.ts'));
      throw Error('Unexpected dependency '+name);
    },
    localStorage:{getItem:()=>null,setItem:()=>{}},
    Date:{now:()=>clock},
    setInterval: fn => {intervals.push(fn);return intervals.length;},
    clearInterval:()=>{}, console,
  };
  vm.runInNewContext(code,sandbox,{filename:file});
  return mod.exports;
}
(async()=>{
  const api = load(path.join(app,'src/hooks/useCorporationSim.ts')).useCorporationSim();
  effects.forEach(fn=>fn());
  api.setMode('real');
  api.launchTask('offline failure test','marketing');
  for(let i=0;i<60;i++) {clock+=1000;intervals.forEach(fn=>fn());await Promise.resolve();await Promise.resolve();}
  const reachedApproval = states[1].some(t=>t.phase==='approval');
  api.approveTask(1);
  console.log(JSON.stringify({model_calls_all_failed:modelCalls,task_reached_approval:reachedApproval,done_after_approval:states[3].done,network_calls:0},null,2));
  if(!reachedApproval || states[3].done!==1) throw Error('Behavior changed; reassess finding');
})();
