const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const engine = require('../portfolio_engine.js');

const projectRoot = path.resolve(__dirname, '..');

test('无效组合UI状态不包含决策性结论或交易建议', () => {
  const state = engine.getInvalidPortfolioDecisionState(['权重合计为80%']);
  const rendered = Object.values(state).flat().join(' ');
  ['压力测试通过', '缓冲池平滑成功', '匹配良好', '建议每月支出', '新增资金买入', '测算卖出'].forEach(text => {
    assert.equal(rendered.includes(text), false, text);
  });
  assert.equal(state.decisionValue, '--');
  assert.equal(state.stressStatus, '不可判定');
});

test('现金缓冲池提供三步引导、快捷值和标准压力情景', () => {
  const html = fs.readFileSync(path.join(projectRoot, 'index.html'), 'utf8');
  const streamlit = fs.readFileSync(path.join(projectRoot, 'app.py'), 'utf8');

  assert.match(html, /按 3 步完成/);
  assert.match(html, /setBufferCoverageMonths\(9\)/);
  assert.match(html, /applyBufferScenario\('standard'\)/);
  assert.match(html, /standard: \{ drop: 20, delay: 1, pause: false \}/);
  assert.match(html, /高级参数：仅在复盘压力来源时调整/);
  assert.match(html, /查看完整诊断指标/);

  assert.match(streamlit, /### 只需 3 步/);
  assert.match(streamlit, /set_buffer_coverage_months/);
  assert.match(streamlit, /'standard': \(20, 1, False\)/);
  assert.match(streamlit, /高级参数：仅在复盘压力来源时调整/);
});

test('现金缓冲池核心结果元素在静态页面中保持唯一', () => {
  const html = fs.readFileSync(path.join(projectRoot, 'index.html'), 'utf8');
  [
    't2-coverage-months-val',
    't2-min-buffer-val',
    't2-recommended-spend-val',
    't2-min-buffer-months-val'
  ].forEach(id => {
    assert.equal((html.match(new RegExp(`id=["']${id}["']`, 'g')) || []).length, 1, id);
  });
});
