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
  const source = fs.readFileSync(path.join(projectRoot, 'scripts/app_jsx.js'), 'utf8');
  const streamlit = fs.readFileSync(path.join(projectRoot, 'app.py'), 'utf8');

  assert.match(source, /只需按 3 步完成缓冲池设置/);
  assert.match(source, /setBufferCoverageMonths/);
  assert.match(source, /applyBufferScenario\('standard'\)/);
  assert.match(source, /高级参数：仅在复盘压力来源时调整/);
  assert.match(source, /查看完整诊断指标/);

  assert.match(streamlit, /### 只需 3 步/);
  assert.match(streamlit, /set_buffer_coverage_months/);
  assert.match(streamlit, /'standard': \(20, 1, False\)/);
  assert.match(streamlit, /高级参数：仅在复盘压力来源时调整/);
});

test('现金缓冲池核心结果元素在静态页面中保持唯一', () => {
  const source = fs.readFileSync(path.join(projectRoot, 'scripts/app_jsx.js'), 'utf8');
  assert.equal((source.match(/id="buffer-simulation-card"/g) || []).length, 1);
  assert.equal((source.match(/const setBufferCoverageMonths/g) || []).length, 1);
  assert.equal((source.match(/const applyBufferScenario/g) || []).length, 1);
});

test('不再提供与策略控制台重复的30秒诊断输入', () => {
  const source = fs.readFileSync(path.join(projectRoot, 'scripts/app_jsx.js'), 'utf8');
  const streamlit = fs.readFileSync(path.join(projectRoot, 'app.py'), 'utf8');

  ['30秒诊断', 'quick-diagnosis-card', 'runQuickDiagnosis', 'quick_rigid'].forEach(text => {
    assert.equal(source.includes(text), false, `app_jsx.js: ${text}`);
    assert.equal(streamlit.includes(text), false, `app.py: ${text}`);
  });
  assert.match(source, /3分钟家庭快速体检/);
  assert.match(streamlit, /配置看板与缓冲池模拟的唯一参数口径/);
});

test('估值页面分别展示PE、PB和股息率百分位', () => {
  const source = fs.readFileSync(path.join(projectRoot, 'scripts/app_jsx.js'), 'utf8');
  const adapter = fs.readFileSync(path.join(projectRoot, 'src/utils/marketDataAdapter.js'), 'utf8');
  const streamlit = fs.readFileSync(path.join(projectRoot, 'app.py'), 'utf8');

  assert.match(source, /PE分位/);
  assert.match(source, /PB分位/);
  assert.match(source, /股息率/);
  assert.match(adapter, /pePercentile/);
  assert.match(adapter, /pbPercentile/);
  assert.match(adapter, /dividendYieldPercentile/);
  assert.match(streamlit, /PE\/PB 及各自百分位/);
  assert.match(source, /valuation_history\.json/);
});

test('填写内容使用版本化浏览器本地缓存并自动恢复', () => {
  const source = fs.readFileSync(path.join(projectRoot, 'scripts/app_jsx.js'), 'utf8');
  const assembler = fs.readFileSync(path.join(projectRoot, 'scripts/assemble_index_html.py'), 'utf8');

  assert.match(assembler, /const STORAGE_KEY = 'WEALTH_PLANNING_LOCAL_STORAGE_V1'/);
  assert.match(source, /localStorage\.getItem\(STORAGE_KEY\)/);
  assert.match(source, /localStorage\.setItem\(STORAGE_KEY/);
  assert.match(source, /localStorage\.removeItem\(STORAGE_KEY\)/);
  assert.match(source, /不上传任何服务端/);
  assert.equal(source.includes("fetch(STORAGE_KEY"), false);
});
