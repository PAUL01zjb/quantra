# Implementation Plan: Quantra（Agentic 研报投研工作台）

## Overview

一周内从零搭出一个可演示、可评测、可写进简历的 A 股研报投研 Agent 工作台：研报解析 → 指标抽取 → 混合检索 + 记忆 → 多 Agent 编排 → 带引用备忘录，内置成本路由、全链路审计与引用评测。

时间预算：每天 1–1.5 小时（每周 8–10 小时）。每个阶段都有最小可演示版本，先跑通再优化。

## Architecture Decisions

1. **不锁死框架**：Agent 编排手写 Plan-and-Execute（理解底层原理），检索层 BM25 手写（学习价值），后续可插拔向量/重排/LLM 客户端。这与"两年规划"里"从会用 Agent 到理解 Agent 底层"的目标一致。
2. **确定性优先**：指标抽取先用规则（数字可复现），LLM 抽取作为第二通道交叉校验；关键路径不依赖 LLM 也能跑通（dry-run 模式）。
3. **SQLite 单文件**：事实库、审计日志、记忆层同库，零部署成本，方便周内随时迁移到任何环境。
4. **成本与审计内建**：router 记录每次调用的模型与预估成本；audit 记录每个工具调用；两者从第一天就是数据，而不是事后补。
5. **引用是硬约束**：备忘录只允许引用检索证据，eval 模块用引用覆盖率量化"幻觉"风险。

## Task List

### Phase 0：项目启动与数据接入（D1）

- [ ] Task 1: 跑通仓库骨架与 CLI（init-db / demo-memo / ingest / query）
- [ ] Task 2: 解析模块支持 MD/TXT/PDF，抽取标题、机构、评级、目标价、财务指标、表格
- [ ] Task 3: 3–5 份真实研报入库，输出抽取结果（数量/准确率目检）

### Checkpoint: Foundation
- [ ] `python -m quantra.app.cli demo-memo` 全流程跑通
- [ ] `unittest` 全部通过
- [ ] 至少 1 份真实研报解析结果人工抽查无误

### Phase 1: 检索与记忆（D2–D3）

- [ ] Task 4: 分块策略（标题感知 + 表格完整保留 + 重叠窗口）
- [ ] Task 5: BM25 索引与混合检索（预留向量/重排接口）
- [ ] Task 6: 会话记忆层（研究结论、待验证假设持久化，跨会话可查）

### Checkpoint: Core Retrieval
- [ ] 对研报提问能返回带报告名/章节/页码的上下文
- [ ] 记忆层能存、能查、能在下一次会话复用

### Phase 2: Agent 编排 + 成本路由 + 审计（D4–D5）

- [ ] Task 7: 工具层（search / extract_metric / calc_trend / list_reports）JSON Schema + 白名单
- [ ] Task 8: 成本感知 router（任务复杂度 → 模型 → 预估成本账）
- [ ] Task 9: Plan-and-Execute 主循环：计划 → 执行 → 带引用备忘录（LLM 与 dry-run 双模式）
- [ ] Task 10: 审计回放（`audit-log` 命令可查看每步动作、模型、成本）

### Checkpoint: Core Agent
- [ ] 端到端问答：输入问题 → 输出带引用的备忘录 + 成本报告 + 审计轨迹
- [ ] dry-run 与接 LLM 两种模式都可用

### Phase 3: 评测与打磨（D6–D7）

- [ ] Task 11: 引用覆盖率与幻觉守卫评测（eval 命令 + 至少 10 个问答样例）
- [ ] Task 12: README / 架构图 / 简历叙事页 / 示例输出
- [ ] Task 13（可选加分）: 提一个开源 PR（TencentDB-Agent-Memory #157/#103，或 agent-skills 投研技能包）

### Checkpoint: Complete
- [ ] 引用覆盖率报告 ≥ 目标值（如 80%+，随实测调整）
- [ ] README 可当简历附件用（含实测数字）
- [ ] 代码已推送 GitHub（可公开或私有 + 录屏 demo）

## Risks and Mitigations

| 风险 | 影响 | 应对 |
|---|---|---|
| 时间不够 | 高 | 每阶段最小可演示优先；周日只保"端到端 + README" |
| 真实研报版权/难找 | 中 | 先合成样本跑通，再放手头真实研报；不上传受版权保护的研报 |
| API 成本不可控 | 低 | dry-run 默认零成本；接 API 后批量走便宜模型 |
| 向量检索依赖重 | 低 | 接口先行，先 BM25，向量后补 |
| 简历数字不扎实 | 中 | 评测模块产出真实数字，不编造 |

## Open Questions

- GitHub 仓库名与可见性（当前工作名 quantra）
- 周内是否接入真实研报（可考虑公开渠道的券商研报）
- 是否优先做 Streamlit 演示界面（D7 有余力再做）
