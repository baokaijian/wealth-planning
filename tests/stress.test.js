const test = require('node:test');
const assert = require('node:assert/strict');
const engine = require('../portfolio_engine.js');

test('市场回撤不再次折损现金分配', () => {
  const assets = { a: { role: 'dividend_income', income_type: 'dividend', estimated_yield: 12, distribution_months: { 1: 1 } } };
  const base = engine.runStressTest({ a: 100 }, assets, 100, 0, 0, 0, { drawdown: { dividend_income: 0 }, dividendDrop: { dividend_income: 50 } });
  const crashed = engine.runStressTest({ a: 100 }, assets, 100, 0, 0, 0, { drawdown: { dividend_income: 80 }, dividendDrop: { dividend_income: 50 } });
  assert.equal(crashed.stressDividendsHistory[0], base.stressDividendsHistory[0]);
  assert.equal(crashed.portfolioDrawdown, 80);
});

test('本金为0时回撤为有限数', () => {
  const result = engine.runStressTest({}, {}, 0, 0, 0, 0, { drawdown: {}, dividendDrop: {} });
  assert.equal(result.portfolioDrawdown, 0);
  assert.ok(Number.isFinite(result.maxNetWorthDrawdown));
});
