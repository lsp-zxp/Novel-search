"use client";

import { useMemo, useState } from "react";

const examples = [
  { id: "N001", label: "分成不一致", prompt: "检查《雾港来信》的结算金额和合同分成是否一致" },
  { id: "N002", label: "结算漏单", prompt: "为什么《星河修理铺》没有生成结算账单？" },
  { id: "N003", label: "重复结算", prompt: "检查《长安无名客》是否存在同一周期重复结算" },
  { id: "N004", label: "合同过期", prompt: "《春山照旧》的合同失效后是否仍然生成了结算？" },
  { id: "N043", label: "审核超时", prompt: "《雨夜末班车》AI预审通过后编辑复审是不是超时了？" },
];

const intentLabels = {
  settlement_audit: "结算异常检查",
  contract_audit: "合同有效性检查",
  review_sla: "审核时效检查",
  policy_lookup: "制度查询",
  full_audit: "全量业务巡检",
};

const toolLabels = {
  get_novel_context: "读取作品与流程",
  get_contract_terms: "读取合同条款",
  get_settlement_summary: "读取结算数据",
  retrieve_policy: "检索适用制度",
  check_settlement_consistency: "核验分成与金额",
  check_missing_settlement: "检查结算漏单",
  check_duplicate_settlement: "检查重复结算",
  check_contract_validity: "检查合同有效期",
  check_review_sla: "检查审核SLA",
};

const anomalyLabels = {
  settlement_ratio_mismatch: "结算分成不一致",
  missing_bill: "结算漏单",
  duplicate_settlement: "重复结算",
  expired_contract_settlement: "失效合同结算",
  editor_review_overdue: "编辑复审超时",
};

function formatMoney(value) {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
  }).format(Number(value || 0));
}

