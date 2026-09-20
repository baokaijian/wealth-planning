import {
  calculateBoardMetrics,
  calculateBufferSimulation,
  calculateGoalProjection,
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
import { STRESS_PRESETS, DISCLAIMER_TEXT } from '../constants.js';

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

  // 运行标准复合压力测试
  const stdStress = runCompoundStressTest(board, STRESS_PRESETS.standard, health, 36);

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

  // 构建目标达成总览行
  const goalRows = goals.map((goal, idx) => {
    const currentPrincipalYuan = (board.principal || 50) * 10000;
    const reservedYuan = goal.linkTo1To3y ? (health.bucket1To3y || 0) : (goal.reservedAmount || 0);
    const monthlySurplusYuan = health.monthlySurplus || 0;

    const proj = calculateGoalProjection({
      currentYear,
      targetYear: goal.targetYear,
      targetAmount: goal.targetAmount,
      monthlySurplus: monthlySurplusYuan,
      growthRate: board.growthRate,
      currentPrincipal: currentPrincipalYuan,
      reservedAmount: reservedYuan,
      safeRate: 2.0
    });

    const statusBadge = proj.isAchieved
      ? `🟢 预计富余 ¥${Math.round(proj.diff).toLocaleString()}`
      : `🔴 预计缺口 ¥${Math.round(proj.gap).toLocaleString()}`;

    let leverText = '已达成，无需调控';
    if (!proj.isAchieved && proj.levers) {
      const { extraMonthly, reqRatePct, rateDiffPct, isRateSafe, loosenAmount, delayYears, delayedTargetYear } = proj.levers;
      const rateLabel = isRateSafe
        ? `提升至 ${reqRatePct}% (+${rateDiffPct}%, 稳健区间内)`
        : `提升至 ${reqRatePct}% (+${rateDiffPct}%, ⚠️超稳健上限8%)`;
      leverText = `①每月多储 ¥${extraMonthly.toLocaleString()}<br>②收益率${rateLabel}<br>③降目标至 ¥${(goal.targetAmount - loosenAmount).toLocaleString()} 或延至 ${delayedTargetYear}年 (+${delayYears}年)`;
    }

    return `| ${idx + 1} | ${goal.name} | ${goal.type} | ${goal.priority} | ${goal.targetYear}年 | ¥${Number(goal.targetAmount).toLocaleString()} | ¥${Math.round(proj.fvTotal).toLocaleString()} | ${statusBadge} | ${leverText} |`;
  }).join('\n');

  // 提前退休专项推演
  const fireGoals = goals.filter(g => g.type === '提前退休');
  let fireSection = '';
  if (fireGoals.length > 0) {
    fireSection = `### 4.2 提前退休全生命周期持久性检验 (至 85 岁)\n\n`;
    fireGoals.forEach(fg => {
      const currentPrincipalYuan = (board.principal || 50) * 10000;
      const reservedYuan = fg.linkTo1To3y ? (health.bucket1To3y || 0) : (fg.reservedAmount || 0);
      const proj = calculateGoalProjection({
        currentYear,
        targetYear: fg.targetYear,
        targetAmount: fg.targetAmount,
        monthlySurplus: health.monthlySurplus || 0,
        growthRate: board.growthRate,
        currentPrincipal: currentPrincipalYuan,
        reservedAmount: reservedYuan
      });

      const retConfig = fg.retireConfig || { currentAge: 35, retireAge: 50, retireMonthlyExpense: 10000 };
      const retSim = simulateEarlyRetirement({
        currentAge: retConfig.currentAge,
        retireAge: retConfig.retireAge,
        targetAmount: fg.targetAmount,
        projectedCapitalAtRetire: proj.fvTotal,
        monthlyExpense: retConfig.retireMonthlyExpense,
        dividendYield: boardMetrics.blendedYield,
        bufferInterestRate: board.moneyMarketRate,
        endAge: 85
      });

      fireSection += `**目标名称**：${fg.name}（计划 ${fg.targetYear} 年 / ${retConfig.retireAge} 岁退休）\n`;
      fireSection += `- **退休期初总本金推演终值**：¥${Math.round(proj.fvTotal).toLocaleString()}\n`;
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
- **四桶资金期限布局**：
  - 1年内 (活期应急)：¥${Number(health.bucket1y || 0).toLocaleString()} 元
  - 1-3年 (确定要用的钱)：¥${Number(health.bucket1To3y || 0).toLocaleString()} 元
  - 3-5年 (稳健配置)：¥${Number(health.bucket3To5y || 0).toLocaleString()} 元
  - 5年以上 (长期权益与红利)：¥${Number(health.bucket5yPlus || 0).toLocaleString()} 元

### 1.2 流动性硬隔离检查
- **流动金融资产总额**：¥${liqCheck.liquidFinancialAssets.toLocaleString()} 元
- **未来 12 个月确定性支出 (100% 隔离)**：¥${liqCheck.bucket1y.toLocaleString()} 元
- **未来 1-3 年确定性支出 (50% 折减隔离)**：¥${(liqCheck.bucket1To3y * liqCheck.discountFactor).toLocaleString()} 元
- **可投资资金上限**：**¥${Math.round(liqCheck.investableCeiling).toLocaleString()} 元**
- **当前实际可用本金**：¥${liqCheck.boardPrincipalYuan.toLocaleString()} 元（${liqCheck.isViolated ? '⚠️ **已超限**' : '✅ **在安全限额内**'}）
- **短期支出覆盖倍数**：**${liqCheck.coverageRatio} 倍**（${liqCheck.isCoverageInsufficient ? '⚠️ 低于 1.5 倍安全底线，应急流动性不足' : '✅ 流动性储备充裕'}）
- *架构口径说明：${liqCheck.distinctionNote}*

### 1.3 房产集中度与购房首付核验
- **房产当前总估值**：¥${reRisk.propertyVal.toLocaleString()} 元（房贷余额：¥${reRisk.mortgage.toLocaleString()} 元）
- **房产净资产占比**：**${reRisk.realEstateRatio}%**（评级：**${reRisk.tier === 'green' ? '🟢 绿色健康' : (reRisk.tier === 'yellow' ? '🟡 黄色偏高' : '🔴 红色高危')}**）
- **房产集中度分析提示**：${reRisk.tierAdvice}
- **首付储备核验**：${reRisk.hasHousePlan ? (reRisk.isDownPaymentShort ? `⚠️ 计划购房首付 ¥${reRisk.expectedDownPayment.toLocaleString()} 元，确定资金存在 ¥${reRisk.downPaymentGap.toLocaleString()} 元缺口！**${reRisk.downPaymentWarning}**` : '✅ 购房首付资金已足额预留') : '无近期买房/换房计划'}
- **房产下跌 ${reRisk.stressDropPct}% 压力冲击**：全口径净资产从 ¥${Math.round(reRisk.totalNetWorth).toLocaleString()} 元降至 ¥${Math.round(reRisk.stressTotalNetWorth).toLocaleString()} 元，资产负债率从 ${reRisk.normalDebtToAsset}% 上升至 ${reRisk.stressDebtToAsset}%。

---

## 二、 家庭保障缺口测算 (责任缺口法)

- **寿险保障测算**：
  - 责任总需求：¥${Math.round(insGap.lifeTarget).toLocaleString()} 元（包含全部负债 ¥${debtMetrics.totalDebtBalance.toLocaleString()} + 10年生活底线 ¥${(health.essentialMonthlyExpense*120).toLocaleString()} + 教育金 ¥${insGap.childEduTarget || 500000} - 流动资产）
  - 已有保额：¥${insGap.existingLife.toLocaleString()} 元
  - **寿险净缺口**：**¥${insGap.lifeGap.toLocaleString()} 元**（折合家庭年收入 **${insGap.lifeGapIncomeMultiple} 倍**）
- **重疾保障测算**（按行业稳定度【${insGap.stabConfig.label}】联动）：
  - 建议保额：¥${Math.round(insGap.critTarget).toLocaleString()} 元（${insGap.stabConfig.years}年收入 + ¥${insGap.stabConfig.medical.toLocaleString()} 治疗康复金）
  - 已有保额：¥${insGap.existingCrit.toLocaleString()} 元
  - **重疾净缺口**：**¥${insGap.critGap.toLocaleString()} 元**（折合家庭年收入 **${insGap.critGapIncomeMultiple} 倍**）
- **意外险建议额**：建议保额 ¥${insGap.accidentTarget.toLocaleString()} 元，已有 ¥${insGap.existingAccident.toLocaleString()} 元，净缺口 **¥${insGap.accidentGap.toLocaleString()} 元**。
- **百万医疗兜底检查**：${insGap.hasMillionMedical ? '✅ 已配置百万医疗险（大额自费医疗风险已兜底）' : '⚠️ **未配置百万医疗险**（大额住院费用可能击穿家庭储蓄防线）'}

---

## 三、 债务决策对照与个人养老金税优

### 3.1 债务决策对照矩阵
- **综合负债总额**：¥${debtMetrics.totalDebtBalance.toLocaleString()} 元（月供支出：¥${Number(debt.monthlyDebtPayment || 0).toLocaleString()} 元）
- **综合贷款利率档位**：**${debtMetrics.bracket}** (测算利率: **${debtMetrics.effectiveDebtRate}%**，按档位中值估算，请以实际合同利率为准)
- **组合保守预期收益率**：**${debtMetrics.conservativeYield}%** (取增长预期收益率 ${debtMetrics.growthRate}% 的 70% 作为保守基准)
- **决策矩阵研判结论**：**${debtMetrics.decisionText}**

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
- **加权税后现金流收益率**：**${boardMetrics.blendedYield.toFixed(2)}%**
- **长期增长预期年化收益率**：**${boardMetrics.growthRate.toFixed(2)}%**
- **预期年税后分红总额**：¥${Math.round(boardMetrics.expectedAnnualDividend).toLocaleString()} 元（折合月均 ¥${Math.round(boardMetrics.expectedMonthlyAvg).toLocaleString()} 元）

### 4.2 行为约束引擎硬限额
- **您的行为约束权益上限**：**${behCheck.finalCeiling}%**（根据自评回撤 ${behCheck.bracket} 及恐慌反应严格反解）
- **当前实际配置权益比例**：**${behCheck.actualEquityWeight.toFixed(1)}%**（${behCheck.isExceeded ? `⚠️ 超限 ${behCheck.excessWeight.toFixed(1)}%！${behCheck.warningText}` : '✅ 符合心理与财务耐受底线'}）
- **隐含极端权益回撤承受力**：约 ${behCheck.implicitDrawdown}%

### 4.3 三重集中度诊断
- **标的集中度**：单一最大标的【${concentration.maxSingle.name}】(${concentration.maxSingle.weight.toFixed(1)}%)，前三大标的合计 (${concentration.top3Weight.toFixed(1)}%)。${concentration.targetAdvice}
- **市场与币种集中度**：最大板块【${concentration.maxMarket.market}】占比 ${concentration.maxMarket.weight.toFixed(1)}%。${concentration.marketAdvice}
- **策略风格集中度**：红利低波风格簇占比 **${concentration.dividendStyleWeight.toFixed(1)}%**。${concentration.styleAdvice}

---

## 五、 现金缓冲池平滑与复合情景压力测试

### 5.1 36 个月常规基准平滑
- 缓冲池初始种子金：¥${(board.bufferSeed * 10000).toLocaleString()} 元
- 36 个月最低水位：¥${Math.round(bufferMetrics.minBuffer).toLocaleString()} 元（${bufferMetrics.isBufferSafe ? '✅ 安全平滑，未发生亏空断流' : '⚠️ 出现负余额断流风险'}）
- 最脆弱月份：第 ${bufferMetrics.mostFragileMonth} 个月

### 5.2 复合情景压力测试（标准复合：失业6个月 + 分红降30% + 权益回撤20%）
- **情景推演结论**：${stdStress.isExhausted ? `⚠️ 缓冲池在**第 ${stdStress.exhaustionMonth} 个月出现枯竭**！` : '✅ 成功抵抗标准复合压力冲击，缓冲池全程未穿透。'}
- **枯竭时需变现资产金额（按回撤折价后折算）**：¥${stdStress.minAssetToSell.toLocaleString()} 元
- **压力解除后恢复目标储备所需月数**：约 ${stdStress.monthsToRecover} 个月

---

## 六、 🎯 目标达成总览明细表

| 序号 | 目标名称 | 目标类型 | 优先级 | 目标年份 | 目标金额 | 简化推演终值 | 达成状态 | 缺口调控对策 (三大可调杠杆) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
${goalRows}

${fireSection}---

## 七、 综合财务评分与可解释归因明细

- **财务脆弱性评分**：**${scores.totalVulnerability} 分**（评级：**${scores.vulnerabilityLevel}**，分值越低越稳健）
  - 核心归因：${scores.worstVulnConclusion}
- **理财进攻性评分**：**${scores.totalAggressiveness} 分**（评级：**${scores.aggressivenessLevel}**）

---

> [!NOTE]
> **免责声明**：${DISCLAIMER_TEXT}
`;
}
