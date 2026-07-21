const test = require('node:test');
const assert = require('node:assert/strict');
const engine = require('../portfolio_engine.js');

test('成长资产不计入稳定现金流，分红和票息资产正常计入', () => {
  const assets = {
    growth: { name: '成长', income_type: 'capital_growth', estimated_yield: 10, estimated_return: 10 },
    dividend: { name: '红利', income_type: 'dividend', estimated_yield: 4, estimated_return: 6 },
    bond: { name: '债券', income_type: 'cash_interest', estimated_yield: 2, estimated_return: 2 }
  };
  const result = engine.calculatePortfolio({ growth: 50, dividend: 25, bond: 25 }, assets, 100, 0, 0);
  assert.equal(result.valid, true);
  assert.equal(result.assetDetails[0].expectedAnnualDiv, 0);
  assert.equal(result.expectedAnnualDividend, 15000);
});

test('权重异常返回无效状态且不归一化', () => {
  const assets = { a: { income_type: 'dividend', estimated_yield: 4 }, b: { income_type: 'capital_growth', estimated_yield: 0 } };
  const result = engine.calculatePortfolio({ a: 60, b: 30 }, assets, 100, 0, 0);
  assert.equal(result.valid, false);
  assert.equal(result.totalWeight, 90);
  assert.match(result.errors.join(' '), /必须为 100/);
});

test('负数、非有限数和单项超过100%均无效', () => {
  const assets = { a: { income_type: 'dividend' }, b: { income_type: 'dividend' }, c: { income_type: 'dividend' } };
  const result = engine.calculatePortfolio({ a: -1, b: Infinity, c: 101 }, assets, 1, 0, 0);
  assert.equal(result.valid, false);
  assert.ok(result.errors.length >= 3);
});

test('80%、120%、NaN 和 Infinity 权重无效，100%有效', () => {
  const assets = { a: { income_type: 'dividend', distribution_months: { 12: 1 } }, b: { income_type: 'capital_growth' } };
  assert.equal(engine.calculatePortfolio({ a: 80, b: 0 }, assets, 1, 0, 0).valid, false);
  assert.equal(engine.calculatePortfolio({ a: 100, b: 0 }, assets, 1, 0, 0).valid, true);
  assert.equal(engine.calculatePortfolio({ a: 120, b: 0 }, assets, 1, 0, 0).valid, false);
  assert.equal(engine.calculatePortfolio({ a: NaN, b: 100 }, assets, 1, 0, 0).valid, false);
  assert.equal(engine.calculatePortfolio({ a: Infinity, b: 100 }, assets, 1, 0, 0).valid, false);
});

test('分红月份比例异常可检测', () => {
  const result = engine.validateDistributionMonths({ income_type: 'dividend', distribution_months: { 1: 0.6, 13: 0.6 } });
  assert.equal(result.valid, false);
  assert.match(result.errors.join(' '), /无效分红月份|合计/);
});

test('估值温度计分别返回已验证的PE、PB和股息率百分位', () => {
  const history = [
    { date: '2026-07-13', index_code: '000300', pe: 13, pb: 1.3, dividend_yield: 3 },
    {
      date: '2026-07-20', index_code: '000300', pe: 14.304, pb: 1.4592, dividend_yield: 2.7396,
      pe_percentile_3y: 88.3978, pb_percentile_3y: 78.7293, dividend_yield_percentile_3y: 8.011,
      percentile_window: '3y', valuation_source: 'verified_index_fundamentals'
    }
  ];
  const result = engine.getDcaAdjustment(history, '000300', 'domestic_beta');
  assert.equal(result.pe, '14.30');
  assert.equal(result.pb, '1.46');
  assert.equal(result.pePercentile, 88.4);
  assert.equal(result.pbPercentile, 78.7);
  assert.equal(result.dividendYieldPercentile, 8);
  assert.equal(result.percentile, 88.4);
  assert.equal(result.factor, 0.6);
  assert.equal(result.asOf, '2026-07-20');
});
