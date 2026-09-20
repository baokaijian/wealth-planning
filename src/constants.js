// src/constants.js

// 默认资产配置池（科学三桶结构：安全防御 30% / 长期成长 55% / 综合对冲 15%）
export const DEFAULT_ASSETS = {
  // 安全防御桶 (30%)
  '511880': {
    name: '银华日利货币 ETF',
    type: 'ETF',
    weight: 15.0,
    yield: 1.8,
    months: { 1: 0.083, 2: 0.083, 3: 0.083, 4: 0.083, 5: 0.083, 6: 0.083, 7: 0.083, 8: 0.083, 9: 0.083, 10: 0.083, 11: 0.083, 12: 0.083 },
    market: 'A股',
    category: 'Cash',
    style: '现金货币',
    bucket: 'safety'
  },
  '511360': {
    name: '短融 ETF',
    type: 'ETF',
    weight: 15.0,
    yield: 2.7,
    months: { 3: 0.25, 6: 0.25, 9: 0.25, 12: 0.25 },
    market: 'A股',
    category: 'FixedIncome',
    style: '防守固收',
    bucket: 'safety'
  },
  // 长期成长 / 红利核心桶 (55%)
  '512890': {
    name: '中证红利低波 ETF',
    type: 'ETF',
    weight: 20.0,
    yield: 4.5,
    months: { 7: 0.5, 12: 0.5 },
    market: 'A股',
    category: 'Equity',
    style: '红利低波',
    bucket: 'growth',
    targetIndexCode: 'H30269'
  },
  '515450': {
    name: '标普大盘红利低波 ETF',
    type: 'ETF',
    weight: 15.0,
    yield: 4.2,
    months: { 7: 1.0 },
    market: 'A股',
    category: 'Equity',
    style: '红利低波',
    bucket: 'growth',
    targetIndexCode: 'H30269'
  },
  '513530': {
    name: '恒生红利低波 ETF',
    type: 'ETF',
    weight: 10.0,
    yield: 4.8,
    months: { 7: 0.5, 12: 0.5 },
    market: '港股',
    category: 'Equity',
    style: '红利低波',
    bucket: 'growth',
    targetIndexCode: 'HSHYLV'
  },
  '510300': {
    name: '沪深300 ETF',
    type: 'ETF',
    weight: 10.0,
    yield: 1.5,
    months: { 10: 1.0 },
    market: 'A股',
    category: 'Equity',
    style: '核心宽基',
    bucket: 'growth',
    targetIndexCode: '000300'
  },
  // 综合对冲桶 (15%)
  '518880': {
    name: '黄金 ETF',
    type: 'ETF',
    weight: 7.0,
    yield: 0.0,
    months: {},
    market: 'A股',
    category: 'Gold',
    style: '贵金属对冲',
    bucket: 'hedge',
    targetIndexCode: 'AU9999'
  },
  '511010': {
    name: '国债 ETF (10年/30年)',
    type: 'ETF',
    weight: 8.0,
    yield: 2.2,
    months: { 6: 0.5, 12: 0.5 },
    market: 'A股',
    category: 'FixedIncome',
    style: '利率长债',
    bucket: 'hedge',
    targetIndexCode: '000012'
  }
};

// 目标类型与优先级
export const GOAL_TYPES = [
  '子女教育金',
  '养老储备',
  '买房首付',
  '提前退休',
  '自定义'
];

export const GOAL_PRIORITIES = [
  '刚性',
  '弹性'
];

// 综合贷款利率档位定义与中值
export const DEBT_RATE_BRACKETS = {
  '<3.5%': {
    label: '<3.5% (公积金/超低息贷款)',
    median: 3.0,
    description: '通常为公积金贷款或极低息政策性贷款'
  },
  '3.5-4.5%': {
    label: '3.5-4.5% (主流商业房贷/优质消费贷)',
    median: 4.0,
    description: '当前大部分一线与核心二线城市首套房房贷主流利率'
  },
  '4.5-6%': {
    label: '4.5-6% (早期存量商贷/一般信用贷)',
    median: 5.25,
    description: '较早年份发放的房贷未下调利率或一般银行消费信用贷'
  },
  '>6%': {
    label: '>6% (高息网贷/信用卡分期/经营贷)',
    median: 7.2,
    description: '信用卡账单分期、借呗微粒贷等高息信用债务'
  }
};

