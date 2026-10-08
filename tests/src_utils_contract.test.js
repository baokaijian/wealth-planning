const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const projectRoot = path.resolve(__dirname, '..');

async function loadProductionModules() {
  return {
    constants: await import(pathToFileURL(path.join(projectRoot, 'src/constants.js')).href),
    calculations: await import(pathToFileURL(path.join(projectRoot, 'src/utils/calculations.js')).href),
    reports: await import(pathToFileURL(path.join(projectRoot, 'src/utils/reportGenerator.js')).href)
  };
}

const modulesPromise = loadProductionModules();

test('真实计算模块保留所有显式零值，不回填演示默认值', async () => {
  const { calculations } = await modulesPromise;

  const board = {
    principal: 0,
    bufferSeed: 0,
    targetMonthly: 0,
    growthRate: 0,
    moneyMarketRate: 0,
    assets: {}
  };
  assert.equal(calculations.calculateBoardMetrics(board).targetMonthlyYuan, 0);
  assert.equal(calculations.calculateBufferSimulation(board, 1).timeline[0].withdraw, 0);

  const projection = calculations.calculateGoalProjection({
    currentYear: 2026,
    targetYear: 2027,
    targetAmount: 0,
    monthlySurplus: 0,
    growthRate: 0,
    currentPrincipal: 100,
    reservedAmount: 0,
    safeRate: 0
  });
  assert.equal(projection.fvPrincipal, 100);

  const retirement = calculations.simulateEarlyRetirement({
    currentAge: 50,
    retireAge: 50,
    targetAmount: 1200,
    projectedCapitalAtRetire: 1200,
    monthlyExpense: 100,
    dividendYield: 0,
    bufferInterestRate: 0,
    endAge: 51
  });
  assert.equal(retirement.finalCapital, 0);

  const insurance = calculations.calculateInsuranceGap(
    {
      monthlyIncome: 0,
      essentialMonthlyExpense: 0,
      assetsBreakdown: { cashCurrent: 0, cashShortDebt: 0 }
    },
    {
      childEduTarget: 0,
      existingLifeCover: 0,
      existingCritCover: 0,
      existingAccidentCover: 0,
      stabilityTier: 'medium',
      hasMillionMedical: true,
      coverageTier: 'strong'
    },
    0
  );
  assert.equal(insurance.childEduTarget, 0);
  assert.equal(insurance.lifeTarget, 0);

  const pension = calculations.calculatePensionTaxBenefit({
    currentYearDeposited: 0,
    marginalTaxRate: 0
  });
  assert.equal(pension.taxRate, 0);
  assert.equal(pension.annualTaxSavingsForegone, 0);

  const liquidity = calculations.checkLiquiditySegregation({
    assetsBreakdown: {},
    expectedExpenses: { expense1y: 0, expense1To3y: 0 }
  }, 0);
  assert.equal(liquidity.expense1y, 0);
  assert.equal(liquidity.expense1To3y, 0);
  assert.equal(liquidity.boardPrincipalYuan, 0);

  const stress = calculations.runCompoundStressTest(board, {
    unemploymentMonths: 0,
    unemploymentReplacementRate: 0,
    dividendDropRate: 0,
    delayMonths: 0,
    medicalExpense: 0,
    inflationRate: 0,
    equityDrawdownRate: 0
  }, {
    monthlyIncome: 0,
    essentialMonthlyExpense: 0,
    monthlySurplus: 0
  }, 1);
  assert.equal(stress.timeline[0].withdraw, 0);
  assert.equal(stress.timeline[0].unemploymentLoss, 0);
});

