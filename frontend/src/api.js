// Thin API client. The bearer token encodes the persona (server-side session);
// the account_id is never sent by the client (Rule 4).

const auth = (token) => ({ Authorization: `Bearer ${token}` });

export async function getMe(token) {
  const r = await fetch("/me", { headers: auth(token) });
  if (!r.ok) throw new Error("auth failed");
  return r.json();
}

export async function getSignals(token) {
  const r = await fetch("/ops/signals", { headers: auth(token) });
  if (!r.ok) throw new Error(`signals ${r.status}`);
  return r.json();
}

export async function getProposals(token) {
  const r = await fetch("/proposals", { headers: auth(token) });
  return r.ok ? (await r.json()).proposals : [];
}

export async function confirmProposal(token, id) {
  const r = await fetch(`/proposals/${id}/confirm`, { method: "POST", headers: auth(token) });
  return r.json();
}

export async function cancelProposal(token, id) {
  const r = await fetch(`/proposals/${id}/cancel`, { method: "POST", headers: auth(token) });
  return r.json();
}

// Stream a chat turn. Calls onEvent for each SSE event:
//   {type:"tool_call",tool,args} | {type:"tool_result",tool,result}
//   {type:"final",answer,iterations,provider} | {type:"error",detail}
export async function streamChat(token, message, history, onEvent) {
  const resp = await fetch("/chat/stream", {
    method: "POST",
    headers: { ...auth(token), "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });
  if (!resp.ok || !resp.body) {
    onEvent({ type: "error", detail: `HTTP ${resp.status}` });
    return;
  }
  const reader = resp.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop();
    for (const part of parts) {
      const line = part.split("\n").find((l) => l.startsWith("data:"));
      if (line) {
        try { onEvent(JSON.parse(line.slice(5).trim())); } catch (_) {}
      }
    }
  }
}
