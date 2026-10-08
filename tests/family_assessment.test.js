const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

async function loadAssessmentModule() {
  return import(pathToFileURL(
    path.resolve(__dirname, '../src/utils/familyAssessment.js')
  ).href);
}

const healthyBase = {
  household: {
    adults: 2,
    children: 1,
    elderlyDependents: 0,
    primaryAge: 36,
    incomeSourceType: 'dual_salary',
    incomeStability: 'stable',
    yearsToRetirement: 24,
  },
  cashflow: {
    monthlyIncome: 36000,
    essentialMonthlyExpense: 15000,
    monthlyDebtPayment: 5000,
  },
  assets: {
    cash: 260000,
    bonds: 180000,
    equities: 360000,
    gold: 60000,
    property: 1800000,
    business: 0,
    otherLiquid: 0,
  },
  debts: {
    total: 600000,
    highInterest: 0,
    highestRate: 3.6,
  },
  goals: {
    expensesWithin1Year: 30000,
    expenses1To3Years: 100000,
    homePurchaseWithinYears: null,
  },
  protection: {
    basicMedicalCovered: true,
    lifeCoverageGap: 0,
  },
  risk: {
    investmentHorizonYears: 12,
    maxAcceptableLossPct: 20,
    marketDropReaction: 'hold',
  },
};

test('双薪育儿家庭输出完整画像、三维风险和非产品化配置区间', async () => {
  const { assessFamily } = await loadAssessmentModule();
  const result = assessFamily(healthyBase);

  assert.equal(result.lifecycle.key, 'dual_income_parent');
  assert.equal(result.profile.key, 'dual_income_parent');
  assert.equal(result.completeness.isSufficient, true);
  assert.equal(result.risk.finalLevel, Math.min(
    result.risk.capacity.level,
    result.risk.willingness.level,
    result.risk.actualExposure.level
  ));
  assert.equal(result.topActions.length, 3);
  assert.ok(result.investable.safeUpperBound >= 0);
  assert.ok(result.allocationRanges.growth.max >= result.allocationRanges.growth.min);
  assert.equal(JSON.stringify(result).includes('ETF'), false);
  assert.equal(JSON.stringify(result).includes('基金'), false);
});

test('合法零值不会被示例默认值覆盖，零收入会触发现金流红线', async () => {
  const { assessFamily } = await loadAssessmentModule();
  const input = structuredClone(healthyBase);
  input.cashflow.monthlyIncome = 0;
  input.cashflow.monthlyDebtPayment = 0;
  input.assets.property = 0;
  input.debts.total = 0;
  input.goals.expensesWithin1Year = 0;
  input.goals.expenses1To3Years = 0;

  const result = assessFamily(input);

  assert.equal(result.normalized.cashflow.monthlyIncome, 0);
  assert.equal(result.normalized.assets.property, 0);
  assert.equal(result.normalized.debts.total, 0);
  assert.equal(result.completeness.missingFields.includes('cashflow.monthlyIncome'), false);
  assert.equal(result.redLines.some(item => item.code === 'negative_cashflow'), true);
  assert.equal(result.investable.safeUpperBound, 0);
});

test('缺失值进入完整度清单，不伪造结论或金额', async () => {
  const { assessFamily } = await loadAssessmentModule();
  const result = assessFamily({
    household: { adults: 1, children: 0, primaryAge: 27 },
    cashflow: { monthlyIncome: null },
    assets: { cash: 0 },
  });

  assert.equal(result.completeness.isSufficient, false);
  assert.ok(result.completeness.missingFields.includes('cashflow.monthlyIncome'));
  assert.equal(result.investable.safeUpperBound, null);
  assert.equal(result.risk.finalLevel, null);
  assert.equal(result.topActions[0].code, 'complete_information');
});

test('硬性红线覆盖生命周期建议并禁止进攻配置', async () => {
  const { assessFamily } = await loadAssessmentModule();
  const input = structuredClone(healthyBase);
  input.debts.highInterest = 180000;
  input.debts.highestRate = 15;
  input.cashflow.monthlyDebtPayment = 18000;

  const result = assessFamily(input);

  assert.equal(result.lifecycle.key, 'dual_income_parent');
  assert.equal(result.profile.key, 'high_debt_pressure');
  assert.equal(result.redLines[0].code, 'high_interest_debt');
  assert.equal(result.allocationRanges.growth.max, 0);
  assert.match(result.topActions[0].title, /高息负债/);
});

