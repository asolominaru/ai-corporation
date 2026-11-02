// Тесты ядра v0: протокол задач, контракты ролей, приёмка по sha256, human approval.
import {test, before, after} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, mkdirSync, writeFileSync, cpSync, readFileSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {Board} from '../src/board.mjs';

const REPO = resolve(fileURLToPath(new URL('..', import.meta.url)));
let root, board;

const base = {
  id: 'TSK-001', project: 'vforume', title: 'Проверочная задача',
  goal: 'Проверить, что протокол задач работает end-to-end',
  inputs: ['schemas/task.schema.json'], expected_output: 'Markdown-отчёт о проверке',
  criteria: 'Отчёт существует, UTF-8, содержит вывод', owner: 'RES'
};

before(() => {
  root = mkdtempSync(resolve(tmpdir(), 'faios-'));
  for (const d of ['config', 'org', 'schemas']) cpSync(resolve(REPO, d), resolve(root, d), {recursive: true});
  mkdirSync(resolve(root, 'outputs'), {recursive: true});
  board = new Board(root);
});
after(() => { board.close(); rmSync(root, {recursive: true, force: true}); });

test('add: валидная задача создаётся, reviewer берётся из контракта роли', () => {
  const t = board.add(base);
  assert.equal(t.status, 'ready');
  assert.equal(t.reviewer, 'AUD');
});

test('add: дубликат id отклоняется', () => {
  assert.throws(() => board.add(base), /UNIQUE|constraint/i);
});

test('add: неизвестное направление отклоняется', () => {
  assert.throws(() => board.add({...base, id: 'TSK-002', project: 'nope'}), /направление/);
});

test('add: обязательные поля протокола', () => {
  assert.throws(() => board.add({...base, id: 'TSK-003', goal: ''}), /goal/);
  assert.throws(() => board.add({...base, id: 'TSK-003', inputs: []}), /inputs/);
  assert.throws(() => board.add({...base, id: 'TSK-003', criteria: ' '}), /criteria/);
});

test('add: reviewer не из контракта и совпадение с исполнителем отклоняются', () => {
  assert.throws(() => board.add({...base, id: 'TSK-004', reviewer: 'SAL'}), /контракту роли/);
  assert.throws(() => board.add({...base, id: 'TSK-004', owner: 'AUD', reviewer: 'AUD'}));
});

test('add: режим и бюджет валидируются', () => {
  assert.throws(() => board.add({...base, id: 'TSK-005', mode: 'CHAOS'}), /режим/);
  assert.throws(() => board.add({...base, id: 'TSK-005', budget_rub: -1}), /budget/);
  const ok = board.add({...base, id: 'TSK-005', mode: 'REVIEW', budget_rub: 0});
  assert.equal(ok.mode, 'REVIEW');
});

test('add: владелец не может быть исполнителем', () => {
  assert.throws(() => board.add({...base, id: 'TSK-006', owner: 'OWNER'}), /исполнителем/);
});

test('полный цикл: start → submit → review accepted', () => {
  board.start('TSK-001');
  writeFileSync(resolve(root, 'outputs/r1.md'), '# Отчёт\nПроверка пройдена.\n');
  const t = board.submit('TSK-001', 'outputs/r1.md');
  assert.equal(t.status, 'review');
  const done = board.review('TSK-001', 'AUD', t.hash, 'accepted', 'Критерии подтверждены');
  assert.equal(done.status, 'accepted'); // human_approval не задан — сразу accepted
});

test('submit: артефакт вне outputs отклоняется', () => {
  board.add({...base, id: 'TSK-010'});
  board.start('TSK-010');
  writeFileSync(resolve(root, 'evil.md'), 'x');
  assert.throws(() => board.submit('TSK-010', 'evil.md'), /outputs/);
});

test('review: устаревший хэш отклоняется (защита от решения по другой версии)', () => {
  board.add({...base, id: 'TSK-011'});
  board.start('TSK-011');
  writeFileSync(resolve(root, 'outputs/r2.md'), 'v1');
  const t = board.submit('TSK-011', 'outputs/r2.md');
  assert.throws(() => board.review('TSK-011', 'AUD', '0'.repeat(64), 'accepted', 'x'), /Устаревшее/);
  board.review('TSK-011', 'AUD', t.hash, 'changes_requested', 'Нужны правки');
  assert.equal(board.task('TSK-011').status, 'changes_requested');
});

test('review: подмена артефакта после сдачи обнаруживается', () => {
  board.add({...base, id: 'TSK-012'});
  board.start('TSK-012');
  writeFileSync(resolve(root, 'outputs/r3.md'), 'оригинал');
  const t = board.submit('TSK-012', 'outputs/r3.md');
  writeFileSync(resolve(root, t.artifact), 'подмена'); // имитация порчи копии
  assert.throws(() => board.review('TSK-012', 'AUD', t.hash, 'accepted', 'x'), /изменился/);
});

test('human_approval: accepted аудитором → pending_owner → approve владельца', () => {
  board.add({...base, id: 'TSK-013', human_approval: true});
  board.start('TSK-013');
  writeFileSync(resolve(root, 'outputs/r4.md'), 'рискованное изменение');
  const t = board.submit('TSK-013', 'outputs/r4.md');
  const after1 = board.review('TSK-013', 'AUD', t.hash, 'accepted', 'Технически корректно');
  assert.equal(after1.status, 'pending_owner');
  assert.deepEqual(board.pendingOwner().map(x => x.id), ['TSK-013']);
  assert.throws(() => board.start('TSK-013'));
  const final = board.approve('TSK-013', 'Согласовано, публикуем');
  assert.equal(final.status, 'accepted');
});

test('human_approval: reject владельца возвращает в changes_requested', () => {
  board.add({...base, id: 'TSK-014', human_approval: true});
  board.start('TSK-014');
  writeFileSync(resolve(root, 'outputs/r5.md'), 'ещё одно изменение');
  const t = board.submit('TSK-014', 'outputs/r5.md');
  board.review('TSK-014', 'AUD', t.hash, 'accepted', 'ок');
  const r = board.reject('TSK-014', 'Не сейчас, сначала страница группы');
  assert.equal(r.status, 'changes_requested');
});

test('audit: ревью своей работы невозможно; события пишутся', () => {
  const t = board.task('TSK-014');
  board.start('TSK-014'); // changes_requested → running
  writeFileSync(resolve(root, 'outputs/r6.md'), 'исправлено');
  const t2 = board.submit('TSK-014', 'outputs/r6.md');
  assert.throws(() => board.review('TSK-014', 'RES', t2.hash, 'accepted', 'сам себе'), /контракту/);
  const ev = board.events('TSK-014').map(e => e.action);
  for (const a of ['created', 'started', 'submitted', 'reviewed', 'owner_rejected'])
    assert.ok(ev.includes(a), `нет события ${a}`);
});

test('list: фильтр по направлению', () => {
  board.add({...base, id: 'TSK-020', project: 'yardniki'});
  const vf = board.list('vforume');
  assert.ok(vf.length >= 5 && vf.every(t => t.project === 'vforume'));
  assert.equal(board.list('yardniki').length, 1);
});
