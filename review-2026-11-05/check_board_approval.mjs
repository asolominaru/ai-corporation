// Isolated reproduction: only temporary data; original board data is untouched.
import {mkdtempSync, cpSync, mkdirSync, writeFileSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {Board} from '../KIMI  КОРПОРАЦИЯ/КОРПОРАЦИЯ/founder-ai-os/src/board.mjs';
const repo = fileURLToPath(new URL('../KIMI  КОРПОРАЦИЯ/КОРПОРАЦИЯ/founder-ai-os/', import.meta.url));
const tmp = mkdtempSync(resolve(tmpdir(), 'kimi-board-audit-'));
let board;
try {
  for (const d of ['config','org']) cpSync(resolve(repo,d),resolve(tmp,d),{recursive:true});
  mkdirSync(resolve(tmp,'outputs'));
  board = new Board(tmp);
  board.add({id:'AUDIT-001',project:'vforume',title:'Offline audit',goal:'Verify approval integrity',inputs:['test'],expected_output:'report',criteria:'unchanged artifact',owner:'RES',human_approval:true});
  board.start('AUDIT-001');
  writeFileSync(resolve(tmp,'outputs/test.md'),'original reviewed artifact');
  const t = board.submit('AUDIT-001','outputs/test.md');
  board.review('AUDIT-001','AUD',t.hash,'accepted','reviewed original');
  writeFileSync(resolve(tmp,t.artifact),'modified after reviewer acceptance');
  const result = board.approve('AUDIT-001','offline simulated approval');
  console.log(JSON.stringify({modified_artifact_accepted:result.status==='accepted',scope:'local single-user pilot; not a remote exploit'},null,2));
} finally {board?.close();rmSync(tmp,{recursive:true,force:true});}
