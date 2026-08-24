import React, { useEffect, useMemo, useRef, useState } from "react";
import { marked } from "marked";
import {
  cancelProposal, confirmProposal, getProposals, getSignals, streamChat,
} from "./api.js";

const PERSONAS = [
  { token: "cust-acct-001", label: "Northstar (ACCT-001)", role: "customer" },
  { token: "cust-acct-002", label: "LumenWorks (ACCT-002)", role: "customer" },
  { token: "cust-acct-003", label: "Beacon Retail (ACCT-003)", role: "customer" },
  { token: "cust-acct-004", label: "Axis Labs (ACCT-004)", role: "customer" },
  { token: "ops", label: "Internal Ops", role: "internal_ops" },
];

const TOOL_LABELS = {
  search_documents: "📄 Searching documents",
  get_order: "📦 Looking up order",
  get_account: "🏢 Looking up account",
  get_ticket: "🎫 Looking up ticket",
  list_tickets: "🎫 Listing tickets",
  calc_cancellation_fee: "🧮 Cancellation calculator",
  calc_service_credit: "🧮 Service-credit calculator",
  calc_sla: "🧮 SLA calculator",
  check_bulk_upload: "🧮 Bulk-upload check",
  create_escalation: "⚠️ Preparing escalation",
  update_ticket: "✏️ Preparing ticket update",
  create_followup_task: "✅ Preparing follow-up task",
};

const SUGGESTIONS = {
  customer: [
    "Can I cancel ORD-1001 without a cancellation fee? Explain why.",
    "A pickup was missed due to carrier fault — do I get a service credit?",
    "My 4,200-row bulk upload keeps failing. Is that over my plan limit?",
    "What's my first-response SLA if all shipment creation is down?",
  ],
  internal_ops: [
    "What issues need attention right now?",
    "Is ORD-2002 eligible for a service credit? Which contract governs?",
    "Prepare a P1 escalation for ticket TKT-501.",
    "What changed between support policy v2 and v3?",
  ],
};

export default function App() {
  const [persona, setPersona] = useState(PERSONAS[0]);
  const [tab, setTab] = useState("chat");

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand"><span className="logo">◆</span> ParcelPilot <span className="sub">Support Console</span></div>
        <div className="controls">
          <label className="persona">
            Session:
            <select value={persona.token}
              onChange={(e) => setPersona(PERSONAS.find((p) => p.token === e.target.value))}>
              {PERSONAS.map((p) => <option key={p.token} value={p.token}>{p.label}</option>)}
            </select>
          </label>
          <div className="tabs">
            <button className={tab === "chat" ? "on" : ""} onClick={() => setTab("chat")}>Chat</button>
            {persona.role === "internal_ops" &&
              <button className={tab === "ops" ? "on" : ""} onClick={() => setTab("ops")}>Ops Board</button>}
          </div>
        </div>
      </header>
      {tab === "chat"
        ? <Chat key={persona.token} persona={persona} />
        : <OpsBoard persona={persona} />}
    </div>
  );
}

function Chat({ persona }) {
  const [messages, setMessages] = useState([]);
  const [proposals, setProposals] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scroller = useRef(null);
  const history = useRef([]);

  const refreshProposals = () =>
    getProposals(persona.token).then((p) => setProposals(p.filter((x) => x.status === "pending")));

  useEffect(() => { refreshProposals(); }, [persona.token]);
  useEffect(() => { scroller.current?.scrollTo(0, scroller.current.scrollHeight); }, [messages]);

  async function send(text) {
    const q = (text ?? input).trim();
    if (!q || busy) return;
    setInput("");
    setBusy(true);
    setMessages((m) => [...m, { role: "user", content: q },
      { role: "assistant", content: "", trace: [], streaming: true, provider: "" }]);

    const update = (fn) => setMessages((m) => {
      const copy = [...m]; fn(copy[copy.length - 1]); return copy;
    });

    await streamChat(persona.token, q, history.current, (ev) => {
      if (ev.type === "tool_call") update((a) => a.trace.push({ tool: ev.tool, args: ev.args, running: true }));
      else if (ev.type === "tool_result") update((a) => {
        const step = [...a.trace].reverse().find((s) => s.tool === ev.tool && s.running);
        if (step) { step.running = false; step.result = ev.result; }
      });
      else if (ev.type === "final") update((a) => {
        a.content = ev.answer; a.streaming = false; a.provider = ev.provider;
      });
      else if (ev.type === "error") update((a) => {
        a.content = `⚠️ ${ev.detail}`; a.streaming = false;
      });
    });

    setBusy(false);
    history.current = [...history.current, { role: "user", content: q }];
    setMessages((m) => {
      const last = m[m.length - 1];
      if (last?.role === "assistant" && last.content)
        history.current = [...history.current, { role: "assistant", content: last.content }];
      return m;
    });
    refreshProposals();
  }

  async function act(id, confirm) {
    await (confirm ? confirmProposal : cancelProposal)(persona.token, id);
    refreshProposals();
  }

  return (
    <div className="chat">
      <div className="messages" ref={scroller}>
        {messages.length === 0 && (
          <div className="empty">
            <p>Ask a support question. Every fee, credit and SLA is computed by a deterministic
              tool and answers cite their governing source.</p>
            <div className="chips">
              {SUGGESTIONS[persona.role].map((s) =>
                <button key={s} className="chip" onClick={() => send(s)}>{s}</button>)}
            </div>
          </div>
        )}
        {messages.map((m, i) => <Message key={i} m={m} />)}
        {proposals.length > 0 && (
          <div className="proposals">
            {proposals.map((p) => <ConfirmCard key={p.id} p={p} onAct={act} />)}
          </div>
        )}
      </div>
      <div className="composer">
        <input value={input} placeholder="Type a message…" disabled={busy}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()} />
        <button onClick={() => send()} disabled={busy}>{busy ? "…" : "Send"}</button>
      </div>
    </div>
  );
}

