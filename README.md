# NovelOps Agent

面向小说平台的业务异常调查与处理 Agent。当前 MVP 已形成以下闭环：

```text
用户目标 → 规划调查 → 查询业务事实 → RAG检索适用制度
       → 确定性规则核验 → 生成带引用的报告 → 人工审批 → 工单草稿
```

## 核心设计

- **LangGraph**：管理调查节点、状态、循环和人工审批中断。
- **业务工具**：查询作品、合同和结算记录。
- **本地RAG**：使用中文字符 bigram + BM25 检索制度条款。
- **混合召回**：在线Embedding、本地JSON向量索引、BM25与RRF融合。
- **Rerank**：使用结构化输出对融合候选进行在线重排序。
- **元数据过滤**：按业务类型、版本和案例发生日期选择适用规则。
- **规则引擎**：确定性计算金额及比例，不让大模型心算。
- **Human-in-the-loop**：创建工单前必须人工批准。

没有 API Key 时可离线运行完整流程。配置模型后，LLM负责规划与报告组织，但仍只能根据工具证据下结论。

## 快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m novelops_agent.cli --approve yes
pytest -q
```

若当前终端的 `python` 不可见：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m novelops_agent.cli --approve yes
.\.venv\Scripts\python.exe -m pytest -q
```

## 知识库结构

```text
knowledge/
├── catalog.json                         # 文档版本、生效日期、业务类型
├── settlement/
│   ├── 作者结算管理办法_2026_v2.md
│   ├── 作者结算管理办法_2025_v1.md      # 验证历史版本过滤
│   └── 结算异常处理SOP.md
├── contract/
│   └── 小说签约与合同生效规则.md
└── review/
    └── 投稿审核时效规范.md
```

当前文档均为作品集演示规则，不代表任何真实公司的制度。

## RAG返回内容

每条召回结果都包含文档名称、版本、条款、原文、生效区间、业务类型和检索分数。引用格式例如：

```text
《作者结算管理办法》2026-v2 第3.1条 分成比例
```

## 项目结构

```text
novelops_agent/
├── agent.py                 # LangGraph调查图和审批节点
├── rag.py                   # 中文BM25、切块和元数据过滤
├── tools.py                 # RAG与业务工具注册表
├── repository.py            # 模拟业务数据仓储
├── schemas.py               # 结构化规划与报告
├── cli.py                   # 命令行演示入口
└── data/sample_data.json    # 异常与正常案例
tests/
├── test_agent.py
├── test_rag.py
└── test_tools.py
```

## 使用真实大模型

复制 `.env.example` 为 `.env`，填入百炼Workspace地址和API Key。不要把真实Key提交到代码仓库：

```dotenv
DASHSCOPE_API_KEY=your-bailian-key
DASHSCOPE_BASE_URL=https://YOUR_WORKSPACE_ID.cn-beijing.maas.aliyuncs.com/compatible-mode/v1

LLM_MODEL=deepseek-v4-pro
RERANK_MODEL=deepseek-v4-pro
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIMENSIONS=1024
EMBEDDING_BATCH_SIZE=10
HYBRID_RERANK_ENABLED=true
```

默认由Agent和Rerank共用 `deepseek-v4-pro`，向量化使用Qwen3-Embedding系列的 `text-embedding-v4`。如果两类模型使用不同Key或Endpoint，可分别设置 `LLM_API_KEY`、`LLM_BASE_URL`、`EMBEDDING_API_KEY`、`EMBEDDING_BASE_URL`，它们会覆盖公共的 `DASHSCOPE_*` 配置。

首次配置Key后构建本地向量索引：

```powershell
.\.venv\Scripts\python.exe scripts\build_vector_index.py
```

文档未变化时会复用已有向量；使用 `--force` 可以强制全部重建。索引默认写入 `knowledge/index/vectors.json`，其中包含Chunk文本、元数据、内容哈希和向量。

测试混合检索与Rerank：

```powershell
.\.venv\Scripts\python.exe scripts\search_knowledge.py `
  "签约第三个月需要多少听读收益才能获得全勤" `
  --platform "番茄小说" `
  --business-type settlement `
  --effective-at 2026-10-07
```

完整检索链路：

```text
BM25 Top20 ─┐
            ├─ RRF融合 Top10 → 在线Rerank → Top3
向量 Top20 ─┘
```

当API Key或向量索引不存在时，Agent会明确返回 `bm25_fallback`；索引存在且关闭Rerank时返回 `hybrid_bm25_vector_rrf`；完整链路返回 `hybrid_bm25_vector_rrf_rerank`。

## Agent测评

先使用50本小说的标注数据运行离线确定性测评，不调用大模型，不产生API费用：

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_agent.py
```

输出包含异常精确率、召回率、F1、分类型召回率、人工中断准确率、证据覆盖率及失败案例。

## Supabase业务数据库

业务表迁移文件位于 `database/migrations/001_initial_schema.sql`，包含作者、小说、流程事件、合同、结算和异常标准答案六张表。默认启用RLS并撤销 `anon`、`authenticated` 权限，只允许后端Secret访问。

1. 在Supabase Dashboard的SQL Editor执行迁移文件。
2. 在 `.env` 增加：

```dotenv
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SECRET_KEY=sb_secret_your-secret-key
```

旧项目也可以临时使用：

```dotenv
SUPABASE_SERVICE_ROLE_KEY=your-legacy-service-role-key
```

Secret或service role密钥只能放在后端，不能发送到浏览器或提交到Git。

导入50本小说（脚本直接调用 Supabase REST API，无需安装 Supabase 客户端）：

```powershell
.\.venv\Scripts\python.exe scripts\import_seed_to_supabase.py
```

配置成功后，Agent会自动使用Supabase；未配置时继续使用本地 `sample_data.json`。

## Next.js 自然语言测试页面

页面位于 `web/`，浏览器不会读取百炼或Supabase密钥。启动时需要两个PowerShell窗口。

窗口1，启动常驻Agent API：

```powershell
cd "D:\Novel Coding"
.\.venv\Scripts\python.exe scripts\serve_agent_api.py
```

窗口2，启动Next.js：

```powershell
cd "D:\Novel Coding\web"
npm.cmd install
npm.cmd run dev
```

然后访问 `http://localhost:3000`。用户无需单独输入小说ID：可以在问题中直接写书名或 `N001`，后端会自动匹配Supabase作品；纯制度问答不需要作品。页面支持意图和置信度展示、工具轨迹、RAG证据、风险报告以及LangGraph interrupt批准/拒绝。

## 安全边界

- RAG只提供制度依据，不直接执行规则。
- 金额和比例由代码核验。
- 历史制度通过生效日期过滤，避免引用错误版本。
- 未检索到规则时明确提示人工确认。
- 创建工单前必须审批；示例不会修改真实合同或付款。

## 后续升级

1. 建立RAG评测集，统计 Recall@K、MRR、Rerank增益、引用正确率和拒答率。
2. 增加管理后台，实现文档上传、版本发布、失效和增量重建索引。
3. 将JSON业务数据替换为SQLite/PostgreSQL，将向量迁移到对应向量扩展。
4. 将工单草稿持久化到Supabase，补充完整审批记录。
5. 对比 `deepseek-v4-pro` Listwise Rerank与专用Cross-Encoder的效果及成本。