// 保障需求：行业稳定性系数
export const INSURANCE_STABILITY_CONFIG = {
  high: {
    years: 3,
    medical: 300000,
    label: '高稳定 (体制内/大型垄断国企)'
  },
  medium: {
    years: 4,
    medical: 400000,
    label: '中等稳定 (成熟实业/常规外企)'
  },
  low: {
    years: 5,
    medical: 500000,
    label: '波动大 (互联网/金融初创/提成销售)'
  }
};

// 商业保险覆盖自评档位
export const INSURANCE_COVERAGE_TIERS = [
  { id: 'none', label: '极低/空白 (仅基本医保或无商业险)' },
  { id: 'insufficient', label: '基础不足 (仅少量单位团险或低保额意外险)' },
  { id: 'moderate', label: '基本齐备 (常规寿险/重疾险但保额一般)' },
  { id: 'complete', label: '充足全面 (高额寿险+重疾+百万医疗兜底)' }
];

// 个人养老金相关常量
export const PENSION_ANNUAL_MAX = 12000;
export const PENSION_TAX_BRACKETS = [
  { rate: 0.0, label: '不达起征点 (0%)' },
  { rate: 0.03, label: '3% (年应税所得 ≤ 3.6万)' },
  { rate: 0.10, label: '10% (3.6万 - 14.4万)' },
  { rate: 0.20, label: '20% (14.4万 - 30万)' },
  { rate: 0.25, label: '25% (30万 - 42万)' },
  { rate: 0.30, label: '30% (42万 - 66万)' },
  { rate: 0.35, label: '35% (66万 - 96万)' },
  { rate: 0.45, label: '45% (年应税所得 > 96万)' }
];

// 房产集中度预警阈值
export const PROPERTY_THRESHOLDS = {
  greenMax: 0.60,
  yellowMax: 0.75,
  defaultStressDropPct: 20
};

// 复合压力测试预设情景
export const STRESS_PRESETS = {
  standard: {
    id: 'standard',
    name: '标准复合情景',
    description: '失业 6 个月 + 组合分红降 30% + 权益市值同步回撤 20%',
    unemploymentMonths: 6,
    dividendDropRate: 0.30,
    equityDrawdownRate: 0.20,
    medicalExpense: 0,
    medicalMonth: 0,
    delayMonths: 0,
    inflationRate: 0.0
  },
  severe: {
    id: 'severe',
    name: '严重复合情景',
    description: '失业 12 个月 + 组合分红降 50% + 权益市值回撤 35% + 第 6 个月突发一次性医疗 20 万元',
    unemploymentMonths: 12,
    dividendDropRate: 0.50,
    equityDrawdownRate: 0.35,
    medicalExpense: 200000,
    medicalMonth: 6,
    delayMonths: 0,
    inflationRate: 0.0
  },
  stagflation: {
    id: 'stagflation',
    name: '滞胀情景',
    description: '年通胀 5% (刚性生活支出逐月递增) + 分红延迟 4 个月到账 + 分红永久下降 20%',
    unemploymentMonths: 0,
    dividendDropRate: 0.20,
    equityDrawdownRate: 0.15,
    medicalExpense: 0,
    medicalMonth: 0,
    delayMonths: 4,
    inflationRate: 0.05
  }
};

// 历史极端周期回放预设（逐月回撤与分红系数）
export const HISTORICAL_REPLAYS = {
  replay_2018: {
    id: 'replay_2018',
    name: '2018 式阴跌回放',
    description: '宏观去杠杆与外部冲击，12 个月逐月阴跌累计回撤 25%，分红保持平稳发放。',
    monthlyDrawdown: [-0.02, -0.04, -0.07, -0.09, -0.12, -0.15, -0.18, -0.20, -0.22, -0.23, -0.24, -0.25],
    dividendFactor: 1.0
  },
  replay_2022: {
    id: 'replay_2022',
    name: '2022 式股债双杀回放',
    description: '全球加息周期与流动性收紧，权益回撤 20%，债券资产阶段回调 3%，分红下调 10%。',
    monthlyDrawdown: [-0.05, -0.08, -0.12, -0.16, -0.18, -0.20, -0.19, -0.18, -0.20, -0.20, -0.18, -0.18],
    dividendFactor: 0.90
  },
  replay_2015: {
    id: 'replay_2015',
    name: '2015 式急跌回放',
    description: '杠杆资金踩踏出清，前 3 个月急速暴跌 40%，随后低位宽幅剧烈震荡。',
    monthlyDrawdown: [-0.15, -0.32, -0.40, -0.38, -0.39, -0.37, -0.38, -0.36, -0.36, -0.35, -0.36, -0.35],
    dividendFactor: 0.95
  }
};