function Message({ m }) {
  if (m.role === "user") return <div className="msg user"><div className="bubble">{m.content}</div></div>;
  return (
    <div className="msg assistant">
      {m.trace?.length > 0 && <Trace trace={m.trace} />}
      {m.content
        ? <div className="bubble md" dangerouslySetInnerHTML={{ __html: marked.parse(m.content) }} />
        : m.streaming && <div className="bubble thinking"><span className="dot" /><span className="dot" /><span className="dot" /></div>}
      {m.provider && <div className="provider">via {m.provider}</div>}
    </div>
  );
}

function Trace({ trace }) {
  const [open, setOpen] = useState(null);
  return (
    <div className="trace">
      {trace.map((s, i) => (
        <div key={i} className={`step ${s.running ? "running" : "done"}`}>
          <button className="stephead" onClick={() => setOpen(open === i ? null : i)}>
            <span className="tname">{TOOL_LABELS[s.tool] || s.tool}</span>
            {s.running ? <span className="spin" /> : <span className="check">✓</span>}
          </button>
          {open === i && (
            <pre className="stepbody">{JSON.stringify({ args: s.args, result: s.result }, null, 2)}</pre>
          )}
        </div>
      ))}
    </div>
  );
}

function ConfirmCard({ p, onAct }) {
  return (
    <div className="confirm">
      <div className="confirm-head">⚠️ Action needs your confirmation</div>
      <div className="confirm-kind">{p.kind.replace("_", " ")}</div>
      <div className="confirm-preview">{p.preview}</div>
      <div className="confirm-actions">
        <button className="primary" onClick={() => onAct(p.id, true)}>Confirm</button>
        <button onClick={() => onAct(p.id, false)}>Cancel</button>
      </div>
    </div>
  );
}

function OpsBoard({ persona }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => {
    getSignals(persona.token).then(setData).catch((e) => setErr(String(e)));
  }, [persona.token]);

  if (err) return <div className="ops"><p className="err">{err}</p></div>;
  if (!data) return <div className="ops"><p>Loading signals…</p></div>;

  const sevRank = (s) => (s.breached === true ? 0 : s.breached === null ? 1 : 2);
  return (
    <div className="ops">
      <div className="ops-meta">
        Snapshot {data.generated_at} · {data.totals.open} open of {data.totals.tickets} tickets
        <span className="synthlabel"> · {data.totals.synthetic} synthetic (analytics only)</span>
      </div>

      <section>
        <h2>🔥 Spikes</h2>
        {data.spikes.length === 0 ? <p className="muted">No surges detected.</p> :
          data.spikes.map((s) => (
            <div key={s.issue} className="card spike">
              <b>{s.issue.replace(/_/g, " ")}</b>: {s.recent_24h} in last 24h vs {s.baseline_prior} baseline
            </div>
          ))}
      </section>

      <section>
        <h2>👥 Multi-customer issues</h2>
        {data.multi_customer_issues.map((c) => (
          <div key={c.issue} className="card">
            <b>{c.issue.replace(/_/g, " ")}</b> {c.known_issue && <span className="ki">{c.known_issue}</span>}
            <div className="muted">{c.open_count} open across {c.distinct_accounts} accounts: {c.accounts.join(", ")}</div>
          </div>
        ))}
      </section>

      <section>
        <h2>⏱ SLA watch</h2>
        <table className="sla">
          <thead><tr><th>Ticket</th><th>Account</th><th>Issue</th><th>Sev</th><th>Target</th><th>Elapsed</th><th>Status</th></tr></thead>
          <tbody>
            {[...data.sla_watch].sort((a, b) => sevRank(a) - sevRank(b)).map((s) => (
              <tr key={s.ticket_id} className={s.breached === true ? "breach" : ""}>
                <td>{s.ticket_id}</td><td>{s.account_id}</td><td>{s.issue.replace(/_/g, " ")}</td>
                <td>{s.severity}</td><td>{s.target} <span className="cov">{s.coverage}</span></td>
                <td>{s.elapsed_minutes}m</td>
                <td>{s.breached === true ? "❌ BREACHED" : s.breached === null ? "— indeterminate" : "✓ within"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted small">Business-hours targets are marked indeterminate — the source docs never define the business calendar, so we don't guess.</p>
      </section>
    </div>
  );
}
