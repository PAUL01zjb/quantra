# Quantra 一周任务清单

> 更新方式：每完成一项把 `[ ]` 改为 `[x]`，并把实测数字填进 README 简历叙事。

## Phase 0：数据接入（D1）

- [ ] Task 1: 跑通 CLI（init-db / demo-memo / ingest / query）
- [x] Task 2: 解析小框架（输入/输出接口 + pdfplumber + MinerU 插槽）
- [x] Task 2b: 归档层（company 主维度 + metric_fact 复合键 + 指标词典 + 公司卡片）
- [ ] Task 3: 3–5 份真实研报入库并目检抽取结果

## Phase 1：检索与记忆（D2–D3）

- [ ] Task 4: 分块策略（标题感知、表格完整、重叠窗口）
- [ ] Task 5: BM25 + 混合检索（预留向量/重排接口）
- [ ] Task 6: 会话记忆层（结论/假设持久化）

## Phase 2：Agent 编排 + 成本路由 + 审计（D4–D5）

- [ ] Task 7: 工具 Schema 从函数类型注解自动生成 + 参数校验/错误恢复/超时
- [ ] Task 8: 编排状态机（三态 + 预算上限 + 重试回退）
- [ ] Task 9: 成本感知 router + 每步 trace（模型/成本/延迟）
- [ ] Task 10: 审计回放 + 安全钩子（副作用操作人工审批）
- [ ] Task 11（加分）: 多 Agent 角色（研究/质检/风控评审）

## Phase 3：评测与打磨（D6–D7）

- [ ] Task 12: 金标准评测（≥10 条问答 + 回归对比）
- [ ] Task 13: README / 架构图 / 简历叙事 / 示例输出
- [ ] Task 14（可选）: 开源 PR 贡献

## 收尾检查点

- [ ] demo-memo 与 unittest 全绿
- [ ] 引用覆盖率报告生成
- [ ] GitHub 已推送，README 含实测数字
