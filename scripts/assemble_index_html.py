# scripts/assemble_index_html.py
import re
import os

with open('src/constants.js', 'r', encoding='utf-8') as f:
    constants_js = f.read()

with open('src/utils/calculations.js', 'r', encoding='utf-8') as f:
    calculations_js = f.read()

with open('src/utils/reportGenerator.js', 'r', encoding='utf-8') as f:
    report_generator_js = f.read()

def strip_es_modules(code):
    code = re.sub(r'import\s+[\s\S]*?from\s+[\'"][^\'"]+[\'"];?', '', code)
    code = re.sub(r'export\s+const\s+', 'const ', code)
    code = re.sub(r'export\s+function\s+', 'function ', code)
    code = re.sub(r'export\s+default\s+', '', code)
    return code.strip()

clean_constants = strip_es_modules(constants_js)
clean_calculations = strip_es_modules(calculations_js)
clean_report = strip_es_modules(report_generator_js)

migrate_state_js = """
// ==========================================
// 状态平滑迁移器 (migrateState)
// ==========================================
function migrateState(stored) {
  if (!stored) return INITIAL_STATE;
  const migrated = {
    ...INITIAL_STATE,
    ...stored,
    board: { ...INITIAL_STATE.board, ...(stored.board || {}) },
    health: { ...INITIAL_STATE.health, ...(stored.health || {}) },
    insurance: { ...INITIAL_STATE.insurance, ...(stored.insurance || {}) },
    debt: { ...INITIAL_STATE.debt, ...(stored.debt || {}) },
    pension: { ...INITIAL_STATE.pension, ...(stored.pension || {}) },
    property: { ...INITIAL_STATE.property, ...(stored.property || {}) },
    stress: { ...INITIAL_STATE.stress, ...(stored.stress || {}) },
    behavior: { ...INITIAL_STATE.behavior, ...(stored.behavior || {}) },
    thermometer: { ...INITIAL_STATE.thermometer, ...(stored.thermometer || {}) },
    goals: Array.isArray(stored.goals) && stored.goals.length > 0 ? stored.goals : INITIAL_STATE.goals
  };

  // 迁移老旧 bucket 字段至 A 组资产与 B 组确定性支出
  if (!migrated.health.assetsBreakdown) {
    migrated.health.assetsBreakdown = {
      cashCurrent: 100000,
      cashShortDebt: (migrated.health.bucket1To3y || 150000),
      equityAssets: (migrated.board.principal || 80) * 10000 * 0.55,
      goldAssets: 56000,
      bondAssets: 184000,
      propertyEstimated: (migrated.property?.totalEstimatedValue || 2800000),
      pensionCashValue: 20000,
      otherAssets: 0
    };
  }
  if (!migrated.health.expectedExpenses) {
    migrated.health.expectedExpenses = {
      expense1y: (migrated.health.bucket1y || 100000),
      expense1To3y: (migrated.health.bucket1To3y || 150000),
      expense3To5y: (migrated.health.bucket3To5y || 100000)
    };
  }
  // 利率中值与自定义利率防呆
  if (migrated.debt.customDebtRate === 5.5 && !migrated.debt.useCustomRate) {
    migrated.debt.customDebtRate = null;
    migrated.debt.useCustomRate = false;
  }
  if (migrated.debt.remainingYears === undefined) {
    migrated.debt.remainingYears = 15;
  }
  if (migrated.stress.unemploymentReplacementRate === undefined) {
    migrated.stress.unemploymentReplacementRate = 0.3;
  }
  return migrated;
}
"""

with open('scripts/app_jsx.js', 'r', encoding='utf-8') as f:
    app_jsx = f.read()