// 行为约束引擎：回撤档位映射基础上限与扣减规则
export const BEHAVIOR_DRAWDOWN_MAP = {
  '<5%': 20,
  '5-10%': 35,
  '10-20%': 55,
  '20-30%': 70,
  '>30%': 85
};

export const BEHAVIOR_RULES = {
  panicReactionDeduction: {
    'panic_sell': 15,
    'pause_watch': 5,
    'buy_more': 0
  },
  cashflowRelianceDeduction: 10,
  industryVolatileDeduction: 10,
  floorProtection: 15,
  extremeEquityDrawdown: 0.40
};

// 10大代表性指数监测列表
export const THERMOMETER_INDICES = [
  { code: 'H30269', name: '中证红利低波', type: 'dividend', metricName: '股息率近三年百分位', defaultPercentile: 72, dividendYield: 4.85, pe: 6.2, desc: '偏重金融煤炭交运，红利低波核心表征' },
  { code: '000015', name: '上证红利', type: 'dividend', metricName: '股息率近三年百分位', defaultPercentile: 65, dividendYield: 5.12, pe: 5.8, desc: '上交所传统成熟高分红蓝筹' },
  { code: '932039', name: '央企股东回报', type: 'dividend', metricName: '股息率近三年百分位', defaultPercentile: 58, dividendYield: 4.30, pe: 7.1, desc: '央企分红与回购质量评估' },
  { code: 'HSHYLV', name: '港股通高股息低波', type: 'dividend', metricName: '股息率近三年百分位', defaultPercentile: 78, dividendYield: 6.40, pe: 5.2, desc: '港股离岸高股息，考虑税后现金流' },
  { code: '000300', name: '沪深300', type: 'broad', metricName: '综合PE/PB估值百分位', defaultPercentile: 32, dividendYield: 2.85, pe: 11.8, desc: 'A股核心大盘蓝筹基准' },
  { code: '000510', name: '中证A500', type: 'broad', metricName: '综合PE/PB估值百分位', defaultPercentile: 35, dividendYield: 2.70, pe: 13.2, desc: '新一代均衡型宽基旗舰' },
  { code: '000905', name: '中证500', type: 'broad', metricName: '综合PE/PB估值百分位', defaultPercentile: 26, dividendYield: 1.95, pe: 22.4, desc: '中盘成长弹性与制造龙头' },
  { code: '000688', name: '科创50', type: 'growth', metricName: 'PE/PS估值百分位', defaultPercentile: 18, dividendYield: 0.60, pe: 42.0, desc: '硬科技硬核成长核心板块' },
  { code: 'SPX', name: '标普500', type: 'global', metricName: 'PE估值历史百分位', defaultPercentile: 86, dividendYield: 1.45, pe: 26.5, desc: '美股成熟大盘综合指数' },
  { code: 'NDX', name: '纳斯达克100', type: 'global', metricName: 'PE估值历史百分位', defaultPercentile: 88, dividendYield: 0.75, pe: 31.0, desc: '全球科技创新巨头指数' }
];

// 估值温度计五档区间与纪律导向
export const THERMOMETER_TIERS = [
  { min: 0, max: 20, code: 'deep_low', label: '深度低估', color: '#10B981', action: '定投倍数放大至 1.5-2.0x；若缓冲池储备超额，可将盈余资金适度转入' },
  { min: 20, max: 40, code: 'low', label: '低估', color: '#34D399', action: '按 1.2x 步长积极定投建仓，持续累积低成本份额' },
  { min: 40, max: 60, code: 'neutral', label: '中性平衡', color: '#38BDF8', action: '估值处于合理中枢，保持既定配置目标权重，常规基准定投' },
  { min: 60, max: 80, code: 'warm', label: '偏热', color: '#FBBF24', action: '停止增量资金加仓，将新增可结余资金导向现金缓冲池或债券防守桶' },
  { min: 80, max: 100, code: 'overheat', label: '极度过热', color: '#F87171', action: '启动卖出侧纪律：建议按月度 3 次分批将成长类持仓再平衡回目标权重' }
];

// 流动性硬隔离折扣与覆盖率参数
export const LIQUIDITY_DISCOUNT_FACTOR = 0.5; // 1-3年资金50%折减
export const LIQUIDITY_SAFE_COVERAGE_RATIO = 1.5; // 应急资金安全倍数底线

// 集中度限制
export const CONCENTRATION_LIMITS = {
  singleAssetYellow: 40, // 单一标的黄灯
  top3AssetsRed: 70, // 前三标的红灯
  marketCurrencyAlert: 60, // 单一市场/板块预警
  dividendStyleClusterAlert: 50 // 红利低波风格共振预警
};

