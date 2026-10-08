// 家庭快速评估纯函数模型。金额单位统一为元，比例输入统一为百分数。

const RISK_LABELS = {
  1: '保守',
  2: '稳健',
  3: '均衡',
  4: '成长',
  5: '积极',
};

const LIFECYCLE_CONFIG = {
  young_single: { title: '年轻单身积累期', emergencyMonths: 6 },
  dual_income_parent: { title: '双薪育儿家庭', emergencyMonths: 9 },
  single_income_dependents: { title: '单薪多责任家庭', emergencyMonths: 12 },
  self_employed_variable: { title: '自雇及收入波动家庭', emergencyMonths: 12 },
  home_purchase: { title: '买房或换房准备期', emergencyMonths: 9 },
  near_retirement: { title: '临近退休家庭', emergencyMonths: 12 },
  retired: { title: '已退休家庭', emergencyMonths: 18 },
  general: { title: '家庭发展期', emergencyMonths: 9 },
};

const PROFILE_CONFIG = {
  high_debt_pressure: '高债务承压家庭',
  cashflow_pressure: '现金流承压家庭',
  property_business_concentrated: '高房产或经营资产集中家庭',
  protection_gap: '保障缺口家庭',
};

const REQUIRED_FIELDS = [
  ['household.adults', '家庭成年人数'],
  ['household.children', '子女人数'],
  ['household.primaryAge', '家庭主要决策者年龄'],
  ['household.incomeSourceType', '收入来源类型'],
  ['household.incomeStability', '收入稳定性'],
  ['cashflow.monthlyIncome', '税后月收入'],
  ['cashflow.essentialMonthlyExpense', '月必要支出'],
  ['cashflow.monthlyDebtPayment', '每月偿债额'],
  ['assets.cash', '随时可用现金'],
  ['assets.bonds', '稳健类金融资产'],
  ['assets.equities', '权益类金融资产'],
  ['assets.property', '房产估值'],
  ['debts.total', '负债总额'],
  ['debts.highInterest', '高息负债余额'],
  ['goals.expensesWithin1Year', '一年内确定支出'],
  ['goals.expenses1To3Years', '一至三年确定支出'],
  ['protection.basicMedicalCovered', '基础医疗保障情况'],
  ['risk.investmentHorizonYears', '投资期限'],
  ['risk.maxAcceptableLossPct', '最大可接受亏损'],
  ['risk.marketDropReaction', '市场下跌反应'],
];

function getPath(value, path) {
  return path.split('.').reduce((current, key) => (
    current !== null && current !== undefined ? current[key] : undefined
  ), value);
}

function isProvided(value) {
  return value !== null && value !== undefined && value !== '';
}