# Build HTML
html_template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>家庭财富规划与量化风险管理系统 (纯前端/localStorage)</title>
  <!-- 引入 React 18、ReactDOM 以及 Babel Standalone 浏览器实时解析器 -->
  <script src="https://cdn.jsdelivr.net/npm/react@18.2.0/umd/react.production.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/react-dom@18.2.0/umd/react-dom.production.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/@babel/standalone@7.24.4/babel.min.js"></script>
  <style>
    :root {{
      --bg-dark: #0B0F19;
      --card-bg: rgba(22, 28, 45, 0.75);
      --card-border: rgba(255, 255, 255, 0.08);
      --card-hover-border: rgba(16, 185, 129, 0.35);
      --text-main: #F1F5F9;
      --text-muted: #94A3B8;
      --primary: #10B981;
      --primary-hover: #059669;
      --primary-bg: rgba(16, 185, 129, 0.12);
      --amber: #F59E0B;
      --amber-bg: rgba(245, 158, 11, 0.15);
      --rose: #F43F5E;
      --rose-bg: rgba(244, 63, 94, 0.15);
      --blue: #38BDF8;
      --blue-bg: rgba(56, 189, 248, 0.12);
      --purple: #A855F7;
      --purple-bg: rgba(168, 85, 247, 0.15);
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    html {{
      scroll-behavior: smooth;
    }}

    body {{
      background-color: var(--bg-dark);
      color: var(--text-main);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      line-height: 1.5;
      min-height: 100vh;
      overflow-x: hidden;
      background-image: 
        radial-gradient(circle at 10% 20%, rgba(16, 185, 129, 0.05) 0%, transparent 40%),
        radial-gradient(circle at 90% 80%, rgba(56, 189, 248, 0.05) 0%, transparent 40%);
    }}

    /* 滚动条美化 */
    ::-webkit-scrollbar {{
      width: 8px;
      height: 8px;
    }}
    ::-webkit-scrollbar-track {{
      background: #0F172A;
    }}
    ::-webkit-scrollbar-thumb {{
      background: #334155;
      border-radius: 4px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
      background: #475569;
    }}

    .container {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 20px;
    }}

    /* 顶部导航 */
    header {{
      background: rgba(15, 23, 42, 0.88);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--card-border);
      position: sticky;
      top: 0;
      z-index: 100;
    }}
    .header-inner {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 20px;
      max-width: 1440px;
      margin: 0 auto;
    }}
    .logo-area {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .logo-badge {{
      background: linear-gradient(135deg, #10B981, #06B6D4);
      width: 40px;
      height: 40px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      box-shadow: 0 0 15px rgba(16, 185, 129, 0.3);
    }}
    .brand-title {{
      font-size: 1.15rem;
      font-weight: 700;
      color: #FFF;
      letter-spacing: -0.02em;
    }}
    .brand-subtitle {{
      font-size: 0.75rem;
      color: var(--text-muted);
    }}

    .nav-tabs {{
      display: flex;
      gap: 6px;
      background: rgba(0, 0, 0, 0.25);
      padding: 4px;
      border-radius: 10px;
      border: 1px solid var(--card-border);
    }}
    .nav-tab-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 7px 14px;
      border-radius: 7px;
      font-size: 0.85rem;
      font-weight: 500;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s ease;
    }}
    .nav-tab-btn:hover {{
      color: var(--text-main);
      background: rgba(255, 255, 255, 0.05);
    }}
    .nav-tab-btn.active {{
      color: #FFF;
      background: var(--primary);
      box-shadow: 0 2px 10px rgba(16, 185, 129, 0.35);
    }}

    /* 卡片与网格系统 */
    .grid-2 {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }}
    .grid-3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }}
    .grid-4 {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }}
    .grid-6 {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; }}
    .grid-8 {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }}

    @media (max-width: 1100px) {{
      .grid-8 {{ grid-template-columns: repeat(2, 1fr); }}
      .grid-6 {{ grid-template-columns: repeat(3, 1fr); }}
      .grid-4 {{ grid-template-columns: repeat(2, 1fr); }}
    }}
    @media (max-width: 768px) {{
      .grid-8, .grid-6, .grid-4, .grid-3, .grid-2 {{ grid-template-columns: 1fr; }}
      .header-inner {{ flex-direction: column; gap: 12px; }}
      .nav-tabs {{ flex-wrap: wrap; justify-content: center; }}
    }}

    .card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
      backdrop-filter: blur(10px);
      -webkit-backdrop-filter: blur(10px);
      box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
      margin-bottom: 20px;
      transition: border-color 0.2s ease;
    }}
    .card:hover {{
      border-color: var(--card-hover-border);
    }}

    .card-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 16px;
      padding-bottom: 12px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }}
    .card-title {{
      font-size: 1.05rem;
      font-weight: 700;
      color: #FFF;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    /* 指标卡片 */
    .metric-card {{
      background: rgba(30, 41, 59, 0.6);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 16px;
      position: relative;
      overflow: hidden;
    }}
    .metric-label {{
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-bottom: 4px;
    }}
    .metric-val {{
      font-size: 1.45rem;
      font-weight: 700;
      color: #FFF;
      letter-spacing: -0.01em;
    }}
    .metric-sub {{
      font-size: 0.75rem;
      color: var(--text-muted);
      margin-top: 4px;
    }}

    /* 按钮 */
    .btn {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid transparent;
      transition: all 0.2s ease;
    }}
    .btn-primary {{
      background: var(--primary);
      color: #FFF;
    }}
    .btn-primary:hover {{
      background: var(--primary-hover);
      box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
    }}
    .btn-outline {{
      background: rgba(255, 255, 255, 0.05);
      border-color: var(--card-border);
      color: var(--text-main);
    }}
    .btn-outline:hover {{
      background: rgba(255, 255, 255, 0.1);
      border-color: rgba(255, 255, 255, 0.2);
    }}
    .btn-danger {{
      background: rgba(244, 63, 94, 0.2);
      border-color: rgba(244, 63, 94, 0.4);
      color: #FB7185;
    }}
    .btn-danger:hover {{
      background: rgba(244, 63, 94, 0.35);
    }}
    .btn-sm {{
      padding: 4px 10px;
      font-size: 0.75rem;
      border-radius: 6px;
    }}

    /* 表格样式 */
    .table-container {{
      width: 100%;
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.85rem;
      text-align: left;
    }}
    th {{
      background: rgba(15, 23, 42, 0.6);
      color: var(--text-muted);
      font-weight: 600;
      padding: 10px 14px;
      border-bottom: 1px solid var(--card-border);
      white-space: nowrap;
    }}
    td {{
      padding: 12px 14px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      color: var(--text-main);
    }}
    tr:hover td {{
      background: rgba(255, 255, 255, 0.02);
    }}

    /* 徽章与标签 */
    .tag {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 0.72rem;
      font-weight: 600;
    }}
    .tag-green {{ background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }}
    .tag-yellow {{ background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.3); }}
    .tag-red {{ background: rgba(244, 63, 94, 0.15); color: #F87171; border: 1px solid rgba(244, 63, 94, 0.3); }}
    .tag-blue {{ background: rgba(56, 189, 248, 0.15); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.3); }}
    .tag-purple {{ background: rgba(168, 85, 247, 0.15); color: #C084FC; border: 1px solid rgba(168, 85, 247, 0.3); }}

    .pulse-dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--primary);
      box-shadow: 0 0 8px var(--primary);
      display: inline-block;
      animation: pulse 2s infinite;
    }}
    @keyframes pulse {{
      0%, 100% {{ transform: scale(1); opacity: 1; }}
      50% {{ transform: scale(1.4); opacity: 0.6; }}
    }}

    .storage-tag {{
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.75rem;
      color: #34D399;
      background: rgba(16, 185, 129, 0.1);
      padding: 4px 10px;
      border-radius: 20px;
      border: 1px solid rgba(16, 185, 129, 0.2);
    }}

    /* 表单控件 */
    .form-group {{
      margin-bottom: 14px;
    }}
    .form-label {{
      display: block;
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-bottom: 6px;
      font-weight: 500;
    }}
    .input-control {{
      width: 100%;
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid var(--card-border);
      color: #FFF;
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 0.85rem;
      outline: none;
      transition: border-color 0.2s;
    }}
    .input-control:focus {{
      border-color: var(--primary);
      box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
    }}
    .input-control.error {{
      border-color: #EF4444;
      background: rgba(239, 68, 68, 0.08);
    }}

    /* 弹窗遮罩 */
    .modal-backdrop {{
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(6px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 200;
    }}
    .modal-box {{
      background: #111827;
      border: 1px solid var(--card-border);
      border-radius: 14px;
      width: 90%;
      max-width: 620px;
      padding: 24px;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
      max-height: 90vh;
      overflow-y: auto;
    }}

    /* 红黄绿灯总览卡片 */
    .traffic-card {{
      background: rgba(30, 41, 59, 0.5);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 12px 14px;
      cursor: pointer;
      transition: all 0.2s ease;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
    .traffic-card:hover {{
      transform: translateY(-2px);
      border-color: rgba(255, 255, 255, 0.2);
      box-shadow: 0 6px 16px rgba(0,0,0,0.3);
    }}
    .traffic-card.red {{ border-left: 4px solid #EF4444; background: rgba(239, 68, 68, 0.08); }}
    .traffic-card.yellow {{ border-left: 4px solid #F59E0B; background: rgba(245, 158, 11, 0.08); }}
    .traffic-card.green {{ border-left: 4px solid #10B981; background: rgba(16, 185, 129, 0.08); }}
  </style>
</head>
<body>
  <div id="root"></div>

  <script type="text/babel">
    const {{ useState, useEffect, useMemo, useRef }} = React;

    const STORAGE_KEY = 'WEALTH_PLANNING_LOCAL_STORAGE_V1';

    // ==========================================
    // 常量与配置
    // ==========================================
{clean_constants}

{migrate_state_js}

    // ==========================================
    // 纯函数计算工具引擎
    // ==========================================
{clean_calculations}

    // ==========================================
    // 报告生成引擎
    // ==========================================
{clean_report}

    // ==========================================
    // React 主界面组件 App()
    // ==========================================
{app_jsx}

    ReactDOM.createRoot(document.getElementById('root')).render(<App />);
  </script>
</body>
</html>
"""

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html_template)

print("Successfully generated index.html. Total size:", len(html_template), "bytes")
