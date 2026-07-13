const test = require('node:test');
const assert = require('node:assert/strict');
const engine = require('../portfolio_engine.js');

test('市场回撤不再次折损现金分配', () => {
  const assets = { a: { role: 'dividend_income', income_type: 'dividend', estimated_yield: 12, distribution_months: { 1: 1 } } };
  const base = engine.runStressTest({ a: 100 }, assets, 100, 0, 0, 0, { drawdown: { dividend_income: 0 }, cashflowDrop: { equityDividend: 50, bondCoupon: 0, moneyMarket: 0 } });
  const crashed = engine.runStressTest({ a: 100 }, assets, 100, 0, 0, 0, { drawdown: { dividend_income: 80 }, cashflowDrop: { equityDividend: 50, bondCoupon: 0, moneyMarket: 0 } });
  assert.equal(crashed.stressDividendsHistory[0], base.stressDividendsHistory[0]);
  assert.equal(crashed.portfolioDrawdown, 80);
});

test('现金流折损按资产类型分离，现金利率也影响缓冲池利息', () => {
  const assets = {
    stock: { role: 'dividend_income', income_type: 'dividend', estimated_yield: 12, distribution_months: { 1: 1 } },
    bond: { role: 'bond_duration', income_type: 'cash_interest', estimated_yield: 12, distribution_months: { 1: 1 } },
    cash: { role: 'cash', income_type: 'cash_interest', estimated_yield: 12, distribution_months: { 1: 1 } }
  };
  const result = engine.runStressTest({ stock: 34, bond: 33, cash: 33 }, assets, 100, 0, 1, 0.12, {
    drawdown: {}, cashflowDrop: { equityDividend: 100, bondCoupon: 50, moneyMarket: 25 }
  });
  assert.equal(Math.round(result.stressDividendsHistory[0]), 49500);
  assert.equal(result.interestEarnedHistory[0], 0);
  const withBuffer = engine.runStressTest({}, {}, 0, 100, 1, 0.12, { drawdown: {}, cashflowDrop: { equityDividend: 0, bondCoupon: 0, moneyMarket: 50 } });
  assert.equal(withBuffer.interestEarnedHistory[0], 0.5);
});

test('本金、缓冲和支取均为0时结果有限', () => {
  const result = engine.runStressTest({}, {}, 0, 0, 0, 0, { drawdown: {}, cashflowDrop: {} });
  assert.equal(result.portfolioDrawdown, 0);
  assert.ok(Number.isFinite(result.maxNetWorthDrawdown));
});
