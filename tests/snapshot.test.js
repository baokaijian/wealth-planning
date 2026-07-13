const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const engine = require('../portfolio_engine.js');

test('恶意快照字符串仅作为数据保留，不产生可执行渲染结构', () => {
  globalThis.__snapshotPwned = false;
  const malicious = { version: 2, schema: 'wealth-planning-financial-plan', exportedAt: '<img src=x onerror="globalThis.__snapshotPwned=true">', metrics: { healthScore: 80 } };
  const result = engine.validateAndMigrateSnapshot(malicious);
  assert.equal(result.valid, true);
  assert.equal(globalThis.__snapshotPwned, false);
  assert.equal(result.snapshot.exportedAt, malicious.exportedAt);
});

test('快照比较渲染不把外部字段拼入innerHTML', () => {
  const source = fs.readFileSync(require.resolve('../index.html'), 'utf8');
  const body = source.slice(source.indexOf('function renderSnapshotComparison'), source.indexOf('function setFamilyBucketUI'));
  assert.equal(body.includes('innerHTML'), false);
  assert.match(body, /textContent/);
});

test('version 1 只读迁移，未知结构返回明确错误', () => {
  const legacy = engine.validateAndMigrateSnapshot({ version: 1, exportedAt: '2026-01-01', metrics: { healthScore: 60 } });
  assert.equal(legacy.snapshot.readOnlySource, true);
  assert.equal(legacy.snapshot.version, 2);
  const invalid = engine.validateAndMigrateSnapshot({ version: 2, schema: 'bad', exportedAt: 1, metrics: { html: '<script>' } });
  assert.equal(invalid.valid, false);
  assert.ok(invalid.errors.length >= 3);
});

test('无效组合导出的决策指标均为 null', () => {
  const metrics = engine.getSnapshotDecisionMetrics({ valid: false, errors: ['权重合计为80%'] }, { safeMonthlyWithdrawWan: 1, recommendedMonthlyExpenseWan: 0.9 }, { stressBreached: false, stressMinBuffer: 10 });
  assert.deepEqual(metrics, {
    safeMonthlyWithdrawWan: null,
    recommendedMonthlyExpenseWan: null,
    stressBreached: null,
    stressMinBuffer: null,
    portfolioValid: false,
    portfolioErrors: ['权重合计为80%']
  });
});
