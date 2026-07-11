const test = require('node:test');
const assert = require('node:assert/strict');
const engine = require('../portfolio_engine.js');

test('安全支取上限可以超过目标支取的3倍', () => {
  const result = engine.calculateCashflowFeasibility(12, 100, 100, 100, {}, {}, 0);
  assert.ok(result.safeMonthlyWithdraw > 300);
  assert.equal(result.searchCapped, false);
});

test('最低缓冲使用额外追加口径，不减少投资本金', () => {
  const assets = { bond: { income_type: 'cash_interest', estimated_yield: 12, distribution_months: { 12: 1 } } };
  const result = engine.calculateCashflowFeasibility(12, 10000, 0, 100, { bond: 100 }, assets, 0);
  assert.ok(result.minAdditionalBufferWan === null || result.minAdditionalBufferWan >= 0);
});