test('多条红线按高息负债、负现金流、偿债过载的顺序输出', async () => {
  const { assessFamily } = await loadAssessmentModule();
  const input = structuredClone(healthyBase);
  input.cashflow.monthlyIncome = 20000;
  input.cashflow.monthlyDebtPayment = 12000;
  input.cashflow.essentialMonthlyExpense = 10000;
  input.debts.highInterest = 100000;
  input.debts.highestRate = 12;

  const result = assessFamily(input);

  assert.deepEqual(result.redLines.slice(0, 3).map(item => item.code), [
    'high_interest_debt',
    'negative_cashflow',
    'debt_service_overload',
  ]);
  assert.deepEqual(result.redLines.slice(0, 3).map(item => item.priorityRank), [1, 2, 3]);
});

test('风险最终等级严格取能力、意愿和实际暴露适配度的最低值', async () => {
  const { assessFamily } = await loadAssessmentModule();
  const input = structuredClone(healthyBase);
  input.risk.maxAcceptableLossPct = 5;
  input.risk.marketDropReaction = 'panic_sell';

  const result = assessFamily(input);

  assert.equal(result.risk.willingness.level, 1);
  assert.equal(result.risk.finalLevel, 1);
  assert.equal(result.risk.finalLabel, '保守');
});

const lifecycleTemplates = [
  ['young_single', {
    household: { adults: 1, children: 0, elderlyDependents: 0, primaryAge: 28, incomeSourceType: 'single_salary', incomeStability: 'stable', yearsToRetirement: 32 },
  }],
  ['dual_income_parent', {}],
  ['single_income_dependents', {
    household: { adults: 2, children: 2, elderlyDependents: 1, primaryAge: 39, incomeSourceType: 'single_salary', incomeStability: 'stable', yearsToRetirement: 21 },
  }],
  ['self_employed_variable', {
    household: { adults: 2, children: 1, elderlyDependents: 0, primaryAge: 38, incomeSourceType: 'self_employed', incomeStability: 'volatile', yearsToRetirement: 22 },
  }],
  ['home_purchase', {
    goals: { expensesWithin1Year: 50000, expenses1To3Years: 600000, homePurchaseWithinYears: 2 },
  }],
  ['near_retirement', {
    household: { adults: 2, children: 0, elderlyDependents: 0, primaryAge: 57, incomeSourceType: 'dual_salary', incomeStability: 'stable', yearsToRetirement: 3 },
  }],
  ['retired', {
    household: { adults: 2, children: 0, elderlyDependents: 0, primaryAge: 67, incomeSourceType: 'pension', incomeStability: 'stable', yearsToRetirement: 0, retired: true },
  }],
];

for (const [expectedKey, overrides] of lifecycleTemplates) {
  test(`识别家庭生命周期模板：${expectedKey}`, async () => {
    const { assessFamily } = await loadAssessmentModule();
    const input = structuredClone(healthyBase);
    Object.entries(overrides).forEach(([section, value]) => {
      input[section] = { ...(input[section] || {}), ...value };
    });
    const result = assessFamily(input);
    assert.equal(result.lifecycle.key, expectedKey);
    assert.equal(result.topActions.length, 3);
  });
}

test('高房产或经营资产集中作为财务约束画像保留生命周期', async () => {
  const { assessFamily } = await loadAssessmentModule();
  const input = structuredClone(healthyBase);
  input.assets.property = 6000000;
  input.assets.business = 1500000;
  input.assets.equities = 100000;

  const result = assessFamily(input);

  assert.equal(result.lifecycle.key, 'dual_income_parent');
  assert.equal(result.profile.key, 'property_business_concentrated');
  assert.ok(result.constraints.some(item => item.code === 'property_concentration'));
  assert.ok(result.constraints.some(item => item.code === 'business_concentration'));
  assert.match(result.stress.message, /集中/);
});

test('压力提示反映失业冲击后的覆盖月数', async () => {
  const { assessFamily } = await loadAssessmentModule();
  const input = structuredClone(healthyBase);
  input.household.incomeStability = 'volatile';
  input.cashflow.incomeShockPct = 80;

  const result = assessFamily(input);

  assert.ok(Number.isFinite(result.stress.cashCoverageMonths));
  assert.ok(Number.isFinite(result.stress.stressedCoverageMonths));
  assert.ok(result.stress.stressedCoverageMonths <= result.stress.cashCoverageMonths);
  assert.ok(result.stress.message.length > 0);
});

test('任意合法模板输出不包含 NaN 或 Infinity', async () => {
  const { assessFamily } = await loadAssessmentModule();
  const result = assessFamily(healthyBase);
  const serialized = JSON.stringify(result);

  assert.equal(serialized.includes('NaN'), false);
  assert.equal(serialized.includes('Infinity'), false);
});
