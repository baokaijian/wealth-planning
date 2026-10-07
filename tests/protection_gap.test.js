const test = require('node:test');
const assert = require('node:assert/strict');
const engine = require('../portfolio_engine.js');

test('保障缺口测算：双职工基准案例测算验证', () => {
  // 债务 200 万，月必要支出 1.5 万（10年 = 180万），年收入 40 万，子女教育 20 万，流动资产 30 万
  const fd = {
    'debt-house': 2000000,
    'debt-car': 0,
    'debt-consumption': 0,
    'debt-biz': 0,
    'f-essential-expense': 15000,
    'f-fixed-expense': 20000,
    'f-monthly-income': 33333.333333, // 年收入约 40 万
    'f-children': 'yes',
    'protect-child-edu': 200000,
    'protect-career-stability': 'normal', // 4 年
    'protect-rehab-reserve': 300000,
    'existing-life-insurance': 1000000,
    'existing-ci-insurance': 500000,
    'existing-accident-insurance': 500000,
    'protect-has-million-medical': false,
    'protect-coverage': 'basic'
  };

  const totalLiabilities = 2000000;
  const annualIncome = 400000;
  const liquidCash = 300000;

  const result = engine.calculateProtectionGap(fd, totalLiabilities, annualIncome, liquidCash);

  // 1. 寿险：需求 = 200万 + 180万 + 20万 - 30万 = 370万
  assert.equal(result.life.required, 3700000);
  assert.equal(result.life.existing, 1000000);
  assert.equal(result.life.gap, 2700000);
  // 倍数: 270 / 40 = 6.8 倍 (或 6.75 四舍五入到 6.8)
  assert.equal(result.life.incomeMultiple, 6.8);

  // 2. 重疾：需求 = 40万 * 4 + 30万 = 190万
  assert.equal(result.ci.required, 1900000);
  assert.equal(result.ci.existing, 500000);
  assert.equal(result.ci.gap, 1400000);
  assert.equal(result.ci.incomeMultiple, 3.5);

  // 3. 意外：需求 = 370万 * 0.5 = 185万
  assert.equal(result.accident.required, 1850000);
  assert.equal(result.accident.existing, 500000);
  assert.equal(result.accident.gap, 1350000);
  assert.equal(result.accident.incomeMultiple, 3.4);

  // 4. 医疗险兜底
  assert.equal(result.medical.hasMillionMedical, false);
  assert.ok(result.medical.warning.includes('缺少百万医疗险兜底'));

  // 5. 联动告警
  assert.equal(result.shouldAlertPriority, true);
});

test('保障缺口测算：保障充足且无缺口时取消联动警告', () => {
  const fd = {
    'debt-house': 0,
    'f-essential-expense': 5000,
    'f-fixed-expense': 6000,
    'f-children': 'no',
    'protect-career-stability': 'stable', // 3 年
    'protect-rehab-reserve': 300000,
    'existing-life-insurance': 1000000,
    'existing-ci-insurance': 2000000,
    'existing-accident-insurance': 1000000,
    'protect-has-million-medical': true,
    'protect-coverage': 'strong'
  };

  const totalLiabilities = 0;
  const annualIncome = 300000;
  const liquidCash = 1000000;

  const result = engine.calculateProtectionGap(fd, totalLiabilities, annualIncome, liquidCash);
  // 10年生活费 60万 - 流动资产 100万 => 寿险需求为 0
  assert.equal(result.life.required, 0);
  assert.equal(result.life.gap, 0);

  // 重疾需求 = 30万 * 3 + 30万 = 120万；已有 200万 => 净缺口 0
  assert.equal(result.ci.required, 1200000);
  assert.equal(result.ci.gap, 0);

  assert.equal(result.accident.gap, 0);
  assert.equal(result.medical.hasMillionMedical, true);
  assert.equal(result.shouldAlertPriority, false);
});

test('保障缺口测算：空白可选项使用业务默认值，明确的 0 仍被保留', () => {
  const blankDefaults = engine.calculateProtectionGap({
    'f-essential-expense': 0,
    'f-fixed-expense': 0,
    'f-children': 'yes',
    'f-stability': 'volatile',
    'protect-child-edu': '',
    'protect-rehab-reserve': '',
    'protect-has-million-medical': true,
    'protect-coverage': 'strong'
  }, 0, 100000, 0);

  assert.equal(blankDefaults.life.components.childEduReserve, 200000);
  assert.equal(blankDefaults.ci.rehabReserve, 300000);
  assert.equal(blankDefaults.ci.incomeYears, 5);

  const explicitZero = engine.calculateProtectionGap({
    'f-essential-expense': 0,
    'f-fixed-expense': 0,
    'f-children': 'yes',
    'f-stability': 'normal',
    'protect-child-edu': 0,
    'protect-rehab-reserve': 0,
    'protect-has-million-medical': true,
    'protect-coverage': 'strong'
  }, 0, 100000, 0);

  assert.equal(explicitZero.life.components.childEduReserve, 0);
  assert.equal(explicitZero.ci.rehabReserve, 0);
});
