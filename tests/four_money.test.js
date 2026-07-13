const test = require('node:test');
const assert = require('node:assert/strict');
const engine = require('../portfolio_engine.js');

const base = insurance => ({
  'f-fixed-expense': 1000, 'f-essential-expense': 1000, 'debt-monthly-repay': 0,
  'ast-cash': 12000, 'ast-mmf': 0, 'ast-insurance': insurance,
  'ast-ashare': 20000, 'ast-hk': 0, 'ast-overseas': 0, 'ast-others': 0,
  'ast-house': 50000, 'ast-gold': 5000, 'protect-coverage': 'strong'
});

test('商业保险保障充分度不增加资产金额，现金价值按折扣计入', () => {
  const withoutCashValue = engine.calculateFourMoneyAnalysis(base(0), 87000, 87000, 0, 0, 0.2, 12, 20);
  const withCashValue = engine.calculateFourMoneyAnalysis(base(10000), 97000, 97000, 0, 0, 0.2, 12, 20);
  const lifeA = withoutCashValue.buckets.find(item => item.key === 'life').amount;
  const lifeB = withCashValue.buckets.find(item => item.key === 'life').amount;
  assert.equal(withCashValue.protectionAdequacyMonths, 9);
  assert.equal(lifeB - lifeA, 7000);
});

test('四类钱不重复分类且合计不超过总资产', () => {
  const totalAssets = 97000;
  const result = engine.calculateFourMoneyAnalysis(base(10000), totalAssets, totalAssets, 0, 0, 0.2, 12, 20);
  const totalBuckets = result.buckets.reduce((sum, bucket) => sum + bucket.amount, 0);
  assert.ok(totalBuckets <= totalAssets);
  const spend = result.buckets.find(item => item.key === 'spend').amount;
  const life = result.buckets.find(item => item.key === 'life').amount;
  assert.ok(spend + life - result.insuranceCashValue * result.insuranceLiquidityDiscount <= 12000);
});