function InvestigationResult({ data, onApprove, approving }) {
  const { intent = {}, plan = [], traces = [], report = {}, case: caseInfo } = data;
  const riskClass = report.risk_level === "high" ? "danger" : report.risk_level === "medium" ? "warning" : "safe";

  return (
    <article className="result-stack">
      <section className="result-card intent-card">
        <div>
          <span className="eyebrow">意图识别</span>
          <h2>{intentLabels[intent.intent] || intent.intent || "未识别"}</h2>
          <p>{intent.normalized_request || "—"}</p>
          {data.target?.title && (
            <span className="resolved-target">
              已匹配：{data.target.title}{data.target.id ? ` · ${data.target.id}` : ""}
            </span>
          )}
        </div>
        <div className="confidence">
          <strong>{Math.round((intent.confidence || 0) * 100)}%</strong>
          <span>置信度</span>
        </div>
      </section>

      <section className="result-card">
        <div className="section-heading">
          <div>
            <span className="eyebrow">执行计划</span>
            <h3>{plan.length} 个步骤已完成</h3>
          </div>
          <span className="status-dot">可审计</span>
        </div>
        <ol className="plan-list">
          {plan.map((tool, index) => {
            const trace = traces.find((item) => item.tool === tool);
            return (
              <li key={`${tool}-${index}`}>
                <span className={trace?.ok ? "step-index done" : "step-index failed"}>
                  {trace?.ok ? "✓" : "!"}
                </span>
                <div>
                  <strong>{toolLabels[tool] || tool}</strong>
                  <span>{trace?.ok ? "执行成功" : trace?.result?.error || "未执行"}</span>
                </div>
              </li>
            );
          })}
        </ol>
      </section>

      <section className={`report-card ${riskClass}`}>
        <div className="report-topline">
          <span className={`risk-badge ${riskClass}`}>
            {report.anomaly_type === "none" ? "未发现异常" : `${report.risk_level || "—"} risk`}
          </span>
          <span className="anomaly-code">{report.anomaly_type || "—"}</span>
        </div>
        <h2>{report.conclusion || "调查完成"}</h2>
        <div className="impact-row">
          <span>受影响金额</span>
          <strong>{formatMoney(report.affected_amount)}</strong>
        </div>
        <div className="recommendation">
          <span>处理建议</span>
          <p>{report.recommendation || "保留调查记录。"}</p>
        </div>
      </section>

      {report.anomalies?.length > 1 && (
        <section className="result-card anomalies-card">
          <div className="section-heading">
            <div>
              <span className="eyebrow">风险明细</span>
              <h3>共检测到 {report.anomalies.length} 处异常</h3>
            </div>
            <span className="status-dot">全部命中</span>
          </div>
          <ul className="anomaly-list">
            {report.anomalies.map((item, index) => {
              const risk = item.risk_level === "high" ? "danger" : item.risk_level === "medium" ? "warning" : "safe";
              return (
                <li key={`${item.anomaly_type}-${index}`}>
                  <span className={`risk-badge ${risk}`}>{item.risk_level}</span>
                  <div>
                    <strong>{anomalyLabels[item.anomaly_type] || item.anomaly_type}</strong>
                    <span className="anomaly-code">{item.anomaly_type}</span>
                    <p>{item.conclusion}</p>
                    <p className="anomaly-impact">影响金额 {formatMoney(item.affected_amount)}</p>
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {!!report.evidence?.length && (
        <details className="result-card evidence-card" open>
          <summary>证据与制度引用 · {report.evidence.length} 条</summary>
          <ul>
            {report.evidence.map((item, index) => (
              <li key={index}><span>{index + 1}</span><p>{item}</p></li>
            ))}
          </ul>
        </details>
      )}

      {data.requires_approval && !caseInfo && (
        <section className="approval-card">
          <div>
            <span className="eyebrow">Human in the loop</span>
            <h3>是否批准创建处理工单？</h3>
            <p>Agent已暂停，等待你的决定。审批不会修改合同或付款数据。</p>
          </div>
          <div className="approval-actions">
            <button className="button secondary" disabled={approving} onClick={() => onApprove(false)}>
              拒绝
            </button>
            <button className="button primary" disabled={approving} onClick={() => onApprove(true)}>
              {approving ? "处理中…" : "批准创建草稿"}
            </button>
          </div>
        </section>
      )}

      {caseInfo && (
        <section className="case-card">
          <span className="case-check">✓</span>
          <div>
            <span className="eyebrow">工单草稿已生成</span>
            <h3>{caseInfo.id}</h3>
            <p>{caseInfo.summary}</p>
          </div>
        </section>
      )}
    </article>
  );
}

export default function Home() {
  const [request, setRequest] = useState("检查《雾港来信》的结算金额和合同分成是否一致");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState("");

  const canSubmit = useMemo(() => request.trim() && !loading, [request, loading]);

  async function investigate(event) {
    event?.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const response = await fetch("/api/investigate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request: request.trim() }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "调查失败");
      setResult(data);
    } catch (err) {
      setError(err.message || "调查失败");
    } finally {
      setLoading(false);
    }
  }

  async function approve(approved) {
    if (!result?.thread_id) return;
    setApproving(true);
    setError("");
    try {
      const response = await fetch("/api/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ thread_id: result.thread_id, approved }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "审批失败");
      setResult({ ...result, ...data, requires_approval: false });
    } catch (err) {
      setError(err.message || "审批失败");
    } finally {
      setApproving(false);
    }
  }

  function applyExample(example) {
    setRequest(example.prompt);
    setResult(null);
    setError("");
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-mark">N</div>
        <div className="brand-copy">
          <strong>NovelOps AI</strong>
          <span>小说业务异常调查 Agent</span>
        </div>
        <div className="runtime-status"><span /> DeepSeek · Hybrid RAG</div>
      </header>

      <div className="workspace">
        <aside className="sidebar">
          <div>
            <span className="eyebrow">测试案例</span>
            <h1>用自然语言<br />调查业务异常</h1>
            <p className="sidebar-intro">直接说出书名和你想调查的问题，Agent会自动匹配作品。</p>
          </div>
          <nav className="example-list" aria-label="测试案例">
            {examples.map((example) => (
              <button
                key={example.id}
                className={request === example.prompt ? "example active" : "example"}
                onClick={() => applyExample(example)}
              >
                <span>{example.id}</span>
                <strong>{example.label}</strong>
              </button>
            ))}
          </nav>
          <div className="safety-note">
            <span>安全边界</span>
            <p>报告由证据与规则驱动。所有工单操作均需人工确认。</p>
          </div>
        </aside>

        <section className="main-panel">
          <div className="conversation-head">
            <div>
              <span className="eyebrow">Investigation workspace</span>
              <h2>发起一次调查</h2>
            </div>
            <span className="data-source">Supabase 已连接</span>
          </div>

          <form className="composer" onSubmit={investigate}>
            <label className="request-field request-only">
              <span>你想调查什么？</span>
              <textarea
                value={request}
                onChange={(event) => setRequest(event.target.value)}
                placeholder="例如：检查《雾港来信》为什么没有生成9月结算单"
                rows={3}
                onKeyDown={(event) => {
                  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") investigate(event);
                }}
              />
            </label>
            <div className="composer-footer">
              <span>Ctrl + Enter 发送</span>
              <button className="button primary submit" disabled={!canSubmit} type="submit">
                {loading ? "Agent调查中…" : "开始调查"}
              </button>
            </div>
          </form>

          {loading && (
            <div className="loading-card" role="status">
              <div className="loading-orbit"><span /><span /><span /></div>
              <div><strong>Agent正在调查</strong><p>识别意图、查询业务数据、检索制度并执行规则检查…</p></div>
            </div>
          )}

          {error && <div className="error-banner" role="alert">{error}</div>}
          {result && <InvestigationResult data={result} onApprove={approve} approving={approving} />}

          {!loading && !result && !error && (
            <div className="empty-state">
              <div className="flow-preview">
                <span>意图识别</span><i>→</i><span>场景路由</span><i>→</i><span>证据调查</span><i>→</i><span>人工审批</span>
              </div>
              <p>调查结果会在这里显示，包括每一步工具执行结果。</p>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
