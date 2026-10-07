# 待补官方来源

以下规则已根据用户提供内容整理入库，但尚未提供原始页面链接。对外展示或作为自动决策依据前，应补充官方来源并人工核验。

| 文档ID | 平台 | 待补内容 |
|---|---|---|
| `fanqie-settlement-income-2025-2026` | 番茄小说 | 稿费构成、打赏分成、结算周期官方页面 |
| `fanqie-attendance-2026-10` | 番茄小说 | 2026年10月全勤新规公告 |
| `fanqie-settlement-anomaly-reference-2025-2026` | 番茄小说 | 预估收益、渠道费、提现规则说明 |
| `fanqie-contract-2026-09` | 番茄小说 | 完本签约模式官方公告 |
| `jinjiang-contract-reference-2026` | 晋江文学城 | 作者签约协议或官方帮助页面 |
| `platform-contract-review-sla-reference-2026` | 跨平台 | 两个平台的官方审核时效页面；经验数据需单独标为非官方 |
| `fanqie-completed-review-2026-09` | 番茄小说 | 完本签约三个审核环节官方说明 |
| `fanqie-low-quality-2026-05` | 番茄小说 | 低质内容治理公告及2026年6月治理数据来源 |

补录步骤：

1. 在 `catalog.json` 对应记录填写 `source_url`。
2. 若原文与当前整理内容一致，将 `verification_status` 改为 `verified_official`。
3. 若只能找到媒体或作者经验内容，保留 `pending_official_source`，并将 `source_type` 标成实际来源类型。
4. 记录页面发布日期和规则生效时间；两者不一定相同。
5. 保存页面标题和必要短摘录，不要整页复制受版权保护的内容。
