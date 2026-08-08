# Quantra —— Agentic 研报投研工作台

> 研报解析 → 指标抽取 → 混合检索 + 会话记忆 → 多 Agent 编排 → 带引用的投资备忘录
> 内置：成本感知模型路由、全链路审计、引用/幻觉评测

Quantra 是一个面向 A 股投研场景的开源 Agent 工作台。它把"读研报、抽指标、找上下文、算趋势、写备忘录"这条研究员日常链路 Agent 化，并且把金融场景最在意的三件事做成第一等公民：

- **引用可溯源**：回答里的每个结论都必须能回到具体研报的章节和页码
- **动作可审计**：Agent 的每个工具调用都落库，成本、模型、参数可回放
- **成本可计算**：批量抽取跑便宜模型、复杂推理路由旗舰模型，每次运行出一份成本账

> 免责声明：本项目仅用于学习与研究，不构成任何投资建议。

## 快速开始

```bash
cd quantra
python -m quantra.app.cli init-db            # 初始化 SQLite
python -m quantra.app.cli demo-memo          # 零 API Key 跑通全流程演示
python -m quantra.app.cli ingest data/samples/示例-消费龙头2025年报点评.md
python -m quantra.app.cli query "华泰对这家公司2025年毛利率怎么看？"
python -m quantra.app.cli audit-log --limit 20
```

接 LLM（可选）：复制 `.env.example` 为 `.env`（或导出环境变量），配置 OpenAI 兼容接口。
未配置时系统自动进入 dry-run 确定性模式，功能链路依然完整，只是备忘录由模板生成。

## 架构

```
研报 PDF / MD / TXT
        │
        ▼
┌─────────────┐   ┌──────────────┐   ┌──────────────┐
│ ingest      │ → │ storage      │ → │ retrieval    │
│ 解析+指标抽取│   │ SQLite 事实库 │   │ 分块+BM25(+向量)│
└─────────────┘   │ 记忆层+审计   │   └──────────────┘
                  └──────┬───────┘          │
                         ▼                  ▼
┌───────────────────────────────────────────────────┐
│ agent                                            │
│  Plan-and-Execute 编排 · 工具白名单 · 审计钩子    │
│  成本感知 router（便宜模型批量 / 旗舰模型推理）     │
└───────────────────────────────────────────────────┘
        │
        ▼
┌─────────────┐   ┌──────────────┐
│ 带引用备忘录  │ ← │ eval         │
│ + 成本报告   │   │ 引用覆盖率评测 │
└─────────────┘   └──────────────┘
```

## 目录结构

```
quantra/
├── data/samples/        合成样本研报（先跑通，再放真实研报）
├── scripts/             工具脚本（如生成示例 PDF）
├── quantra/
│   ├── ingest/          PDF/MD 解析 + 指标抽取
│   ├── storage/         SQLite 事实库、记忆层、审计日志
│   ├── retrieval/       分块、BM25、混合检索（可插拔向量/重排）
│   ├── agent/           模型路由、工具、Plan-and-Execute 编排、审计
│   ├── eval/            引用覆盖率、幻觉守卫评测
│   └── app/             CLI 入口
├── tasks/               一周实施计划（plan.md / todo.md）
└── tests/               unittest 测试
```

## 一周计划

见 [`tasks/plan.md`](tasks/plan.md)（含验收标准与检查点）与 [`tasks/todo.md`](tasks/todo.md)。
核心理念：每天交付一个"可演示版本"，先跑通再优化。

## 简历叙事（模板）

- 独立开发开源 A 股投研 Agent 工作台 Quantra：研报解析 → 指标抽取 → 混合检索 → 多 Agent 编排 → 带引用备忘录
- 内置成本感知模型路由与全链路审计；评测模块对回答做引用覆盖率与幻觉守卫检查
- 周内完成 N 份研报、M 个指标抽取，准确率 X%，引用覆盖率 ≥ Y%（填入实测数字）

## Roadmap（一周之后）

- [ ] 向量检索接入（sentence-transformers 或 API embedding）+ RRF 融合
- [ ] LLM 指标抽取与人工规则双通道，交叉校验
- [ ] Streamlit 演示界面
- [ ] 因子定义抽取（对接"研报 → 因子复现"方向）
- [ ] 给开源社区贡献（如 TencentDB-Agent-Memory GFI / agent-skills 技能包 PR）
