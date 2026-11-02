// Founder AI OS — ядро v0: журнал задач по Task Protocol v1.
// Локальный однопользовательский пилот: SQLite (WAL), один writer, без npm-зависимостей.
// Границы: не автономный исполнитель, не многопользовательский сервер, не платные вызовы моделей.
import {DatabaseSync} from 'node:sqlite';
import {readFileSync, mkdirSync, writeFileSync, realpathSync} from 'node:fs';
import {resolve, relative, dirname, isAbsolute} from 'node:path';
import {createHash, randomUUID} from 'node:crypto';
import {fileURLToPath} from 'node:url';

const sha256 = b => createHash('sha256').update(b).digest('hex');
const MODES = new Set(['SOLO', 'PAIR', 'PARALLEL', 'COMPETE', 'REVIEW']);
const STATUSES = ['ready', 'running', 'review', 'pending_owner', 'accepted', 'changes_requested'];

export class Board {
  constructor(root) {
    this.root = realpathSync(root);
    const company = JSON.parse(readFileSync(resolve(this.root, 'config/company.json')));
    this.tenant = company.tenant;
    this.projects = new Set([...(company.projects ?? []), ...(company.meta_projects ?? [])].map(p => p.id));
    this.roles = new Map(JSON.parse(readFileSync(resolve(this.root, 'org/agents.json'))).roles.map(r => [r.id, r]));
    mkdirSync(resolve(this.root, 'data'), {recursive: true});
    this.db = new DatabaseSync(resolve(this.root, 'data/board.sqlite'));
    this.db.exec(`PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;
      CREATE TABLE IF NOT EXISTS tasks(
        id TEXT PRIMARY KEY, project TEXT NOT NULL, title TEXT NOT NULL,
        goal TEXT NOT NULL, why TEXT, inputs TEXT NOT NULL, expected_output TEXT NOT NULL,
        criteria TEXT NOT NULL, mode TEXT NOT NULL, model_hint TEXT, budget_rub REAL,
        deadline TEXT, owner TEXT NOT NULL, reviewer TEXT NOT NULL,
        human_approval INTEGER NOT NULL DEFAULT 0, next_action TEXT,
        status TEXT NOT NULL, artifact TEXT, hash TEXT);
      CREATE TABLE IF NOT EXISTS events(
        seq INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL,
        task TEXT NOT NULL, action TEXT NOT NULL, detail TEXT NOT NULL);`);
  }

  event(id, action, detail) {
    this.db.prepare('INSERT INTO events(at,task,action,detail) VALUES(?,?,?,?)')
      .run(new Date().toISOString(), id, action, JSON.stringify(detail));
  }

  task(id) {
    const t = this.db.prepare('SELECT * FROM tasks WHERE id=?').get(id);
    if (!t) throw Error(`Задача ${id} не найдена`);
    return t;
  }

  tx(fn) {
    this.db.exec('BEGIN IMMEDIATE');
    try { const r = fn(); this.db.exec('COMMIT'); return r; }
    catch (e) { this.db.exec('ROLLBACK'); throw e; }
  }

  validate(t) {
    if (!/^[A-Z0-9][A-Z0-9_-]{1,79}$/.test(t.id ?? '')) throw Error('id: заглавные буквы/цифры, 2–80 символов');
    if (!this.projects.has(t.project)) throw Error(`Неизвестное направление: ${t.project}`);
    const role = this.roles.get(t.owner);
    if (!role) throw Error(`Неизвестная роль исполнителя: ${t.owner}`);
    if (role.id === 'OWNER') throw Error('Владелец не бывает исполнителем задачи');
    const reviewer = t.reviewer ?? role.contract.independent_reviewer;
    if (!reviewer || !this.roles.has(reviewer)) throw Error('Не определён независимый проверяющий');
    if (reviewer !== role.contract.independent_reviewer) throw Error(`Проверяющий обязан быть ${role.contract.independent_reviewer} по контракту роли`);
    if (reviewer === t.owner) throw Error('Исполнитель и проверяющий обязаны быть разными');
    for (const f of ['title', 'goal', 'expected_output', 'criteria'])
      if (!t[f]?.trim()) throw Error(`Поле ${f} обязательно по протоколу`);
    if (!Array.isArray(t.inputs) || !t.inputs.length || t.inputs.some(i => !i?.trim()))
      throw Error('inputs: минимум один входной материал');
    const mode = t.mode ?? 'SOLO';
    if (!MODES.has(mode)) throw Error(`Недопустимый режим: ${mode}`);
    if (t.budget_rub != null && (typeof t.budget_rub !== 'number' || t.budget_rub < 0))
      throw Error('budget_rub: число ≥ 0 либо null (платные вызовы заблокированы)');
    if (t.deadline && !/^\d{4}-\d{2}-\d{2}$/.test(t.deadline)) throw Error('deadline: формат ГГГГ-ММ-ДД');
    return {reviewer, mode};
  }

  add(t) {
    const {reviewer, mode} = this.validate(t);
    return this.tx(() => {
      this.db.prepare(`INSERT INTO tasks(id,project,title,goal,why,inputs,expected_output,criteria,mode,
        model_hint,budget_rub,deadline,owner,reviewer,human_approval,next_action,status)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'ready')`)
        .run(t.id, t.project, t.title, t.goal, t.why ?? null, JSON.stringify(t.inputs),
          t.expected_output, t.criteria, mode, t.model_hint ?? null, t.budget_rub ?? null,
          t.deadline ?? null, t.owner, reviewer, t.human_approval ? 1 : 0, t.next_action ?? null);
      this.event(t.id, 'created', {project: t.project, owner: t.owner, reviewer, mode});
      return this.task(t.id);
    });
  }