test('房产测算公开稳定报告契约并保留无房无债家庭零值', async () => {
  const { calculations } = await modulesPromise;
  const result = calculations.calculateRealEstateRisk(
    { totalEstimatedValue: 0, stressDropPct: 0 },
    {
      hasHousePlan: false,
      expectedDownPayment: 0,
      assetsBreakdown: {
        cashCurrent: 0,
        cashShortDebt: 0,
        equityAssets: 0,
        goldAssets: 0,
        bondAssets: 0,
        otherAssets: 0,
        pensionCashValue: 0
      }
    },
    {
      mortgageBalance: 0,
      carLoanBalance: 0,
      consumerLoanBalance: 0,
      businessLoanBalance: 0
    }
  );

  assert.equal(result.propertyVal, 0);
  assert.equal(result.mortgage, 0);
  assert.equal(result.totalAssets, 0);
  assert.equal(result.totalDebt, 0);
  assert.equal(result.totalNetWorth, 0);
  assert.equal(result.financialAssets, 0);
  assert.equal(result.financialDebt, 0);
  assert.equal(result.financialNetWorth, 0);
  assert.equal(result.normalDebtToAsset, 0);
  assert.equal(result.financialDebtRatio, 0);
  assert.equal(result.stressDebtToAsset, 0);
  assert.equal(result.realEstateRatio, 0);
  assert.equal(result.stressDropAmount, 0);
  assert.equal(result.stressTotalNetWorth, 0);
  assert.equal(result.expectedDownPayment, 0);
  assert.match(result.tierAdvice, /房产/);
  assert.equal(typeof result.downPaymentWarning, 'string');
});

test('养老金建议字段完整，Markdown 报告永不输出非有限值或缺失字段标记', async () => {
  const { constants, calculations, reports } = await modulesPromise;
  const pension = calculations.calculatePensionTaxBenefit({
    hasAccount: false,
    currentYearDeposited: 0,
    marginalTaxRate: 0
  });
  assert.match(pension.guidanceText, /税|养老金/);

  const report = reports.generateMarkdownReport({
    board: {
      principal: 0,
      bufferSeed: 0,
      targetMonthly: 0,
      growthRate: 0,
      moneyMarketRate: 0,
      assets: {}
    },
    health: {
      monthlyIncome: 0,
      monthlyExpense: 0,
      essentialMonthlyExpense: 0,
      monthlySurplus: 0,
      unemploymentRecoveryMonths: 0,
      expectedExpenses: { expense1y: 0, expense1To3y: 0 },
      assetsBreakdown: {}
    },
    insurance: {
      childEduTarget: 0,
      existingLifeCover: 0,
      existingCritCover: 0,
      existingAccidentCover: 0,
      hasMillionMedical: true,
      coverageTier: 'strong'
    },
    debt: {
      mortgageBalance: 0,
      carLoanBalance: 0,
      consumerLoanBalance: 0,
      businessLoanBalance: 0,
      monthlyDebtPayment: 0,
      remainingYears: 0,
      availableFundX: 0
    },
    pension: { currentYearDeposited: 0, marginalTaxRate: 0 },
    property: { totalEstimatedValue: 0, stressDropPct: 0 },
    behavior: {},
    goals: []
  });

  assert.doesNotMatch(report, /\b(?:NaN|undefined|Infinity)\b/);
  assert.match(report, /\*标的指引建议：[^*]+\*/);
  assert.match(report, /\| \*\*总资产\*\* \| ¥0 元 \| ¥0 元 \| ¥0 元 \|/);

  const initialReport = reports.generateMarkdownReport(constants.INITIAL_STATE);
  assert.doesNotMatch(initialReport, /\b(?:NaN|undefined|Infinity)\b/);
  assert.match(initialReport, /房产集中度分析提示/);
});

test('债务与投资利差落入不确定区间时不输出确定性胜负', async () => {
  const { calculations } = await modulesPromise;
  const result = calculations.calculateDebtDecisionMetrics({
    debtRateBracket: '3.5-4.5%',
    useCustomRate: true,
    customDebtRate: 4.0,
    availableFundX: 200000
  }, 6.0);

  assert.equal(result.decisionType, 'neutral');
  assert.match(result.decisionText, /风险偏好与流动性/);
  assert.match(result.assumptionNote, /并非保证/);
  assert.ok(result.comparisonTable.every(row => row.advantage === '差异不具稳健优势'));
});