// 初始自洽示范数据
export const INITIAL_STATE = {
  board: {
    principal: 80.0, // 80 万元总本金
    bufferSeed: 10.0, // 10 万元缓冲池初始种子金
    targetMonthly: 1.2, // 1.2 万元/月 (对齐月必要生活支出 12,000 元)
    growthRate: 6.5,
    moneyMarketRate: 2.0,
    assets: DEFAULT_ASSETS
  },
  health: {
    // 收支
    monthlyIncome: 30000,
    monthlyExpense: 18000,
    essentialMonthlyExpense: 12000,
    monthlySurplus: 12000,
    // 基础信息与收入结构
    incomeSourceCount: 'dual', // 'single' | 'dual' | 'multiple'
    unemploymentRecoveryMonths: 6, // 预期失业恢复月数
    unemploymentReplacementRate: 0.3, // 失业期替代收入比例 30%
    // A组：资金分层资产
    assetsBreakdown: {
      cashCurrent: 100000, // 现金活期 10万
      cashShortDebt: 200000, // 货基短债 20万
      equityAssets: 440000, // 权益类资产 44万 (80万*55%)
      goldAssets: 56000, // 黄金资产 5.6万 (80万*7%)
      bondAssets: 184000, // 债券资产 18.4万
      propertyEstimated: 2800000, // 房产估值 280万
      pensionCashValue: 20000, // 养老金现值 2万
      otherAssets: 0
    },
    // B组：未来确定性支出
    expectedExpenses: {
      expense1y: 100000, // 12个月内大额支出 10万
      expense1To3y: 150000, // 1-3年大额支出 15万
      expense3To5y: 100000 // 3-5年大额支出 10万
    },
    hasHousePlan: false,
    expectedDownPayment: 600000
  },
  insurance: {
    coverageTier: 'insufficient',
    stabilityTier: 'medium',
    childEduTarget: 500000, // 子女教育金目标独立输入 50万
    existingLifeCover: 500000,
    existingCritCover: 200000,
    existingAccidentCover: 500000,
    hasMillionMedical: false
  },
  debt: {
    mortgageBalance: 800000,
    carLoanBalance: 0,
    consumerLoanBalance: 0,
    businessLoanBalance: 0,
    monthlyDebtPayment: 4500,
    remainingYears: 15,
    debtRateBracket: '3.5-4.5%',
    customDebtRate: null,
    useCustomRate: false,
    highInterestDebtBalance: 0,
    availableFundX: 200000
  },
  pension: {
    hasAccount: true,
    currentYearDeposited: 4000,
    marginalTaxRate: 0.20
  },
  property: {
    totalEstimatedValue: 2800000,
    stressDropPct: 20
  },
  stress: {
    scenarioType: 'preset',
    selectedPresetId: 'standard',
    selectedReplayId: 'replay_2018',
    customDrawdown: null,
    unemploymentReplacementRate: 0.3
  },
  behavior: {
    drawdownBracket: '10-20%',
    marketDropReaction: 'panic_sell',
    cashflowRelianceHigh: true,
    industryVolatileHigh: false
  },
  thermometer: {
    selectedIndex: 'H30269',
    percentileOverrides: {},
    dataSource: 'cached',
    userHoldings: {
      '511880': 12.0,
      '511360': 12.0,
      '512890': 16.0,
      '515450': 12.0,
      '513530': 8.0,
      '510300': 8.0,
      '518880': 6.0,
      '511010': 6.0
    },
    incrementalCapital: 50000
  },
  goals: [
    {
      id: 'goal-edu-2035',
      name: '2035 年子女教育金',
      type: '子女教育金',
      targetAmount: 1000000,
      targetYear: 2035,
      priority: '刚性',
      reservedAmount: 0,
      linkTo1To3y: false,
      retireConfig: { currentAge: 35, retireAge: 50, retireMonthlyExpense: 10000 }
    },
    {
      id: 'goal-fire-2040',
      name: '2040 提前退休计划',
      type: '提前退休',
      targetAmount: 2500000,
      targetYear: 2040,
      priority: '弹性',
      reservedAmount: 150000,
      linkTo1To3y: true,
      retireConfig: { currentAge: 35, retireAge: 50, retireMonthlyExpense: 12000 }
    }
  ]
};

export const DISCLAIMER_TEXT = "免责声明：所有财务推演与量化模型均基于用户输入的数据及假设性收益率，不代表任何历史业绩保证或未来投资收益承诺，不构成具体金融产品推荐。市场有风险，投资决策需审慎。";