  start(id) {
    return this.tx(() => {
      const t = this.task(id);
      if (!['ready', 'changes_requested'].includes(t.status)) throw Error(`Нельзя начать из статуса ${t.status}`);
      this.db.prepare("UPDATE tasks SET status='running' WHERE id=?").run(id);
      this.event(id, 'started', {owner: t.owner});
    });
  }

  submit(id, path) {
    return this.tx(() => {
      const t = this.task(id);
      if (t.status !== 'running') throw Error('Задача не в работе');
      const full = realpathSync(resolve(this.root, path)), rel = relative(this.root, full);
      if (rel.startsWith('..') || isAbsolute(rel) || !rel.startsWith('outputs/') || !rel.endsWith('.md'))
        throw Error('Артефакт: только outputs/*.md внутри репозитория');
      const bytes = readFileSync(full);
      if (!bytes.length || bytes.length > 2_000_000) throw Error('Артефакт пуст или больше 2 МБ');
      new TextDecoder('utf-8', {fatal: true}).decode(bytes);
      const hash = sha256(bytes), dest = `data/artifacts/${id}/${randomUUID()}.md`;
      mkdirSync(dirname(resolve(this.root, dest)), {recursive: true});
      writeFileSync(resolve(this.root, dest), bytes, {flag: 'wx', mode: 0o600});
      this.db.prepare("UPDATE tasks SET status='review', artifact=?, hash=? WHERE id=?").run(dest, hash, id);
      this.event(id, 'submitted', {source: rel, artifact: dest, hash});
      return this.task(id);
    });
  }

  review(id, reviewer, expectedHash, decision, note) {
    return this.tx(() => {
      const t = this.task(id);
      if (t.status !== 'review') throw Error(`Ревью невозможно из статуса ${t.status}`);
      if (t.reviewer !== reviewer || t.owner === reviewer) throw Error('Ревьюер не соответствует контракту');
      if (expectedHash !== t.hash) throw Error('Устаревшее решение: укажите sha256 просмотренной версии');
      if (!['accepted', 'changes_requested'].includes(decision) || !note?.trim())
        throw Error('Нужно решение accepted|changes_requested и обоснование');
      if (sha256(readFileSync(resolve(this.root, t.artifact))) !== t.hash)
        throw Error('Артефакт изменился после сдачи');
      const next = decision === 'accepted' && t.human_approval ? 'pending_owner' : decision;
      this.db.prepare('UPDATE tasks SET status=? WHERE id=?').run(next, id);
      this.event(id, 'reviewed', {reviewer, decision, note, hash: t.hash, next});
      return this.task(id);
    });
  }

  approve(id, note) {
    return this.tx(() => {
      const t = this.task(id);
      if (t.status !== 'pending_owner') throw Error('Задача не ожидает решения владельца');
      if (!note?.trim()) throw Error('Нужен комментарий владельца');
      this.db.prepare("UPDATE tasks SET status='accepted' WHERE id=?").run(id);
      this.event(id, 'owner_approved', {note, by: 'OWNER'});
      return this.task(id);
    });
  }

  reject(id, note) {
    return this.tx(() => {
      const t = this.task(id);
      if (t.status !== 'pending_owner') throw Error('Задача не ожидает решения владельца');
      if (!note?.trim()) throw Error('Нужен комментарий владельца');
      this.db.prepare("UPDATE tasks SET status='changes_requested' WHERE id=?").run(id);
      this.event(id, 'owner_rejected', {note, by: 'OWNER'});
      return this.task(id);
    });
  }

  list(project) {
    return project
      ? this.db.prepare('SELECT * FROM tasks WHERE project=? ORDER BY rowid').all(project)
      : this.db.prepare('SELECT * FROM tasks ORDER BY rowid').all();
  }

  pendingOwner() {
    return this.db.prepare("SELECT id,project,title,owner FROM tasks WHERE status='pending_owner' ORDER BY rowid").all();
  }

  events(id) {
    return this.db.prepare('SELECT * FROM events WHERE task=? ORDER BY seq').all(id);
  }

  close() { this.db.close(); }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const board = new Board(resolve(fileURLToPath(new URL('..', import.meta.url))));
  try {
    const [cmd, ...a] = process.argv.slice(2);
    if (cmd === 'list') console.log(JSON.stringify(board.list(a[0]), null, 2));
    else if (cmd === 'pending') console.log(JSON.stringify(board.pendingOwner(), null, 2));
    else if (cmd === 'add') console.log(board.add(JSON.parse(readFileSync(a[0], 'utf8'))));
    else if (cmd === 'start') board.start(a[0]);
    else if (cmd === 'submit') console.log(board.submit(a[0], a[1]));
    else if (cmd === 'review') board.review(a[0], a[1], a[2], a[3], a.slice(4).join(' '));
    else if (cmd === 'approve') board.approve(a[0], a.slice(1).join(' '));
    else if (cmd === 'reject') board.reject(a[0], a.slice(1).join(' '));
    else if (cmd === 'events') console.log(JSON.stringify(board.events(a[0]), null, 2));
    else throw Error('Команды: list [project] | pending | add task.json | start ID | submit ID outputs/f.md | review ID ROLE SHA256 accepted|changes_requested ПРИЧИНА | approve ID КОММЕНТАРИЙ | reject ID КОММЕНТАРИЙ | events ID');
  } catch (e) { console.error(e.message); process.exitCode = 1; }
  finally { board.close(); }
}
