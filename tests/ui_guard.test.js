const test = require('node:test');
const assert = require('node:assert/strict');
const engine = require('../portfolio_engine.js');

test('无效组合UI状态不包含决策性结论或交易建议', () => {
  const state = engine.getInvalidPortfolioDecisionState(['权重合计为80%']);
  const rendered = Object.values(state).flat().join(' ');
  ['压力测试通过', '缓冲池平滑成功', '匹配良好', '建议每月支出', '新增资金买入', '测算卖出'].forEach(text => {
    assert.equal(rendered.includes(text), false, text);
  });
  assert.equal(state.decisionValue, '--');
  assert.equal(state.stressStatus, '不可判定');
});
