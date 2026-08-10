# Quantra 架构设计（v0.1）

> 更新：2026-08-08 ｜ 状态：与代码同步演进

## 1. 总体架构

```mermaid
flowchart TB
  subgraph 数据层
    A["研报 PDF / MD / TXT"]
    B["场景模拟器<br/>真实业务场景定义"]
  end
  subgraph 核心层
    C["ingest 解析 + 指标抽取"]
    D["storage SQLite<br/>事实库/审计/记忆"]
    E["retrieval 分块 + BM25<br/>+ 可插拔向量"]
    F["agent 编排状态机<br/>工具Schema生成/路由/审计"]
    G["eval 金标准评测<br/>引用覆盖率/幻觉守卫"]
  end
  subgraph 输出层
    H["带引用投资备忘录"]
    I["成本报告 + Trace + 审计回放"]
    J["场景评测报告"]
  end
  A --> C --> D
  B --> F
  D --> E --> F
  F --> G
  F --> H
  F --> I
  G --> J
```

## 2. 一次业务问答的完整时序

```mermaid
sequenceDiagram
  participant U as 用户/场景
  participant A as QuantraAgent
  participant R as Retriever
  participant T as Tools
  participant L as LLM(可插拔)
  participant S as SQLite
  U->>A: 业务问题（如"对比两家公司毛利率"）
  A->>A: 编排状态机进入 PLANNING
  A->>L: 生成计划（或确定性默认计划）
  A->>A: 校验计划步骤（工具白名单 + 预算）
  A->>A: EXECUTING
  A->>R: 检索相关研报段落
  R-->>A: 带章节/页码的引用块
  A->>T: extract_metric / calc_trend（审计 + 成本记录）
  T-->>A: 结构化指标与趋势
  A->>L: 生成带引用备忘录（或 dry-run 模板）
  A->>A: REVIEWING（引用覆盖检查）
  A->>S: 记忆写入 + 审计落库
  A-->>U: 备忘录 + 成本 + trace + 评测
```

## 3. 模块职责与接口

| 模块 | 职责 | 关键接口 |
|---|---|---|
| `parsing/` | 解析小框架：输入接口 ParseRequest → 引擎层（pdfplumber/MinerU/Docling 插拔）→ 输出接口 ParseResult | `parse_document(request) -> ParseResult` |
| `ingest/parser` | （旧版，待迁移）解析 + 规则抽取指标 | `parse_document(path) -> Report` |
| `storage/db` | 事实库、审计、记忆统一落库 | `upsert_report / audit / memory_append` |
| `retrieval/chunking` | 标题感知分块、表格保留、重叠窗口 | `chunk_report(report) -> list[Chunk]` |
| `retrieval/bm25` | 手写 BM25（含中文分词兜底） | `fit(docs) / top_k(query)` |
| `retrieval/hybrid` | BM25 + 可插拔向量 + RRF | `search(query, k) -> list[RetrievedChunk]` |
| `agent/tools` | 工具注册、Schema 生成、白名单 | `run_tool(name, args)` |
| `agent/orchestrator` | 三态状态机、计划-执行-评审 | `run(question) -> AgentResult` |
| `agent/router` | 成本感知模型路由 | `route(task, settings) -> model` |
| `agent/audit` | 全链路审计钩子 | `step(action, detail)` 上下文管理器 |
| `eval/grounding` | 引用覆盖率、幻觉守卫 | `citation_coverage(memo, evidence)` |
| `scenarios/` | 真实业务场景定义与模拟运行 | `run_scenario(id) -> report` |
| `app/cli` | 命令行入口 | `ingest / query / scenario / eval / audit-log` |

## 4. 关键设计决策（trade-off）

### 4.1 编排 = 状态机，不是"死循环调模型"

决策：planning → executing → reviewing 三态显式建模；步数上限、成本预算上限、失败重试与回退。

为什么：裸 ReAct 循环的最大问题是"不收敛不可控"。显式状态机让"Agent 卡死/超支"从玄学变成可设计、可测试、可面试讲解的工程问题。

代价：编排灵活性略降（每类任务需要适配计划模板），通过"确定性默认计划 + LLM 计划双通道"缓解。

### 4.2 工具 Schema 从函数签名自动生成

决策：用 `inspect.signature` + 类型注解 + docstring 第一行生成 JSON Schema，执行前参数校验、执行后异常恢复。

为什么：手写 Schema 会与函数实现漂移；自动生成保证"工具定义"与"工具实现"单一事实源。这也是函数调用底层的核心工程点。

代价：类型注解需要规范（`Optional[str]`、默认值语义需约定），用测试锁定。

### 4.6 解析层 = 接口化流水线，不是"一个解析函数"

决策：`ParseRequest`（输入契约：来源/语言/模式/是否解析表格/页范围/引擎）→ 引擎层（pdfplumber 默认、MinerU/Docling 可选）→ `ParseResult`（输出契约：blocks/markdown/stats/engine）。

为什么：解析方案演进快（CNN 版面检测 → VLM 端到端），接口隔离后换引擎不影响上层；上层（抽取/归档/Agent）只依赖输出契约，可测试、可审计。

代价：多一层抽象；用引擎选择策略（auto → 文本型用 pdfplumber，扫描件切 MinerU）缓解。

### 4.3 检索 = BM25 起步，向量可插拔

决策：手写 BM25（含中文 unigram+bigram 兜底），向量检索通过 `Embedder` 接口预留，RRF 融合。

为什么：金融数字场景大量精确匹配（指标名、年份、数值），BM25 是性价比最高的基线；先跑通再上向量，避免过早引入依赖。

代价：语义召回弱于向量检索，D3 以 recall@k 金标准集评估差距后决定是否接入。

### 4.4 记忆 = 分层设计

决策：episodic（问答记录）+ semantic（研究结论/待验证假设/失败经验）分层，跨会话可查、可去重。

为什么：对齐 8/3 简报"记忆层卡位"主题；研究结论不丢、失败经验可复用，是量化研究 Agent 的核心痛点。

### 4.5 评测 = 引用覆盖率 + 金标准回归

决策：每个结论句必须与证据文本有可量化重合度；金标准问答集做回归对比，防止改动破坏已有能力。

为什么：金融场景幻觉代价高；"引用可溯源"不是口号，是评测指标。

## 5. 数据模型

核心实体：`Report / Section / Table / Metric / Chunk / AgentStep / AgentResult / Scenario`。

存储：SQLite 单文件（reports、sections、metrics、chunks、audit_log、memory），零部署成本。

## 6. 可观测性与安全

- 每个工具调用：动作、参数、模型、成本、状态全部进 `audit_log`，`audit-log` 命令可回放。
- 每次运行：生成 trace（步骤、延迟、token、成本预估）。
- 安全：工具白名单 + 参数校验；有副作用操作标记为需人工审批（`side_effect=True`），后续接审批钩子。

## 7. 演进路线

- D3：向量检索接入与 RRF 评估
- D5：多 Agent 角色（研究/质检/风控评审）
- D7：Streamlit 演示界面
- 之后：研报因子定义抽取（对接"研报 → 因子复现"方向）
