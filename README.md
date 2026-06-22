# 💰 红利低波资产现金流规划与监控工具 (Wealth Planning)

这是一个为红利低波策略投资者设计的一站式资产配置、现金流规划及风险监控工具。该项目支持静态网页版 (HTML5/JS) 和本地 Python GUI (Streamlit) 双向展现，帮助投资者合理规划现金缓冲池，评估极端市况下的现金流弹性，实现稳定且具备抗震防线的被动收入财务规划。

---

## 🌟 核心功能模块

1. **📊 资产配置与股息看板**  
   设置本金与被动红利基金（ETF）的目标配置权重，动态计算税后综合股息率及年化/月均预计现金流产出。在行情不可用时，具备自动降级至预设股息率的兜底逻辑。
   
2. **⏱️ 缓冲池与现金流模拟**  
   由于 ETF 分红通常集中在 5-8 月密集派发，本模块通过引入“现金缓冲池”机制，模拟 36 个月的生活费平滑支取变动（结合闲置利息计息），确保日常支取流出的平稳性。
   
3. **🌡️ 估值温度计与测算助手**  
   从 `valuation_history.json` 读取真实历史估值数据（当前支持中证红利低波指数 `H30269` 历史序列），展示当前股息率、PE（市盈率）、PB（市净率）及其所处的历史百分位温度。根据估值高低生成月度定投额度调节测算。
   
4. **⚖️ 资产记账与再平衡提示**  
   支持录入持仓市值，一键测算实际偏离度，并在偏离度超过阈值（如 ±3%）时给出买入/卖出的再平衡测算，规避情绪化交易，亦支持低摩擦的“增量资金再平衡”。
   
5. **⚡ 风险压力测试**  
   支持自定义极端市场参数（分红下降比例、常规 ETF 回撤、港股资产回撤、备用金月份），逐月投影 36 个月内现金缓冲池水位的衰减曲线，输出 12/24/36 个月现金流是否会被击穿的评估。

6. **🏥 家庭资产体检与配置建议**  
   提供一站式、零服务器上传、纯本地运行的家庭财务健康体检。涵盖家庭基本信息、资产负债明细及风险性格约束，智能推导财务健康画像（如债务高锁、现金脆弱、权益高波动型等），生成对应的“安全/成长/对冲”三桶防线比例建议，并支持一键导出 JSON 及复制 Markdown 格式的完整体检报告。

---

## 🛠️ 本地运行方式

### 方案 A：静态网页运行 (推荐，轻量便携)
本项目包含完整的单页静态 Web 应用，可以直接使用浏览器双击打开：
- 主页看板：直接打开根目录的 [index.html](file:///Users/baokaijian/Project/gemini-invest/index.html)。
- 家庭资产体检页：直接打开根目录的 [family_profile.html](file:///Users/baokaijian/Project/gemini-invest/family_profile.html)。
- 或者在终端使用 python 起一个本地网页服务：
  ```bash
  python3 -m http.server 8000
  ```
  然后在浏览器中访问 `http://localhost:8000`。

### 方案 B：Streamlit 本地 GUI 应用 (丰富交互)
如果您偏好 Python 交互式控制台，可以通过 Streamlit 运行：
1. 确保安装依赖：
   ```bash
   pip install streamlit pandas numpy plotly
   ```
2. 在项目根目录执行：
   ```bash
   streamlit run app.py
   ```
   或者直接运行启动脚本 `./run.sh`。

---

## 🔄 数据来源与同步管线

- **基础资产池配置**：通过 [assets.json](file:///Users/baokaijian/Project/gemini-invest/assets.json) 集中维护被动红利基金（ETF）的基础配置信息（代码、目标指数、分配月份、权重等）。
- **实时收盘行情数据**：优先从同级目录下的缓存文件 [live_data.json](file:///Users/baokaijian/Project/gemini-invest/live_data.json) 读取数据，每 60 秒轮询一次。若数据失效或载入失败，系统自动降级使用 `estimated_yield` 兜底，绝不发生跨域频繁直连外部 API 导致的响应堵塞。
- **历史估值数据**：估值温度计的百分位和趋势图完全基于 [valuation_history.json](file:///Users/baokaijian/Project/gemini-invest/valuation_history.json) 的真实日期、股息率、PE、PB 字段进行渲染和对齐。
- **本地行情手动抓取**：
  若想手动触发实时行情抓取并更新本地缓存包，直接执行：
  ```bash
  python3 update_data.py
  ```

---

## 🚀 GitHub Pages 部署与自动化

本项目非常适合无服务端静态部署至 GitHub Pages：
1. **GitHub Pages 配置**：
   - 进入 GitHub 仓库 -> Settings -> Pages。
   - Build and deployment 源选择 **Deploy from a branch**。
   - 分支选择 `master`，路径选择 `/ (root)`，保存即可。
   - 部署成功后，可通过 Pages 地址直接访问（例如：`https://baokaijian.github.io/wealth-planning/`）。
2. **GitHub Actions 行情自动更新**：
   - 仓库已配置好 CI/CD 工作流：[.github/workflows/update_data.yml](file:///Users/baokaijian/Project/gemini-invest/.github/workflows/update_data.yml)。
   - 该工作流在每个交易日的 17:00 (北京时间) 在 GitHub 托管的 Ubuntu 容器中自动运行 `update_data.py`。
   - 抓取到最新收盘行情后，自动向 master 分支 commit 并 push `live_data.json` 缓存，从而触发 GitHub Pages 的自动重绘，无需人工维护。

---

## ⚠️ 风险提示 & 免责声明

> [!IMPORTANT]
> **本项目仅用于资产配置测算，不构成任何投资建议或证券推荐。**
> 
> **基金的过往业绩和历史分红并不预示其未来表现。** 
> 
> 投资有风险，决策需谨慎。ETF 分红金额、频率及月份受宏观经济波动、成分股分红意愿及基金公司分红政策的直接影响，存在不均衡及分红下降甚至暂停分红的可能。压力测试为纯数学理论测算，仅用于测算极端条件下的资金承受边界，不代表任何收益或抗回撤表现的承诺。
