import {
  calculateBoardMetrics,
  calculateBufferSimulation,
  calculateMultiGoalProjections,
  simulateEarlyRetirement,
  calculateDebtDecisionMetrics,
  calculateInsuranceGap,
  calculatePensionTaxBenefit,
  calculateRealEstateRisk,
  checkLiquiditySegregation,
  checkTripleConcentration,
  calculateBehavioralEquityCeiling,
  calculateExplainableScores,
  runCompoundStressTest
} from './calculations.js';
import { STRESS_PRESETS, HISTORICAL_REPLAYS, DISCLAIMER_TEXT } from '../constants.js';

export function generateMarkdownReport(state) {
  const {
    board = {},
    health = {},
    insurance = {},
    debt = {},
    pension = {},
    property = {},
    stress = {},
    behavior = {},
    goals = []
  } = state;

  const boardMetrics = calculateBoardMetrics(board);
  const bufferMetrics = calculateBufferSimulation(board);
  const debtMetrics = calculateDebtDecisionMetrics(debt, board.growthRate);
  const insGap = calculateInsuranceGap(health, insurance, debtMetrics.totalDebtBalance);
  const pensionBenefit = calculatePensionTaxBenefit(pension);
  const reRisk = calculateRealEstateRisk(property, health, debt);
  const liqCheck = checkLiquiditySegregation(health, board.principal);
  const concentration = checkTripleConcentration(board.assets);
  const behCheck = calculateBehavioralEquityCeiling(behavior, board.assets);
  const scores = calculateExplainableScores(state);

  // 运行4大复合压力测试情景进行横向对比
  const stdStress = runCompoundStressTest(board, STRESS_PRESETS.standard, health, 36);
  const sevStress = runCompoundStressTest(board, STRESS_PRESETS.severe, health, 36);
  const stagStress = runCompoundStressTest(board, STRESS_PRESETS.stagflation, health, 36);
  const rep2018 = HISTORICAL_REPLAYS.replay_2018;
  const repStress = runCompoundStressTest(board, {
    id: rep2018.id,
    name: rep2018.name,
    unemploymentMonths: 0,
    dividendDropRate: 1 - rep2018.dividendFactor,
    equityDrawdownRate: 0.25,
    monthlyDrawdown: rep2018.monthlyDrawdown,
    medicalExpense: 0,
    delayMonths: 0,
    inflationRate: 0
  }, health, 36);

  const currentYear = new Date().getFullYear();

  // 1. 构建高息债务警报段落
  let highDebtAlertSection = '';
  if (debtMetrics.hasHighInterestAlert) {
    highDebtAlertSection = `> [!CAUTION]
> **🚨 【高息债务警报】**：检测到家庭当前存在年化 >6.0% 的高息借贷或自报高息债务余额 ¥${Number(debt.highInterestDebtBalance || 0).toLocaleString()} 元！高息借贷利息成本极高，对家庭净资产侵蚀严重，建议将其列为最高优先级偿还事项。

---
`;
  }

  // 2. 流动性硬隔离告警
  let liqAlertSection = '';
  if (liqCheck.isViolated) {
    liqAlertSection = `> [!WARNING]
> **💧 【流动性硬隔离超限警告】**：当前可用投资本金 (¥${(board.principal * 10000).toLocaleString()} 元) 已超出可投资资金上限 (¥${Math.round(liqCheck.investableCeiling).toLocaleString()} 元)，超限 ¥${Math.round(liqCheck.excessAmount).toLocaleString()} 元！**${liqCheck.warningText}**

---
`;
  }

  // 3. 保障缺口警示
  let insAlertSection = '';
  if (insGap.shouldWarnAndDowngrade) {
    insAlertSection = `> [!CAUTION]
> **🛡️ 【先补保障再配置警告】**：家庭自评保障水平处于脆弱档位，且存在寿险或重疾重大净敞口（缺少百万医疗大额兜底）。基础抗风险兜底不足时，大额医疗或极端意外将直接击穿资产组合，**当前三桶资产配置方案结论降级为“参考值”**！

---
`;
  }

  // 构建债务对比表格
  const debtComparisonRows = debtMetrics.comparisonTable.map(row => {
    const diffSign = row.diff > 0 ? `+¥${row.diff.toLocaleString()}` : `-¥${Math.abs(row.diff).toLocaleString()}`;
    return `| ${row.years} 年期 | ¥${row.fundX.toLocaleString()} | ¥${row.fvRepay.toLocaleString()} | ¥${row.fvInvest.toLocaleString()} | ${diffSign} | **${row.advantage}** |`;
  }).join('\n');

  // 多目标资源挤占推演
  const totalPrincipalYuan = (board.principal || 80) * 10000;
  const multiGoalResult = calculateMultiGoalProjections(
    goals,
    totalPrincipalYuan,
    health.monthlySurplus || 12000,
    board.growthRate || 6.5,
    0.02
  );
  const goalItems = multiGoalResult.goalResults || [];

  const goalRows = goalItems.map((item, idx) => {
    const goal = item;
    const proj = item.projection || {};
    const statusBadge = proj.isAchieved
      ? `🟢 预计富余 ¥${Math.round(proj.diff || 0).toLocaleString()}`
      : `🔴 预计缺口 ¥${Math.round(proj.gap || 0).toLocaleString()}`;

    let leverText = '已达成，无需调控';
    if (!proj.isAchieved && proj.levers) {
      const { extraMonthly, reqRatePct, rateDiffPct, isRateSafe, loosenAmount, delayYears, delayedTargetYear } = proj.levers;
      const rateLabel = isRateSafe
        ? `提升至 ${reqRatePct}% (+${rateDiffPct}%, 稳健区间内)`
        : `提升至 ${reqRatePct}% (+${rateDiffPct}%, ⚠️超稳健上限8%)`;
      leverText = `①每月多储 ¥${extraMonthly.toLocaleString()}<br>②收益率${rateLabel}<br>③降目标至 ¥${(goal.targetAmount - loosenAmount).toLocaleString()} 或延至 ${delayedTargetYear}年 (+${delayYears}年)`;
    }

    return `| ${idx + 1} | ${goal.name} | ${goal.type} | ${goal.priority} | ${goal.targetYear}年 | ¥${Number(goal.targetAmount).toLocaleString()} | ¥${Math.round(item.allocatedPrincipal || 0).toLocaleString()} | ¥${Math.round(item.allocatedSurplus || 0).toLocaleString()} | ¥${Math.round(proj.fvTotal || 0).toLocaleString()} | ${statusBadge} | ${leverText} |`;
  }).join('\n');

  // 提前退休专项推演
  const fireGoals = goals.filter(g => g.type === '提前退休');
  let fireSection = '';
  if (fireGoals.length > 0) {
    fireSection = `### 4.2 提前退休全生命周期持久性检验 (至 85 岁)\n\n`;
    fireGoals.forEach(fg => {
      const foundItem = goalItems.find(p => p.id === fg.id) || {};
      const fvCapital = foundItem.projection?.fvTotal || fg.targetAmount;

      const retConfig = fg.retireConfig || { currentAge: 35, retireAge: 50, retireMonthlyExpense: 12000 };
      const retSim = simulateEarlyRetirement({
        currentAge: retConfig.currentAge,
        retireAge: retConfig.retireAge,
        targetAmount: fg.targetAmount,
        projectedCapitalAtRetire: fvCapital,
        monthlyExpense: retConfig.retireMonthlyExpense,
        dividendYield: boardMetrics.blendedYield,
        bufferInterestRate: board.moneyMarketRate,
        endAge: 85
      });

      fireSection += `**目标名称**：${fg.name}（计划 ${fg.targetYear} 年 / ${retConfig.retireAge} 岁退休）\n`;
      fireSection += `- **退休期初总本金推演终值**：¥${Math.round(fvCapital).toLocaleString()}\n`;
      fireSection += `- **退休后月度生活费设定**：¥${Number(retConfig.retireMonthlyExpense).toLocaleString()} / 月\n`;
      fireSection += `- **85 岁持久性评级**：${retSim.isSustainable ? '✅ **资本永续安全**（未耗尽本金）' : '⚠️ **存在耗尽风险**'}\n`;
      if (retSim.isSustainable) {
        fireSection += `- **85 岁预计剩余资产**：¥${Math.round(retSim.finalCapital).toLocaleString()}\n`;
      } else {
        fireSection += `- **预计资金耗尽时点**：${retSim.depletionAge} 岁（退休后第 ${retSim.depletionMonth} 个月）\n`;
      }
      fireSection += `- **最脆弱月份（资金低谷期）**：退休后第 ${retSim.mostFragileMonth} 个月（约 ${retSim.mostFragileAge} 岁），低谷水位：¥${Math.round(retSim.lowestCapital).toLocaleString()}\n\n`;
    });
  }

  return `# 📋 家庭财富规划与量化风险综合体检报告

**生成时间**：${new Date().toLocaleDateString('zh-CN')}  
**推演工具**：纯前端静态本地家庭财务规划与量化风险系统 (数据全部保存在本地浏览器 localStorage)

---

${highDebtAlertSection}${liqAlertSection}${insAlertSection}## 一、 家庭收支、流动性硬隔离与资产体检

### 1.1 收支与短期资金布局
- **家庭月收入**：¥${Number(health.monthlyIncome || 0).toLocaleString()} 元
- **月支出（常规总额）**：¥${Number(health.monthlyExpense || 0).toLocaleString()} 元
- **月必要支出底线**：¥${Number(health.essentialMonthlyExpense || 12000).toLocaleString()} 元（用于责任缺口法生活费基准）
- **月可结余**：**¥${Number(health.monthlySurplus || 0).toLocaleString()} 元**
- **收入结构多元度**：${health.incomeSourceCount === 'dual' ? '双薪家庭' : (health.incomeSourceCount === 'single' ? '单薪主干' : '多元收入')}，预期失业恢复期：${health.unemploymentRecoveryMonths || 6} 个月

### 1.2 流动性硬隔离检查
- **流动金融资产总额**：¥${liqCheck.liquidFinancialAssets.toLocaleString()} 元
- **未来 12 个月确定性支出 (100% 隔离)**：¥${liqCheck.bucket1y.toLocaleString()} 元
- **未来 1-3 年确定性支出 (50% 折减隔离)**：¥${(liqCheck.bucket1To3y * liqCheck.discountFactor).toLocaleString()} 元
- **可投资资金上限**：**¥${Math.round(liqCheck.investableCeiling).toLocaleString()} 元**
- **当前实际可用本金**：¥${liqCheck.boardPrincipalYuan.toLocaleString()} 元（${liqCheck.isViolated ? '⚠️ **已超限**' : '✅ **在安全限额内**'}）
- **短期支出覆盖倍数**：**${liqCheck.coverageRatio} 倍**（${liqCheck.isCoverageInsufficient ? '⚠️ 低于 1.5 倍安全底线，应急流动性不足' : '✅ 流动性储备充裕'}）
- *架构口径说明：${liqCheck.distinctionNote}*

### 1.3 房产集中度与全口径 vs 剔除房产双视角资产负债表
| 财务指标 | 全口径视角 (含房产) | 剔除房产口径 (纯金融投资) | 房产下跌 ${reRisk.stressDropPct}% 冲击情景 |
| :--- | :--- | :--- | :--- |
| **总资产** | ¥${Math.round(reRisk.totalAssets).toLocaleString()} 元 | ¥${Math.round(reRisk.financialAssets).toLocaleString()} 元 | ¥${Math.round(reRisk.stressTotalAssets).toLocaleString()} 元 |
| **总负债** | ¥${Math.round(reRisk.totalDebt).toLocaleString()} 元 | ¥${Math.round(reRisk.financialDebt).toLocaleString()} 元 (不含房贷) | ¥${Math.round(reRisk.totalDebt).toLocaleString()} 元 |
| **净资产** | **¥${Math.round(reRisk.totalNetWorth).toLocaleString()} 元** | **¥${Math.round(reRisk.financialNetWorth).toLocaleString()} 元** | **¥${Math.round(reRisk.stressTotalNetWorth).toLocaleString()} 元** |
| **资产负债率** | **${reRisk.normalDebtToAsset}%** | **${reRisk.financialDebtRatio}%** | **${reRisk.stressDebtToAsset}%** |
| **房产占比** | **${reRisk.realEstateRatio}%** (${reRisk.tier === 'green' ? '🟢 健康' : (reRisk.tier === 'yellow' ? '🟡 偏高' : '🔴 高危')}) | -- | 净资产缩水 ¥${Math.round(reRisk.stressDropAmount).toLocaleString()} 元 |

- **房产集中度分析提示**：${reRisk.tierAdvice}
- **首付储备核验**：${reRisk.hasHousePlan ? (reRisk.isDownPaymentShort ? `⚠️ 计划购房首付 ¥${reRisk.expectedDownPayment.toLocaleString()} 元，确定资金存在 ¥${reRisk.downPaymentGap.toLocaleString()} 元缺口！**${reRisk.downPaymentWarning}**` : '✅ 购房首付资金已足额预留') : '无近期买房/换房计划'}

---

## 二、 家庭保障缺口测算 (责任缺口法)

- **寿险保障测算**：
  - 责任总需求：¥${Math.round(insGap.lifeTarget).toLocaleString()} 元（全部负债 ¥${debtMetrics.totalDebtBalance.toLocaleString()} + 10年生活底线 ¥${(health.essentialMonthlyExpense*120).toLocaleString()} + 教育金 ¥${insGap.childEduTarget || 500000} - 高流动性现金储备 ¥${insGap.liquidCashDeduction.toLocaleString()}）
  - 已有保额：¥${insGap.existingLife.toLocaleString()} 元
  - **寿险净缺口**：**¥${insGap.lifeGap.toLocaleString()} 元**（折合家庭年收入 **${insGap.lifeGapIncomeMultiple} 倍**）
- **重疾保障测算**（按行业稳定度【${insGap.stabConfig.label}】联动）：
  - 建议保额：¥${Math.round(insGap.critTarget).toLocaleString()} 元（${insGap.stabConfig.years}年收入 + ¥${insGap.stabConfig.medical.toLocaleString()} 治疗康复金）
  - 已有保额：¥${insGap.existingCrit.toLocaleString()} 元
  - **重疾净缺口**：**¥${insGap.critGap.toLocaleString()} 元**（折合家庭年收入 **${insGap.critGapIncomeMultiple} 倍**）
- **意外险建议额**：建议保额 ¥${insGap.accidentTarget.toLocaleString()} 元（寿险缺口 50%），已有 ¥${insGap.existingAccident.toLocaleString()} 元，净缺口 **¥${insGap.accidentGap.toLocaleString()} 元**。
- **百万医疗兜底检查**：${insGap.hasMillionMedical ? '✅ 已配置百万医疗险（大额自费医疗风险已兜底）' : '⚠️ **未配置百万医疗险**（大额住院费用可能击穿家庭储蓄防线）'}

---

## 三、 债务决策对照与个人养老金税优

### 3.1 债务决策对照矩阵
- **综合负债总额**：¥${debtMetrics.totalDebtBalance.toLocaleString()} 元（月供支出：¥${Number(debt.monthlyDebtPayment || 0).toLocaleString()} 元，剩余 ${debtMetrics.remainingYears} 年）
- **综合贷款测算利率**：**${debtMetrics.effectiveDebtRate}%**（${debtMetrics.sourceBadge}）
- **组合保守预期收益率**：**${debtMetrics.conservativeYield}%**（取增长预期收益率 ${debtMetrics.growthRate}% 的 70% 作为保守基准）
- **利差对比 (保守收益率 − 贷款利率)**：**${debtMetrics.spread >= 0 ? '+' : ''}${debtMetrics.spread.toFixed(2)}%**（${debtMetrics.spreadLabel}）
- **决策矩阵研判结论**：**${debtMetrics.decisionText}**
- *注：本测算为简化复利终值对照模型，未计入等额本息提前还款本金折减与实际税费摩擦。*

#### 路径模拟对比（模拟可用资金 X = ¥${debtMetrics.fundX.toLocaleString()} 元）
| 模拟周期 | 模拟资金本金 | 路径A: 提前还贷终值效应 | 路径B: 坚持投资推演终值 | 净资产差额 (A - B) | 策略对比建议 |
| :--- | :--- | :--- | :--- | :--- | :--- |
${debtComparisonRows}

### 3.2 个人养老金税优检查
- **开户状态**：${pensionBenefit.hasAccount ? '已开立个人养老金资金账户' : '尚未开户'}
- **本年已缴存**：¥${pensionBenefit.deposited.toLocaleString()} 元 / 每年限额 ¥12,000 元（剩余额度：¥${pensionBenefit.remainingQuota.toLocaleString()} 元）
- **边际个税档位**：${(pensionBenefit.taxRate * 100).toFixed(0)}%
- **放弃的当期税收抵扣额**：**¥${pensionBenefit.annualTaxSavingsForegone.toLocaleString()} 元 / 年**（20 年累计预计放弃 ¥${pensionBenefit.cumulative20ySavings.toLocaleString()} 元）
- *标的指引建议：${pensionBenefit.guidanceText}*

---

## 四、 资产配置、行为约束与三重集中度

### 4.1 看板核心指标
- **总可用本金**：¥${(board.principal * 10000).toLocaleString()} 元（含缓冲池种子金 ¥${(board.bufferSeed * 10000).toLocaleString()} 元）
- **配置结构**：安全防御桶 30% / 长期成长桶 55% / 综合对冲桶 15%
- **加权税后现金流收益率**：**${boardMetrics.blendedYield.toFixed(2)}%**
- **长期增长预期年化收益率**：**${boardMetrics.growthRate.toFixed(2)}%**
- **预期年税后分红总额**：¥${Math.round(boardMetrics.expectedAnnualDividend).toLocaleString()} 元（折合月均 ¥${Math.round(boardMetrics.expectedMonthlyAvg).toLocaleString()} 元）

### 4.2 行为约束引擎硬限额
- **您的行为约束权益上限**：**${behCheck.finalCeiling}%**（严格按 category==='Equity' 统计）
- **当前实际配置权益比例**：**${behCheck.actualEquityWeight.toFixed(1)}%**（${behCheck.isExceeded ? `⚠️ 超限 ${behCheck.excessWeight.toFixed(1)}%！${behCheck.warningText}` : '✅ 符合心理与财务耐受底线'}）
- **隐含极端权益回撤承受力**：约 ${behCheck.implicitDrawdown}%

### 4.3 三重集中度诊断
- **标的集中度**：单一最大标的【${concentration.maxSingle.name}】(${concentration.maxSingle.weight.toFixed(1)}%)，前三大标的合计 (${concentration.top3Weight.toFixed(1)}%)。${concentration.targetAdvice}
- **市场与币种集中度**：最大板块【${concentration.maxMarket.market}】占比 ${concentration.maxMarket.weight.toFixed(1)}%。${concentration.marketAdvice}
- **策略风格集中度**：红利低波风格簇占比 **${concentration.dividendStyleWeight.toFixed(1)}%**。${concentration.styleAdvice}

---

## 五、 现金缓冲池平滑与四大复合情景压力测试横向对比

### 5.1 36 个月常规基准平滑
- 缓冲池初始种子金：¥${(board.bufferSeed * 10000).toLocaleString()} 元
- 36 个月最低水位：¥${Math.round(bufferMetrics.minBuffer).toLocaleString()} 元（${bufferMetrics.isBufferSafe ? '✅ 安全平滑，未发生亏空断流' : '⚠️ 出现负余额断流风险'}）
- 最脆弱月份：第 ${bufferMetrics.mostFragileMonth} 个月

### 5.2 四大情景复合压力测试横向对比表
| 压力测试情景 | 核心压力特征假设 | 缓冲池是否枯竭 | 最早枯竭月份 | 极限最低水位 / 需折算变现资产 | 恢复目标储备月数 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **标准复合情景** | 失业6月(替代率30%)+分红降30%+回撤20% | ${stdStress.isExhausted ? '🔴 枯竭' : '🟢 未枯竭'} | ${stdStress.isExhausted ? `第 ${stdStress.exhaustionMonth} 月` : '全程平稳'} | ${stdStress.isExhausted ? `需变现 ¥${stdStress.minAssetToSell.toLocaleString()} 元` : `最低 ¥${stdStress.minBuffer.toLocaleString()} 元`} | ${stdStress.monthsToRecover} 个月 |
| **严重复合情景** | 失业12月+分红降50%+回撤35%+突发医疗20万 | ${sevStress.isExhausted ? '🔴 枯竭' : '🟢 未枯竭'} | ${sevStress.isExhausted ? `第 ${sevStress.exhaustionMonth} 月` : '全程平稳'} | ${sevStress.isExhausted ? `需变现 ¥${sevStress.minAssetToSell.toLocaleString()} 元` : `最低 ¥${sevStress.minBuffer.toLocaleString()} 元`} | ${sevStress.monthsToRecover} 个月 |
| **滞胀复合情景** | 年通胀5%(生活费递增)+分红延迟4月+分红降20% | ${stagStress.isExhausted ? '🔴 枯竭' : '🟢 未枯竭'} | ${stagStress.isExhausted ? `第 ${stagStress.exhaustionMonth} 月` : '全程平稳'} | ${stagStress.isExhausted ? `需变现 ¥${stagStress.minAssetToSell.toLocaleString()} 元` : `最低 ¥${stagStress.minBuffer.toLocaleString()} 元`} | ${stagStress.monthsToRecover} 个月 |
| **2018 历史回放** | 12个月逐月阴跌回撤25%+分红正常 | ${repStress.isExhausted ? '🔴 枯竭' : '🟢 未枯竭'} | ${repStress.isExhausted ? `第 ${repStress.exhaustionMonth} 月` : '全程平稳'} | ${repStress.isExhausted ? `需变现 ¥${repStress.minAssetToSell.toLocaleString()} 元` : `最低 ¥${repStress.minBuffer.toLocaleString()} 元`} | ${repStress.monthsToRecover} 个月 |

---

## 六、 🎯 目标达成总览明细表 (多目标资源挤占模型)

| 序号 | 目标名称 | 目标类型 | 优先级 | 目标年份 | 目标金额 | 分配本金 | 分配月结余 | 推演终值 (FV) | 达成状态 | 缺口调控对策 (三大可调杠杆) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
${goalRows}

${fireSection}---

## 七、 综合财务评分与可解释归因明细

### 7.1 财务脆弱性评分：${scores.totalVulnerability} 分 (满分100分，${scores.vulnerabilityLevel}，越低越健康)
- **首要短板**：${scores.worstVulnConclusion}

| 归因子维度 | 得分 / 满分 | 现状说明与归因依据 |
| :--- | :---: | :--- |
${scores.vulnFactors.map(f => `| **${f.name}** | **${f.score} / ${f.max} 分** | ${f.desc} |`).join('\n')}

### 7.2 客观理财进攻性评分：${scores.totalAggressiveness} 分 (${scores.aggressivenessLevel})
| 客观行为因子 | 得分 / 满分 | 因子状态说明 |
| :--- | :---: | :--- |
${scores.aggFactors.map(f => `| **${f.name}** | **${f.score} / ${f.max} 分** | ${f.desc} |`).join('\n')}

---

> [!NOTE]
> **免责声明**：${DISCLAIMER_TEXT}
`;
}
