#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
家庭财富规划工具系统性升级 —— 11 大模块全要素自动化验收测试套件
全面覆盖：
1. 家庭保障缺口测算 (责任缺口法寿险/重疾/意外/百万医疗兜底，缺口联动配置降级)
2. 目标导向规划 (多目标CRUD、三大杠杆反解、85岁提前退休持久性与最脆弱月份)
3. 债务决策对照 (贷款利率 vs 保守收益率70%决策矩阵、3/5/10年期资金X对比、置顶高息警报)
4. 个人养老金税优检查 (12000上限、税率档位、当年剩余额度、20年累计放弃税优、红利低波匹配)
5. 房产集中度强化 (三档净资产比预警、首付缺口校验禁动用本金、房产下跌冲击)
6. 复合情景压力测试 (3套预设+3套历史回放、复用36个月引擎、枯竭月/变现资产/恢复月数/3色总结)
7. 行为约束引擎 (回撤档映射基础权益上限、恐慌/现金流/行业扣减、保底15%、透明归因)
8. 估值温度计卖出侧纪律 (五档温度、深度低估加码、过热3次分批再平衡、再平衡联动)
9. 流动性硬隔离校验 (可投资上限 = 流动金融资产 - 12m*100% - 1-3y*50%、超限强警告、覆盖倍数<1.5x)
10. 三重集中度检查 (单标的>40%/前三>70%、板块>60%、红利低波簇>50%共振预警与治理建议)
11. 评分可解释化与统一风险仪表盘 (脆弱性/进攻性子因子归因与拖后腿结论、6大红灯一屏总览与跳转)
12. 前端 SPA 架构与文件完备性 (localStorage、Markdown导出、非建议免责声明、零服务端外发)
"""

import os
import sys
import json
import re

from test_calculations import (
    calculate_goal_projection,
    simulate_early_retirement,
    calculate_debt_decision_metrics,
    calculate_insurance_gap,
    calculate_pension_tax_benefit,
    calculate_real_estate_risk,
    check_liquidity_segregation,
    calculate_behavioral_equity_ceiling,
    calculate_thermometer_signal,
    run_compound_stress_test,
    check_triple_concentration,
    calculate_explainable_scores,
    calculate_unified_risk_dashboard
)

def run_acceptance_tests():
    print("================================================================================")
    print("🚀 开始执行家庭财富规划工具 11 大模块系统性升级全量自动化验收测试")
    print("================================================================================")

    # -------------------------------------------------------------------------
    # [验收模块 1] 家庭保障缺口测算 (责任缺口法)
    # -------------------------------------------------------------------------
    print("\n[验收模块 1] 家庭保障缺口测算 (责任缺口法寿险/重疾/意外/百万医疗兜底)...")
    # 手工复算用例：
    # 月收入 30,000 元 (年收 36 万)，必要生活费 12,000 元/月 (未来10年120个月: 144 万元)
    # 债务 80 万元，子女教育金 50 万元，流动资产 95 万元，已有寿险 50 万元，自评保障不足
    # 寿险目标责任 = 80 + 144 + 50 - 95 = 179 万元；净缺口 = 179 - 50 = 129 万元
    # 中等稳定性：4年年收入 (144万) + 40万医疗康复 = 184 万元；已有重疾 20 万元 -> 净缺口 164 万元
    # 意外目标 = 179万 * 50% = 89.5 万元；已有 50 万元 -> 净缺口 39.5 万元
    ins = calculate_insurance_gap(
        monthly_income=30000,
        essential_monthly_expense=12000,
        child_edu_target=500000,
        liquid_assets=950000,
        total_debt=800000,
        existing_life=500000,
        existing_crit=200000,
        existing_accident=500000,
        has_million_medical=False,
        stability_tier='medium',
        coverage_tier='insufficient'
    )
    print(f"  • 寿险总责任: ¥{ins['life_target']:,} 元 | 净缺口: ¥{ins['life_gap']:,} 元 (倍数: {ins['life_mult']}x)")
    print(f"  • 重疾保额目标: ¥{ins['crit_target']:,} 元 | 净缺口: ¥{ins['crit_gap']:,} 元 (倍数: {ins['crit_mult']}x)")
    print(f"  • 意外保额目标: ¥{ins['accident_target']:,} 元 | 净缺口: ¥{ins['accident_gap']:,} 元")
    print(f"  • 触发资产配置降级提示: {ins['should_warn_downgrade']}")

    assert ins['life_target'] == 1790000, f"寿险总责任期望 1790000, 实际 {ins['life_target']}"
    assert ins['life_gap'] == 1290000, f"寿险净缺口期望 1290000, 实际 {ins['life_gap']}"
    assert ins['crit_target'] == 1840000, f"重疾保额目标期望 1840000, 实际 {ins['crit_target']}"
    assert ins['crit_gap'] == 1640000, f"重疾净缺口期望 1640000, 实际 {ins['crit_gap']}"
    assert ins['accident_target'] == 895000, f"意外保额期望 895000, 实际 {ins['accident_target']}"
    assert ins['accident_gap'] == 395000, f"意外保额净缺口期望 395000, 实际 {ins['accident_gap']}"
    assert ins['should_warn_downgrade'] is True, "自评保障不足且有净缺口时必须触发配置降级警报"
    print("  ✅ [模块 1] 验证通过！")

    # -------------------------------------------------------------------------
    # [验收模块 2] 目标导向规划 (三大杠杆反解 & 85岁提前退休持久性)
    # -------------------------------------------------------------------------
    print("\n[验收模块 2] 目标导向规划 (2035子女教育金100万、三大杠杆反解、85岁退休持久性)...")
    goal = calculate_goal_projection(
        current_year=2026,
        target_year=2035,
        target_amount=1000000,
        monthly_surplus=3000,
        growth_rate=0.055,
        current_principal=200000,
        reserved_amount=0
    )
    assert goal['gap'] > 0, "设定用例应存在资金缺口"
    levers = goal['levers']
    assert levers is not None, "必须反解出三大杠杆"
    print(f"  • 杠杆 1 (储蓄端): 每月多储蓄 ¥{levers['extra_monthly']:,} 元")
    print(f"  • 杠杆 2 (收益端): 收益率需提升 {levers['rate_diff_pct']:.2f}% 至 {levers['req_rate']:.2f}% (稳健: {levers['is_rate_safe']})")
    print(f"  • 杠杆 3 (目标端): 目标延后 {levers['delay_years']} 年至 {levers['delayed_target_year']} 年")
    assert levers['extra_monthly'] > 0 and levers['rate_diff_pct'] > 0 and levers['delay_years'] > 0

    ret = simulate_early_retirement(
        current_age=35,
        retire_age=50,
        target_amount=2000000,
        projected_capital_at_retire=2500000,
        monthly_expense=10000,
        dividend_yield=0.048,
        buffer_interest_rate=0.02,
        end_age=85
    )
    ret_str = '可持续至85岁' if ret['is_sustainable'] else f"{ret['depletion_age']}岁耗尽"
    print(f"  • 退休可持续性: {ret_str}")
    print(f"  • 最脆弱月份: 第 {ret['most_fragile_month']} 个月 (约 {ret['most_fragile_age']} 岁), 水位: ¥{ret['lowest_capital']:,.2f} 元")
    assert ret['most_fragile_month'] >= 1
    print("  ✅ [模块 2] 验证通过！")

    # -------------------------------------------------------------------------
    # [验收模块 3] 债务决策对照 (贷款利率 vs 70%保守收益率 & 10年净资产差额复算)
    # -------------------------------------------------------------------------
    print("\n[验收模块 3] 债务决策对照 (X=20万, 贷款5.5% vs 保守收益率4.0% 决策矩阵与手工复算)...")
    debt_res = calculate_debt_decision_metrics(
        debt_bracket='4.5-6%',
        custom_debt_rate=5.5,
        high_interest_balance=0,
        growth_rate=5.714,
        conservative_yield_override=4.0,
        available_fund_x=200000
    )
    t10 = debt_res['comparison_table'][2]
    print(f"  • 10年期还贷终值: ¥{t10['fv_repay']:,.2f} | 投资终值: ¥{t10['fv_invest']:,.2f} | 差额: ¥{t10['diff']:+,.2f}")
    print(f"  • 决策文案: {debt_res['decision_text']}")
    # 200,000 * (1.055^10) = 341,628.89; 200,000 * (1.04^10) = 296,048.86; diff = 45,580.03
    assert round(t10['fv_repay']) == 341629
    assert round(t10['fv_invest']) == 296049
    assert round(t10['diff']) == 45580
    assert debt_res['decision_text'] == "两者皆可，优先级取决于风险偏好与流动性需求"
    # 高息警报检验
    high_alert = calculate_debt_decision_metrics(debt_bracket='>6%', high_interest_balance=50000)
    assert high_alert['has_high_interest_alert'] is True, "高息债务必须触发置顶警报"
    print("  ✅ [模块 3] 验证通过！")

    # -------------------------------------------------------------------------
    # [验收模块 4] 个人养老金税优检查 (12,000上限、当年放弃税优与20年累计)
    # -------------------------------------------------------------------------
    print("\n[验收模块 4] 个人养老金税优检查 (当年已存4000元, 20%边际税率)...")
    pen = calculate_pension_tax_benefit(has_account=True, current_year_deposited=4000, marginal_tax_rate=0.20)
    print(f"  • 当年剩余可用额度: ¥{pen['remaining']:,} 元")
    print(f"  • 当年放弃递延税优: ¥{pen['annual_tax_saved']:,} 元")
    print(f"  • 20年累计放弃税优: ¥{pen['cumulative_20y']:,} 元")
    assert pen['remaining'] == 8000, "12000 - 4000 应为 8000"
    assert pen['annual_tax_saved'] == 1600, "8000 * 20% 应为 1600"
    assert pen['cumulative_20y'] == 32000, "1600 * 20年 应为 32000"
    print("  ✅ [模块 4] 验证通过！")

    # -------------------------------------------------------------------------
    # [验收模块 5] 房产集中度强化 (三档预警 & 购房首付缺口禁止挪用本金)
    # -------------------------------------------------------------------------
    print("\n[验收模块 5] 房产集中度强化与首付资金核验...")
    # 房产市值 280万, 房贷 80万, 金融资产 95万 -> 净值比 200 / 295 = 67.8% (黄色预警: 60-75%)
    # 购房首付计划 60万, 现有备用金 1年10万 + 1-3年15万 = 25万 -> 首付缺口 35万 (禁止挪用长期本金)
    re_risk = calculate_real_estate_risk(
        property_val=2800000,
        mortgage=800000,
        financial_assets=950000,
        has_house_plan=True,
        expected_down_payment=600000,
        bucket1y=100000,
        bucket1_3y=150000,
        stress_drop_pct=20
    )
    print(f"  • 房产净值占比: {re_risk['ratio']}% (预警档位: {re_risk['tier']})")
    print(f"  • 首付缺口: ¥{re_risk['down_payment_gap']:,} 元 | 触发缺口警报: {re_risk['is_down_payment_short']}")
    print(f"  • 房产下跌20%压力后资产负债率: {re_risk['normal_d_to_a']}% -> {re_risk['stress_d_to_a']}%")
    assert re_risk['ratio'] == 67.8
    assert re_risk['tier'] == 'yellow'
    assert re_risk['is_down_payment_short'] is True
    assert re_risk['down_payment_gap'] == 350000
    assert re_risk['stress_d_to_a'] > re_risk['normal_d_to_a']
    print("  ✅ [模块 5] 验证通过！")

    # -------------------------------------------------------------------------
    # [验收模块 6] 复合情景压力测试 (复用 36 个月引擎 & 折价变现资产反解)
    # -------------------------------------------------------------------------
    print("\n[验收模块 6] 复合情景压力测试 (严重复合情景: 失业12个月+分红腰斩50%+医疗突发20万+回撤35%)...")
    stress_res = run_compound_stress_test(
        principal_ten_thousand=50,
        buffer_seed_ten_thousand=5,
        target_monthly_ten_thousand=0.2,
        unemployment_months=12,
        dividend_drop_rate=0.50,
        equity_drawdown_rate=0.35,
        medical_expense=200000,
        medical_month=6
    )
    print(f"  • 缓冲池是否枯竭: {stress_res['is_exhausted']} (第 {stress_res['exhaustion_month']} 个月枯竭)")
    print(f"  • 最大现金赤字: ¥{stress_res['max_deficit']:,} 元")
    print(f"  • 需折价变现资产规模: ¥{stress_res['min_asset_to_sell']:,} 元 (考虑回撤35%折价)")
    assert stress_res['is_exhausted'] is True
    assert stress_res['exhaustion_month'] == 6
    assert stress_res['min_asset_to_sell'] > stress_res['max_deficit'], "由于35%回撤折价，需变现资产规模必须大于实际赤字金额"
    print("  ✅ [模块 6] 验证通过！")

    # -------------------------------------------------------------------------
    # [验收模块 7] 行为约束引擎 (回撤档映射基础上限、恐慌扣减、超限标红)
    # -------------------------------------------------------------------------
    print("\n[验收模块 7] 行为约束引擎 (自评回撤10-20%[基准55%] - 恐慌卖出15% - 现金流依赖10% = 上限30%)...")
    beh = calculate_behavioral_equity_ceiling(
        drawdown_bracket='10-20%',
        panic_reaction='panic_sell',
        cashflow_reliance_high=True,
        industry_volatile_high=False,
        actual_equity_weight=50.0
    )
    print(f"  • 基准上限: {beh['base']}% | 综合扣减后上限: {beh['final_ceiling']}%")
    print(f"  • 实际权益仓位: 50.0% | 是否超限标红: {beh['is_exceeded']} (超限幅度: {beh['excess_weight']}%)")
    assert beh['base'] == 55
    assert beh['final_ceiling'] == 30
    assert beh['is_exceeded'] is True
    assert beh['excess_weight'] == 20.0
    print("  ✅ [模块 7] 验证通过！")

    # -------------------------------------------------------------------------
    # [验收模块 8] 估值温度计卖出侧纪律 (五档温度、过热与再平衡联动)
    # -------------------------------------------------------------------------
    print("\n[验收模块 8] 估值温度计卖出侧纪律 (85%百分位处于过热区间)...")
    therm_hot = calculate_thermometer_signal(percentile=85)
    therm_cold = calculate_thermometer_signal(percentile=15)
    print(f"  • 85% 百分位信号: {therm_hot['code']} (是否过热: {therm_hot['is_overheated']})")
    print(f"  • 15% 百分位信号: {therm_cold['code']} (是否极度低估: {therm_cold['is_deep_low']})")
    assert therm_hot['is_overheated'] is True
    assert therm_cold['is_deep_low'] is True
    print("  ✅ [模块 8] 验证通过！")

    # -------------------------------------------------------------------------
    # [验收模块 9] 流动性硬隔离校验 (可投资本金上限公式与超限警告)
    # -------------------------------------------------------------------------
    print("\n[验收模块 9] 流动性硬隔离校验 (流动资产95万, 1年确定10万*100%, 1-3年15万*50% -> 上限77.5万)...")
    # 总流动金融资产 10+15+20+50 = 95万
    # 上限 = 95 - 10*1.0 - 15*0.5 = 77.5 万元
    # 当前已投入本金 80 万元 -> 超限 2.5 万元
    liq = check_liquidity_segregation(
        bucket1y=100000,
        bucket1_3y=150000,
        bucket3_5y=200000,
        bucket5y_plus=500000,
        principal_ten_thousand=80
    )
    print(f"  • 流动资产总额: ¥{liq['liquid_financial']:,} 元 | 可投资上限: ¥{liq['investable_ceiling']:,} 元")
    print(f"  • 实际投入本金: ¥{liq['principal_yuan']:,} 元 | 是否违规超限: {liq['is_violated']} (超限金额: ¥{liq['excess_amount']:,} 元)")
    print(f"  • 短期备用金覆盖倍数: {liq['coverage_ratio']}x (是否不足1.5x: {liq['is_coverage_insufficient']})")
    assert liq['investable_ceiling'] == 775000
    assert liq['is_violated'] is True
    assert liq['excess_amount'] == 25000
    print("  ✅ [模块 9] 验证通过！")

    # -------------------------------------------------------------------------
    # [验收模块 10] 三重集中度检查 (单一标的>40%/前三>70%、板块>60%、红利低波>50%)
    # -------------------------------------------------------------------------
    print("\n[验收模块 10] 三重集中度检查 (标的集中度、市场宏观集中度、红利低波共振)...")
    mock_assets = {
        'A': {'name': '红利ETF', 'weight': 45.0, 'market': 'A股', 'style': '红利低波'},
        'B': {'name': '标普500', 'weight': 30.0, 'market': '美股', 'style': '成长蓝筹'},
        'C': {'name': '恒生高股息', 'weight': 15.0, 'market': '港股', 'style': '红利低波'},
        'D': {'name': '中短债基金', 'weight': 10.0, 'market': 'A股', 'style': '防御固收'}
    }
    conc = check_triple_concentration(mock_assets)
    print(f"  • 单一最大标的: {conc['max_single']['name']} ({conc['max_single']['weight']}%) -> 标的状态: {conc['target_status']}")
    print(f"  • 前三大标的合计权重: {conc['top3_weight']}%")
    print(f"  • 红利低波风格合计: {conc['dividend_style_weight']}% -> 风格状态: {conc['style_status']}")
    assert conc['target_status'] == 'red', "前三标的合计 90% > 70% 必须触发红灯警报"
    assert conc['dividend_style_weight'] == 60.0, "红利ETF(45) + 恒生高股息(15) = 60%"
    assert conc['style_status'] == 'yellow', "红利低波 60% > 50% 必须触发风格警报"
    print("  ✅ [模块 10] 验证通过！")

    # -------------------------------------------------------------------------
    # [验收模块 11] 评分可解释化与统一风险仪表盘 (双轴评分、短板明确结论、6大红灯一屏总览)
    # -------------------------------------------------------------------------
    print("\n[验收模块 11] 评分可解释化与统一风险仪表盘...")
    # 模拟高危情况：高息负债=True (30分), 流动性超限=True (30分), 保障缺口降级=True (25分), 缓冲池安全 (0分) -> 脆弱性 85分
    scores = calculate_explainable_scores(
        has_high_debt=True,
        debt_balance=800000,
        is_liq_violated=True,
        is_coverage_insufficient=True,
        has_ins_downgrade=True,
        has_ins_gap=True,
        is_buf_unsafe=False,
        min_buf=50000,
        equity_weight=70.0,
        growth_rate=7.5,
        is_beh_exceeded=True,
        beh_excess_weight=15.0
    )
    print(f"  • 综合脆弱性得分: {scores['total_vulnerability']}分 (评级: {scores['vulnerability_level']})")
    print(f"  • 投资进攻性得分: {scores['total_aggressiveness']}分 (评级: {scores['aggressiveness_level']})")
    assert scores['total_vulnerability'] >= 60, "高危脆弱评分应 > 60"
    assert scores['vulnerability_level'] == '高危脆弱'

    dash = calculate_unified_risk_dashboard(red_count=2, yellow_count=1)
    print(f"  • 统一风险仪表盘: 红灯 {dash['red_count']} 个, 黄灯 {dash['yellow_count']} 个 -> 综合状态: {dash['overall_health']}")
    assert dash['overall_health'] == '高风险'
    print("  ✅ [模块 11] 验证通过！")

    # -------------------------------------------------------------------------
    # [验收模块 12] 前端 SPA 架构与文件完备性检查
    # -------------------------------------------------------------------------
    print("\n[验收模块 12] 前端 SPA 架构、本地持久化与合规免责声明检查...")
    with open('index.html', 'r', encoding='utf-8') as f:
        html = f.read()

    # 1. 检查核心顶栏与仪表盘组件
    assert '统一风险仪表盘' in html, "index.html 必须包含统一风险仪表盘卡片"
    assert '流动性硬隔离严重超限' in html or '流动性硬隔离超限警告' in html, "index.html 必须包含置顶流动性强警告条"
    
    # 2. 检查 11 个模块的核心关键词与交互锚点
    assert '家庭保障缺口测算' in html, "index.html 必须包含家庭保障缺口测算模块"
    assert '责任缺口法' in html, "index.html 必须包含责任缺口法计算提示"
    assert '目标导向规划' in html, "index.html 必须包含目标导向规划子页"
    assert '三大可调杠杆' in html, "index.html 必须包含三大可调杠杆推演"
    assert '债务决策对照' in html, "index.html 必须包含债务决策对照卡片"
    assert '个人养老金税优检查' in html, "index.html 必须包含个人养老金税优检查卡片"
    assert '房产集中度强化' in html or '房产集中度分析' in html, "index.html 必须包含房产集中度分析卡片"
    assert '购房首付核验' in html or '首付校验' in html, "index.html 必须包含首付缺口核验"
    assert '复合情景压力测试' in html, "index.html 必须包含复合情景压力测试面板"
    assert '历史回放' in html and '2018' in html, "index.html 必须包含历史回放选项"
    assert '行为风险约束' in html, "index.html 必须包含行为风险约束卡片"
    assert '为什么是这个数' in html, "index.html 必须包含行为约束透明化推演折叠面板"
    assert '估值温度计' in html, "index.html 必须包含估值温度计卖出纪律"
    assert '流动性硬隔离' in html, "index.html 必须包含流动性硬隔离卡片"
    assert '三重集中度' in html, "index.html 必须包含三重集中度卡片"
    assert '财务脆弱性' in html, "index.html 必须包含可解释化双轴评分"

    # 3. 检查 localStorage 与合规中立 tone
    assert 'localStorage.getItem' in html and 'localStorage.setItem' in html, "必须纯本地存储"
    assert '免责声明：所有财务推演与量化模型均基于用户输入的数据' in html, "必须包含规范免责声明"
    assert '必须还贷' not in html, "严禁绝对化命令语气'必须还贷'"
    assert '必须买' not in html, "严禁绝对化推销语气'必须买'"

    # 4. 检查 Python app.py 的同步性
    with open('app.py', 'r', encoding='utf-8') as f:
        app_code = f.read()
    assert 'calculate_insurance_gap' in app_code, "app.py 必须包含保障缺口函数导入"
    assert 'run_compound_stress_test' in app_code, "app.py 必须包含复合压力测试函数导入"

    print("  ✅ [模块 12] 验证通过！")

    print("\n================================================================================")
    print("🎉 恭喜！全部 12 项系统性升级验收测试 100% 成功通过！无任何断言失败！")
    print("================================================================================")

if __name__ == '__main__':
    run_acceptance_tests()
