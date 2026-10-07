# 50本小说模拟数据

本目录由 `scripts/generate_seed_data.py` 生成，数据为原创虚构内容，仅用于产品演示和测试。

## 数据表

- `authors.csv`：作者主数据。
- `novels.csv`：50本小说主数据。
- `workflow_events.csv`：投稿、审核、签约、发布、结算状态事件。
- `contracts.csv`：已签约作品的合同数据。
- `settlements.csv`：2026年9月结算数据。
- `expected_anomalies.csv`：用于评测Agent的异常标准答案。
- `novelops_seed_50.json`：以上所有表的单文件JSON版本。

CSV使用UTF-8 BOM编码，可直接用Excel打开。表之间通过 `author_id`、`novel_id`、`contract_id` 关联。空字符串表示可空字段，方便后续转换为数据库的 `NULL`。

重新生成：

```powershell
.\.venv\Scripts\python.exe scripts\generate_seed_data.py
```