function numberOrNull(value) {
  if (!isProvided(value)) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function nonNegativeOrNull(value) {
  const parsed = numberOrNull(value);
  return parsed === null ? null : Math.max(0, parsed);
}

function sumKnown(values) {
  return values.reduce((total, value) => total + (value === null ? 0 : value), 0);
}

function round(value, digits = 2) {
  if (!Number.isFinite(value)) return null;
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

function normalizeInput(input = {}) {
  const household = input.household || {};
  const cashflow = input.cashflow || {};
  const assets = input.assets || {};
  const debts = input.debts || {};
  const goals = input.goals || {};
  const protection = input.protection || {};
  const risk = input.risk || {};

  return {
    household: {
      adults: nonNegativeOrNull(household.adults),
      children: nonNegativeOrNull(household.children),
      elderlyDependents: nonNegativeOrNull(household.elderlyDependents),
      primaryAge: nonNegativeOrNull(household.primaryAge),
      incomeSourceType: isProvided(household.incomeSourceType) ? household.incomeSourceType : null,
      incomeStability: isProvided(household.incomeStability) ? household.incomeStability : null,
      yearsToRetirement: nonNegativeOrNull(household.yearsToRetirement),
      retired: household.retired === true,
    },
    cashflow: {
      monthlyIncome: nonNegativeOrNull(cashflow.monthlyIncome),
      essentialMonthlyExpense: nonNegativeOrNull(cashflow.essentialMonthlyExpense),
      monthlyDebtPayment: nonNegativeOrNull(cashflow.monthlyDebtPayment),
      incomeShockPct: nonNegativeOrNull(cashflow.incomeShockPct),
    },
    assets: {
      cash: nonNegativeOrNull(assets.cash),
      bonds: nonNegativeOrNull(assets.bonds),
      equities: nonNegativeOrNull(assets.equities),
      gold: nonNegativeOrNull(assets.gold),
      property: nonNegativeOrNull(assets.property),
      business: nonNegativeOrNull(assets.business),
      otherLiquid: nonNegativeOrNull(assets.otherLiquid),
    },
    debts: {
      total: nonNegativeOrNull(debts.total),
      highInterest: nonNegativeOrNull(debts.highInterest),
      highestRate: nonNegativeOrNull(debts.highestRate),
    },
    goals: {
      expensesWithin1Year: nonNegativeOrNull(goals.expensesWithin1Year),
      expenses1To3Years: nonNegativeOrNull(goals.expenses1To3Years),
      homePurchaseWithinYears: nonNegativeOrNull(goals.homePurchaseWithinYears),
    },
    protection: {
      basicMedicalCovered: typeof protection.basicMedicalCovered === 'boolean'
        ? protection.basicMedicalCovered
        : null,
      lifeCoverageGap: nonNegativeOrNull(protection.lifeCoverageGap),
    },
    risk: {
      investmentHorizonYears: nonNegativeOrNull(risk.investmentHorizonYears),
      maxAcceptableLossPct: nonNegativeOrNull(risk.maxAcceptableLossPct),
      marketDropReaction: isProvided(risk.marketDropReaction) ? risk.marketDropReaction : null,
      largestHoldingPct: nonNegativeOrNull(risk.largestHoldingPct),
      singleMarketPct: nonNegativeOrNull(risk.singleMarketPct),
    },
  };
}

function assessCompleteness(normalized) {
  const missingFields = REQUIRED_FIELDS
    .filter(([path]) => !isProvided(getPath(normalized, path)))
    .map(([path]) => path);
  const missingLabels = REQUIRED_FIELDS
    .filter(([path]) => missingFields.includes(path))
    .map(([, label]) => label);
  const completed = REQUIRED_FIELDS.length - missingFields.length;
  const score = Math.round((completed / REQUIRED_FIELDS.length) * 100);

  return {
    score,
    completedFields: completed,
    totalFields: REQUIRED_FIELDS.length,
    missingFields,
    missingLabels,
    isSufficient: score >= 80
      && isProvided(normalized.cashflow.monthlyIncome)
      && isProvided(normalized.cashflow.essentialMonthlyExpense)
      && isProvided(normalized.assets.cash)
      && isProvided(normalized.risk.maxAcceptableLossPct),
  };
}

function identifyLifecycle(data) {
  const { household, goals } = data;
  let key = 'general';

  if (household.retired || household.incomeSourceType === 'pension') {
    key = 'retired';
  } else if (household.yearsToRetirement !== null && household.yearsToRetirement <= 5) {
    key = 'near_retirement';
  } else if (goals.homePurchaseWithinYears !== null && goals.homePurchaseWithinYears <= 3) {
    key = 'home_purchase';
  } else if (household.incomeSourceType === 'self_employed' || household.incomeStability === 'volatile') {
    key = 'self_employed_variable';
  } else if ((household.children || 0) + (household.elderlyDependents || 0) > 0
    && household.incomeSourceType === 'single_salary') {
    key = 'single_income_dependents';
  } else if ((household.children || 0) > 0
    && ['dual_salary', 'multiple'].includes(household.incomeSourceType)) {
    key = 'dual_income_parent';
  } else if ((household.adults || 0) === 1 && (household.primaryAge || 0) <= 35) {
    key = 'young_single';
  }

  return { key, ...LIFECYCLE_CONFIG[key] };
}

function deriveMetrics(data, lifecycle) {
  const { cashflow, assets, debts, goals } = data;
  const monthlyNeed = cashflow.essentialMonthlyExpense === null
    ? null
    : cashflow.essentialMonthlyExpense + (cashflow.monthlyDebtPayment || 0);
  const monthlySurplus = cashflow.monthlyIncome === null || monthlyNeed === null
    ? null
    : cashflow.monthlyIncome - monthlyNeed;
  const debtServiceRatio = cashflow.monthlyIncome === null || cashflow.monthlyIncome === 0
    ? (cashflow.monthlyDebtPayment > 0 ? 100 : 0)
    : ((cashflow.monthlyDebtPayment || 0) / cashflow.monthlyIncome) * 100;
  const liquidFinancialAssets = sumKnown([
    assets.cash,
    assets.bonds,
    assets.equities,
    assets.gold,
    assets.otherLiquid,
  ]);
  const totalAssets = liquidFinancialAssets + (assets.property || 0) + (assets.business || 0);
  const netWorth = debts.total === null ? null : totalAssets - debts.total;
  const cashCoverageMonths = monthlyNeed === null
    ? null
    : (monthlyNeed > 0 ? (assets.cash || 0) / monthlyNeed : null);
  const emergencyTarget = monthlyNeed === null ? null : monthlyNeed * lifecycle.emergencyMonths;
  const propertyConcentration = totalAssets > 0 ? ((assets.property || 0) / totalAssets) * 100 : 0;
  const businessToLiquidRatio = liquidFinancialAssets > 0
    ? ((assets.business || 0) / liquidFinancialAssets) * 100
    : ((assets.business || 0) > 0 ? 100 : 0);
  const equityRatio = liquidFinancialAssets > 0
    ? ((assets.equities || 0) / liquidFinancialAssets) * 100
    : 0;
  const shortTermExpenses = goals.expensesWithin1Year === null || goals.expenses1To3Years === null
    ? null
    : goals.expensesWithin1Year + goals.expenses1To3Years;

  return {
    monthlyNeed,
    monthlySurplus,
    debtServiceRatio: round(debtServiceRatio),
    liquidFinancialAssets,
    totalAssets,
    netWorth,
    cashCoverageMonths: round(cashCoverageMonths),
    emergencyTarget,
    propertyConcentration: round(propertyConcentration),
    businessToLiquidRatio: round(businessToLiquidRatio),
    equityRatio: round(equityRatio),
    shortTermExpenses,
  };
}

function findConstraints(data, metrics) {
  const constraints = [];
  const priorityRanks = {
    high_interest_debt: 1,
    negative_cashflow: 2,
    debt_service_overload: 3,
    emergency_reserve_critical: 4,
    protection_gap: 5,
    emergency_reserve_low: 6,
    property_concentration: 7,
    business_concentration: 8,
    market_concentration: 9,
  };
  const add = (code, severity, title) => constraints.push({
    code,
    severity,
    title,
    priorityRank: priorityRanks[code],
  });

  if (metrics.monthlySurplus !== null && metrics.monthlySurplus <= 0) {
    add('negative_cashflow', 'critical', '月度现金流无法覆盖必要支出');
  }
  if ((data.debts.highInterest || 0) > 0
    && ((data.debts.highestRate || 0) >= 8
      || data.debts.highInterest >= (data.cashflow.monthlyIncome || 0))) {
    add('high_interest_debt', 'critical', '存在需要优先处理的高息负债');
  }
  if ((metrics.debtServiceRatio || 0) >= 50) {
    add('debt_service_overload', 'critical', '月度偿债占收入比例过高');
  }
  if (metrics.cashCoverageMonths !== null
    && metrics.cashCoverageMonths < 3) {
    add('emergency_reserve_critical', 'critical', '应急资金不足三个月');
  } else if (metrics.cashCoverageMonths !== null
    && metrics.cashCoverageMonths < 6) {
    add('emergency_reserve_low', 'warning', '应急资金低于基础安全线');
  }
  if (data.protection.basicMedicalCovered === false || (data.protection.lifeCoverageGap || 0) > 0) {
    add('protection_gap', 'warning', '家庭保障存在缺口');
  }
  if (metrics.propertyConcentration >= 70) {
    add('property_concentration', 'warning', '房产占家庭总资产比例较高');
  }
  if (metrics.businessToLiquidRatio >= 50) {
    add('business_concentration', 'warning', '经营资产相对可变现金融资产较高');
  }
  if ((data.risk.largestHoldingPct || 0) >= 40 || (data.risk.singleMarketPct || 0) >= 60) {
    add('market_concentration', 'warning', '金融资产存在单一持仓或市场集中');
  }

  return constraints.sort((left, right) => left.priorityRank - right.priorityRank);
}

function assessRisk(data, metrics, constraints, completeness) {
  if (!completeness.isSufficient) {
    return {
      capacity: { level: null, label: '待补充资料' },
      willingness: { level: null, label: '待补充资料' },
      actualExposure: { level: null, label: '待补充资料', observedRiskLevel: null },
      finalLevel: null,
      finalLabel: '待评估',
      method: '三维最低值法',
    };
  }

  let capacityLevel = 3;
  if ((data.risk.investmentHorizonYears || 0) >= 10) capacityLevel += 1;
  if ((metrics.cashCoverageMonths || 0) >= 12) capacityLevel += 1;
  if (['dual_salary', 'multiple'].includes(data.household.incomeSourceType)) capacityLevel += 1;
  if (data.household.incomeStability === 'volatile' || data.household.incomeSourceType === 'self_employed') capacityLevel -= 1;
  if ((metrics.debtServiceRatio || 0) >= 30) capacityLevel -= 1;
  if (data.household.retired || data.household.incomeSourceType === 'pension') capacityLevel = Math.min(capacityLevel, 2);
  if (constraints.some(item => item.severity === 'critical')) capacityLevel = 1;
  capacityLevel = clamp(capacityLevel, 1, 5);

  const acceptedLoss = data.risk.maxAcceptableLossPct || 0;
  let willingnessLevel = acceptedLoss < 10 ? 1
    : acceptedLoss < 15 ? 2
      : acceptedLoss < 25 ? 3
        : acceptedLoss < 35 ? 4
          : 5;
  if (data.risk.marketDropReaction === 'panic_sell') willingnessLevel = 1;
  if (data.risk.marketDropReaction === 'reduce') willingnessLevel = Math.min(willingnessLevel, 2);

  const observedRiskLevel = metrics.equityRatio < 20 ? 1
    : metrics.equityRatio < 40 ? 2
      : metrics.equityRatio < 60 ? 3
        : metrics.equityRatio < 75 ? 4
          : 5;
  let exposureLevel = 5;
  if (metrics.equityRatio >= 80) exposureLevel = 2;
  else if (metrics.equityRatio >= 65) exposureLevel = 3;
  if (constraints.some(item => item.code === 'market_concentration')) exposureLevel = Math.min(exposureLevel, 2);
  if (constraints.some(item => ['property_concentration', 'business_concentration'].includes(item.code))) {
    exposureLevel = Math.min(exposureLevel, 3);
  }
  if (constraints.some(item => item.severity === 'critical')) exposureLevel = 1;

  const finalLevel = Math.min(capacityLevel, willingnessLevel, exposureLevel);
  return {
    capacity: { level: capacityLevel, label: RISK_LABELS[capacityLevel] },
    willingness: { level: willingnessLevel, label: RISK_LABELS[willingnessLevel] },
    actualExposure: {
      level: exposureLevel,
      label: RISK_LABELS[exposureLevel],
      observedRiskLevel,
      equityRatio: metrics.equityRatio,
    },
    finalLevel,
    finalLabel: RISK_LABELS[finalLevel],
    method: '三维最低值法',
  };
}

function calculateInvestable(data, metrics, lifecycle, completeness, constraints) {
  if (!completeness.isSufficient || metrics.shortTermExpenses === null || metrics.emergencyTarget === null) {
    return {
      safeUpperBound: null,
      liquidFinancialAssets: metrics.liquidFinancialAssets,
      reservedForEmergency: metrics.emergencyTarget,
      reservedForShortTermGoals: metrics.shortTermExpenses,
      reservedForHighInterestDebt: data.debts.highInterest,
      emergencyMonths: lifecycle.emergencyMonths,
      status: 'insufficient_information',
    };
  }

  const hasCashflowStop = constraints.some(item => item.code === 'negative_cashflow');
  const upperBound = hasCashflowStop ? 0 : Math.max(
    0,
    metrics.liquidFinancialAssets
      - metrics.emergencyTarget
      - metrics.shortTermExpenses
      - (data.debts.highInterest || 0)
  );

  return {
    safeUpperBound: round(upperBound, 0),
    liquidFinancialAssets: round(metrics.liquidFinancialAssets, 0),
    reservedForEmergency: round(metrics.emergencyTarget, 0),
    reservedForShortTermGoals: round(metrics.shortTermExpenses, 0),
    reservedForHighInterestDebt: round(data.debts.highInterest || 0, 0),
    emergencyMonths: lifecycle.emergencyMonths,
    status: upperBound > 0 ? 'available' : 'no_safe_surplus',
  };
}

function getAllocationRanges(risk, constraints) {
  if (risk.finalLevel === null) return null;
  const ranges = {
    1: { safety: [60, 75], stable: [15, 25], growth: [0, 10], hedge: [5, 10] },
    2: { safety: [45, 60], stable: [20, 30], growth: [10, 20], hedge: [5, 10] },
    3: { safety: [30, 45], stable: [20, 30], growth: [25, 40], hedge: [5, 10] },
    4: { safety: [20, 35], stable: [15, 25], growth: [40, 55], hedge: [5, 10] },
    5: { safety: [15, 25], stable: [10, 20], growth: [55, 70], hedge: [5, 10] },
  }[risk.finalLevel];

  const criticalDebt = constraints.some(item => [
    'high_interest_debt',
    'debt_service_overload',
    'negative_cashflow',
  ].includes(item.code));
  if (criticalDebt) ranges.growth = [0, 0];

  const format = ([min, max], label) => ({ min, max, label });
  return {
    safety: format(ranges.safety, '安全流动层'),
    stable: format(ranges.stable, '稳健收益层'),
    growth: format(ranges.growth, '长期成长层'),
    hedge: format(ranges.hedge, '风险对冲层'),
    note: '区间用于家庭大类资产规划，不构成具体产品推荐。',
  };
}

function buildStress(data, metrics, constraints) {
  if (metrics.monthlyNeed === null || metrics.monthlyNeed <= 0) {
    return {
      cashCoverageMonths: metrics.cashCoverageMonths,
      stressedCoverageMonths: null,
      status: 'insufficient_information',
      message: '补充必要支出后才能计算家庭现金流压力。',
    };
  }
  const shockPct = clamp(data.cashflow.incomeShockPct === null ? 50 : data.cashflow.incomeShockPct, 0, 100);
  const shockBurden = metrics.monthlyNeed + ((data.cashflow.monthlyIncome || 0) * shockPct / 100);
  const stressedCoverageMonths = shockBurden > 0 ? (data.assets.cash || 0) / shockBurden : null;
  const hasConcentration = constraints.some(item => item.code.includes('concentration'));
  const critical = constraints.some(item => item.severity === 'critical');
  const status = critical ? 'critical'
    : stressedCoverageMonths !== null && stressedCoverageMonths < 6 ? 'warning'
      : hasConcentration ? 'warning'
        : 'resilient';
  let message = status === 'critical'
    ? '现金流或债务红线会放大收入中断冲击，应先修复家庭安全底座。'
    : `按收入下降 ${shockPct}% 的保守情景，现金压力覆盖约 ${round(stressedCoverageMonths, 1)} 个月。`;
  if (hasConcentration) message += ' 房产、经营或市场集中会降低应急变现能力。';

  return {
    cashCoverageMonths: metrics.cashCoverageMonths,
    stressedCoverageMonths: round(stressedCoverageMonths),
    incomeShockPct: shockPct,
    status,
    message,
  };
}

function actionForConstraint(constraint, lifecycle) {
  const actions = {
    high_interest_debt: ['repay_high_interest_debt', '优先处理高息负债', '暂停新增高波动配置，制定明确的高息负债清偿顺序。'],
    negative_cashflow: ['repair_cashflow', '先修复月度现金流', '压降非必要支出或增加稳定收入，恢复持续结余后再安排长期投资。'],
    debt_service_overload: ['reduce_debt_service', '降低月度偿债压力', '优先降低月供占收入比例，避免收入中断时出现资金链风险。'],
    emergency_reserve_critical: ['build_emergency_reserve', '补足应急资金', `先建立至少 ${lifecycle.emergencyMonths} 个月必要支出的安全储备。`],
    emergency_reserve_low: ['build_emergency_reserve', '提高应急资金覆盖', `逐步将应急储备提升至 ${lifecycle.emergencyMonths} 个月必要支出。`],
    protection_gap: ['close_protection_gap', '补齐基础保障缺口', '先覆盖可能击穿家庭资产负债表的医疗和家庭责任风险。'],
    property_concentration: ['reduce_property_concentration', '降低房产集中风险', '新增结余优先补充高流动性金融资产，避免继续放大不动产集中。'],
    business_concentration: ['separate_business_assets', '隔离经营与家庭资产', '建立家庭安全资金与经营周转资金的独立边界。'],
    market_concentration: ['diversify_financial_exposure', '降低金融资产集中度', '按市场和风险来源分散长期资产，设置单一暴露上限。'],
  };
  const [code, title, detail] = actions[constraint.code] || ['review_constraint', constraint.title, '优先处理该项约束后再提高风险暴露。'];
  return { code, title, detail, priority: constraint.severity };
}

function lifecycleAction(lifecycle) {
  const actions = {
    young_single: ['set_long_term_plan', '建立长期积累计划', '在安全储备完成后，以长期目标和固定投入形成积累纪律。'],
    dual_income_parent: ['fund_rigid_goals', '隔离育儿与刚性目标资金', '把教育、医疗等确定支出与长期成长资金分开管理。'],
    single_income_dependents: ['protect_primary_income', '保护家庭主收入来源', '提高应急储备并检视主收入者责任保障。'],
    self_employed_variable: ['smooth_variable_income', '建立淡旺季现金流规则', '用较长周期估算可支配结余，隔离经营和家庭资金。'],
    home_purchase: ['isolate_home_funds', '硬隔离购房资金', '三年内确定使用的首付及税费资金不承担权益市场波动。'],
    near_retirement: ['prepare_retirement_runway', '建立退休支取跑道', '逐步准备退休初期现金与稳健资产，降低回撤顺序风险。'],
    retired: ['protect_retirement_withdrawals', '保障退休持续支取', '先验证生活、医疗和长寿情景下的现金流覆盖。'],
    general: ['clarify_family_goals', '明确家庭目标顺序', '按刚性程度和使用期限为目标排序并隔离资金。'],
  };
  const [code, title, detail] = actions[lifecycle.key];
  return { code, title, detail, priority: 'normal' };
}

function buildActions(completeness, constraints, lifecycle, risk) {
  const actions = [];
  if (!completeness.isSufficient) {
    actions.push({
      code: 'complete_information',
      title: '先补齐关键家庭资料',
      detail: `仍需补充：${completeness.missingLabels.slice(0, 4).join('、') || '关键风险信息'}。`,
      priority: 'critical',
    });
  }
  constraints.forEach(item => actions.push(actionForConstraint(item, lifecycle)));
  actions.push(lifecycleAction(lifecycle));
  if (risk.finalLevel !== null) {
    actions.push({
      code: 'align_risk_exposure',
      title: '按最低风险维度校准配置',
      detail: `风险能力、意愿与现有暴露适配度取最低值，当前建议以“${risk.finalLabel}”作为上限。`,
      priority: 'normal',
    });
  }
  actions.push({
    code: 'review_quarterly',
    title: '在家庭情况变化后复评',
    detail: '收入、负债、家庭成员或重大目标变化时重新评估，至少每季度复核一次。',
    priority: 'normal',
  });

  const unique = [];
  const seen = new Set();
  actions.forEach(action => {
    if (!seen.has(action.code)) {
      seen.add(action.code);
      unique.push(action);
    }
  });
  return unique.slice(0, 3);
}

function chooseProfile(lifecycle, constraints) {
  const highDebt = constraints.some(item => ['high_interest_debt', 'debt_service_overload'].includes(item.code));
  const cashflowPressure = constraints.some(item => ['negative_cashflow', 'emergency_reserve_critical'].includes(item.code));
  const concentrated = constraints.some(item => ['property_concentration', 'business_concentration'].includes(item.code));
  const protectionGap = constraints.some(item => item.code === 'protection_gap');
  let key = lifecycle.key;
  if (highDebt) key = 'high_debt_pressure';
  else if (cashflowPressure) key = 'cashflow_pressure';
  else if (concentrated) key = 'property_business_concentrated';
  else if (protectionGap) key = 'protection_gap';

  return {
    key,
    title: PROFILE_CONFIG[key] || lifecycle.title,
    lifecycleKey: lifecycle.key,
    constraintCodes: constraints.map(item => item.code),
  };
}

/**
 * 快速评估家庭风险与大类资产规划边界。
 *
 * 返回结果只给出家庭风险顺序和大类配置区间，不涉及具体产品。
 * 所有缺失数值保留为 null；0 被视为用户明确填写的合法数值。
 */
export function assessFamily(input = {}) {
  const normalized = normalizeInput(input);
  const completeness = assessCompleteness(normalized);
  const lifecycle = identifyLifecycle(normalized);
  const metrics = deriveMetrics(normalized, lifecycle);
  const constraints = findConstraints(normalized, metrics);
  const redLines = constraints.filter(item => item.severity === 'critical');
  const risk = assessRisk(normalized, metrics, constraints, completeness);
  const investable = calculateInvestable(
    normalized,
    metrics,
    lifecycle,
    completeness,
    constraints
  );
  const allocationRanges = getAllocationRanges(risk, constraints);
  const stress = buildStress(normalized, metrics, constraints);

  return {
    version: 1,
    normalized,
    lifecycle,
    profile: chooseProfile(lifecycle, constraints),
    completeness,
    constraints,
    redLines,
    metrics,
    risk,
    investable,
    allocationRanges,
    stress,
    topActions: buildActions(completeness, constraints, lifecycle, risk),
    disclaimer: '本结果用于家庭财务规划与风险教育，不构成具体投资产品建议。',
  };
}

export const FAMILY_ASSESSMENT_VERSION = 1;
