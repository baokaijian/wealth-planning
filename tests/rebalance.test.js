const test = require('node:test');
const assert = require('node:assert/strict');
const engine = require('../portfolio_engine.js');

test('增量资金再平衡基于投入后总额且不超额分配', () => {
  const result = engine.calculateRebalancePlan({ holdings: { a: 80, b: 20 }, targetWeights: { a: 50, b: 50 }, rebalanceBands: { a: 5, b: 5 }, newCash: 20, incrementalMode: true });
  assert.equal(result.postContributionTotal, 120);
  assert.equal(result.rows.find(row => row.code === 'b').targetValue, 60);
  assert.ok(result.allocatedCash <= 20);
  assert.equal(result.rows.find(row => row.code === 'b').buyAmount, 20);
});

test('新增资金用完后才对仍超带的高配资产提示卖出', () => {
  const result = engine.calculateRebalancePlan({ holdings: { a: 90, b: 10 }, targetWeights: { a: 50, b: 50 }, rebalanceBands: { a: 5, b: 5 }, newCash: 10, incrementalMode: true });
  assert.equal(result.unallocatedCash, 0);
  assert.ok(result.rows.find(row => row.code === 'a').sellAmount > 0);
});

test('非增量模式不分配新增资金，且保留完整预算', () => {
  const result = engine.calculateRebalancePlan({ holdings: { a: 50, b: 50 }, targetWeights: { a: 50, b: 50 }, newCash: 10, incrementalMode: false });
  assert.equal(result.valid, true);
  assert.equal(result.allocatedCash, 0);
  assert.equal(result.unallocatedCash, 10);
});

test('非法目标权重返回错误，资金用尽的低配项返回剩余缺口', () => {
  const invalid = engine.calculateRebalancePlan({ holdings: { a: 1 }, targetWeights: { a: 80 }, newCash: 0 });
  assert.equal(invalid.valid, false);
  const result = engine.calculateRebalancePlan({ holdings: { a: 90, b: 10, c: 0 }, targetWeights: { a: 34, b: 33, c: 33 }, rebalanceBands: { a: 5, b: 5, c: 5 }, newCash: 1, incrementalMode: true });
  assert.ok(result.rows.find(row => row.code === 'c').remainingBuyGap > 0);
});
