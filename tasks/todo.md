# Quantra 一周任务清单

> 更新方式：每完成一项把 `[ ]` 改为 `[x]`，并把实测数字填进 README 简历叙事。

## Phase 0：数据接入（D1）

- [ ] Task 1: 跑通 CLI（init-db / demo-memo / ingest / query）
- [ ] Task 2: 解析 MD/TXT/PDF，抽取标题、机构、评级、目标价、指标、表格
- [ ] Task 3: 3–5 份真实研报入库并目检抽取结果

## Phase 1：检索与记忆（D2–D3）

- [ ] Task 4: 分块策略（标题感知、表格完整、重叠窗口）
- [ ] Task 5: BM25 + 混合检索（预留向量/重排接口）
- [ ] Task 6: 会话记忆层（结论/假设持久化）

## Phase 2：Agent 编排 + 成本路由 + 审计（D4–D5）

- [ ] Task 7: 工具层（search / extract_metric / calc_trend / list_reports）
- [ ] Task 8: 成本感知 router
- [ ] Task 9: Plan-and-Execute 主循环（LLM + dry-run 双模式）
- [ ] Task 10: 审计回放

## Phase 3：评测与打磨（D6–D7）

- [ ] Task 11: 引用覆盖率 + 幻觉守卫评测（≥10 个样例）
- [ ] Task 12: README / 架构图 / 简历叙事 / 示例输出
- [ ] Task 13（可选）: 开源 PR 贡献

## 收尾检查点

- [ ] demo-memo 与 unittest 全绿
- [ ] 引用覆盖率报告生成
- [ ] GitHub 已推送，README 含实测数字
