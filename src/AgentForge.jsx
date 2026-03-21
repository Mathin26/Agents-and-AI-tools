import { useState, useEffect, useRef } from "react";

// ─── Inline CSS (injected once) ───────────────────────────────────────────────
const GLOBAL_CSS = `
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #09090f;
  --surface: #111118;
  --surface2: #18181f;
  --border: #2a2a38;
  --accent: #7c6af7;
  --accent2: #e96bf5;
  --accent3: #4fd1c5;
  --text: #e8e8f0;
  --muted: #6b6b80;
  --danger: #f56565;
  --success: #48bb78;
  --font-body: 'Syne', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  --radius: 12px;
  --glow: 0 0 40px rgba(124, 106, 247, 0.15);
}

body { background: var(--bg); color: var(--text); font-family: var(--font-body); }

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--surface); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(20px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes pulse-ring {
  0%   { transform: scale(0.8); opacity: 0.8; }
  100% { transform: scale(1.4); opacity: 0; }
}
@keyframes shimmer {
  0%   { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes blink { 50% { opacity: 0; } }

.animate-in { animation: fadeUp 0.4s ease both; }

.spinner {
  width: 20px; height: 20px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: inline-block;
}

.gradient-text {
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.mesh-bg {
  position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background:
    radial-gradient(ellipse 60% 50% at 20% 20%, rgba(124,106,247,0.08) 0%, transparent 70%),
    radial-gradient(ellipse 50% 60% at 80% 80%, rgba(233,107,245,0.06) 0%, transparent 70%),
    radial-gradient(ellipse 40% 40% at 60% 10%, rgba(79,209,197,0.05) 0%, transparent 70%);
}
`;

function injectCSS() {
  if (document.getElementById("af-styles")) return;
  const s = document.createElement("style");
  s.id = "af-styles";
  s.textContent = GLOBAL_CSS;
  document.head.appendChild(s);
}

// ─── Claude API helper ────────────────────────────────────────────────────────
const BUILDER_SYSTEM = `You are AgentForge. Design AI agents from user requirements.

OUTPUT RULES - STRICTLY FOLLOW:
1. Respond with ONLY a JSON object. No text before or after.
2. Do NOT use markdown code fences or backticks.
3. Start your response with { and end with }.
4. Keep all descriptions under 12 words.
5. Maximum 3 tools per agent to keep response compact.
6. system_prompt must be 2 sentences maximum.

Required JSON shape (replace values, keep structure):
{"agent":{"name":"CamelCaseName","description":"short desc","category":"general","tags":[],"system_prompt":"Two sentences.","emoji":"single emoji"},"tools":[{"name":"tool_name","description":"short desc","icon":"single emoji","parameters":[{"name":"input","type":"string","description":"desc","required":true}]}]}

Allowed categories: productivity, research, data, communication, code, creative, finance, general
Allowed param types: string, number, boolean`;

async function callClaude(messages, system = BUILDER_SYSTEM) {
  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "claude-sonnet-4-5",
      max_tokens: 2000,
      system,
      messages,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.error?.message || `API error ${res.status}`);
  }
  const data = await res.json();
  return data.content?.[0]?.text || "";
}

// ─── Simple in-memory "database" ─────────────────────────────────────────────
const DB = {
  users: {},    // username → { username, email, passwordHash, userId, createdAt }
  sessions: {}, // sessionId → userId
  agents: {},   // userId → [agentSpec, ...]
};

function simpleHash(str) {
  let h = 0;
  for (const c of str) h = (Math.imul(31, h) + c.charCodeAt(0)) | 0;
  return h.toString(16);
}
function uid() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

// ─── Shared UI atoms ─────────────────────────────────────────────────────────
const Btn = ({ children, onClick, variant = "primary", disabled, loading, style = {} }) => {
  const base = {
    display: "inline-flex", alignItems: "center", gap: 8, fontFamily: "var(--font-body)",
    fontWeight: 700, fontSize: 14, padding: "10px 20px", borderRadius: "var(--radius)",
    border: "none", cursor: disabled || loading ? "not-allowed" : "pointer",
    transition: "all 0.2s", opacity: disabled || loading ? 0.5 : 1, ...style,
  };
  const vars = {
    primary: { background: "var(--accent)", color: "#fff" },
    ghost: { background: "transparent", color: "var(--muted)", border: "1px solid var(--border)" },
    danger: { background: "rgba(245,101,101,0.12)", color: "var(--danger)", border: "1px solid rgba(245,101,101,0.3)" },
    success: { background: "rgba(72,187,120,0.12)", color: "var(--success)", border: "1px solid rgba(72,187,120,0.3)" },
  };
  return (
    <button onClick={disabled || loading ? undefined : onClick} style={{ ...base, ...vars[variant] }}>
      {loading && <span className="spinner" />}
      {children}
    </button>
  );
};

const Input = ({ label, value, onChange, type = "text", placeholder, error }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
    {label && <label style={{ fontSize: 12, fontWeight: 600, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>{label}</label>}
    <input
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      style={{
        background: "var(--surface2)", border: `1px solid ${error ? "var(--danger)" : "var(--border)"}`,
        borderRadius: 8, padding: "10px 14px", color: "var(--text)", fontSize: 14,
        fontFamily: "var(--font-body)", outline: "none", transition: "border-color 0.2s",
        width: "100%",
      }}
    />
    {error && <span style={{ fontSize: 12, color: "var(--danger)" }}>{error}</span>}
  </div>
);

const Tag = ({ children, color = "var(--accent)" }) => (
  <span style={{
    fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 20,
    background: `${color}20`, color, border: `1px solid ${color}40`,
    textTransform: "uppercase", letterSpacing: "0.06em",
  }}>{children}</span>
);

// ─── Login / Register Screen ──────────────────────────────────────────────────
function AuthScreen({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setError(""); setLoading(true);
    try {
      if (mode === "register") {
        if (!username || !email || !password) throw new Error("All fields are required.");
        if (DB.users[username]) throw new Error("Username already taken.");
        const userId = uid();
        DB.users[username] = { username, email, passwordHash: simpleHash(password), userId, createdAt: Date.now() };
        DB.agents[userId] = [];
      }
      // Login
      const user = DB.users[username];
      if (!user) throw new Error("User not found.");
      if (user.passwordHash !== simpleHash(password)) throw new Error("Incorrect password.");
      const sessionId = uid();
      DB.sessions[sessionId] = user.userId;
      onLogin({ user, sessionId });
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", position: "relative" }}>
      <div className="mesh-bg" />
      <div className="animate-in" style={{ position: "relative", zIndex: 1, width: "100%", maxWidth: 420, padding: "0 20px" }}>
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>⚡</div>
          <h1 style={{ fontSize: 32, fontWeight: 800, letterSpacing: "-0.02em" }}>
            <span className="gradient-text">AgentForge</span>
          </h1>
          <p style={{ color: "var(--muted)", fontSize: 14, marginTop: 8 }}>
            Build Claude-powered AI agents in seconds
          </p>
        </div>

        {/* Card */}
        <div style={{
          background: "var(--surface)", border: "1px solid var(--border)",
          borderRadius: 20, padding: 32, boxShadow: "var(--glow)",
        }}>
          {/* Tabs */}
          <div style={{ display: "flex", background: "var(--surface2)", borderRadius: 10, padding: 4, marginBottom: 28 }}>
            {["login", "register"].map(m => (
              <button key={m} onClick={() => { setMode(m); setError(""); }} style={{
                flex: 1, padding: "8px 0", border: "none", borderRadius: 8, cursor: "pointer",
                background: mode === m ? "var(--accent)" : "transparent",
                color: mode === m ? "#fff" : "var(--muted)",
                fontFamily: "var(--font-body)", fontWeight: 700, fontSize: 14,
                transition: "all 0.2s", textTransform: "capitalize",
              }}>{m}</button>
            ))}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Input label="Username" value={username} onChange={setUsername} placeholder="your_username" />
            {mode === "register" && <Input label="Email" value={email} onChange={setEmail} type="email" placeholder="you@example.com" />}
            <Input label="Password" value={password} onChange={setPassword} type="password" placeholder="••••••••" />
            {error && <div style={{ fontSize: 13, color: "var(--danger)", background: "rgba(245,101,101,0.08)", borderRadius: 8, padding: "8px 12px" }}>{error}</div>}
            <Btn onClick={handleSubmit} loading={loading} style={{ width: "100%", justifyContent: "center", marginTop: 4 }}>
              {mode === "login" ? "Sign In →" : "Create Account →"}
            </Btn>
          </div>

          {mode === "login" && (
            <p style={{ textAlign: "center", marginTop: 16, fontSize: 12, color: "var(--muted)" }}>
              Demo: register first, then log in
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Agent Card ───────────────────────────────────────────────────────────────
function AgentCard({ agent, onDelete, onChat }) {
  const categoryColors = {
    productivity: "#f6ad55", research: "#68d391", data: "#4fd1c5",
    communication: "#76e4f7", code: "#9f7aea", creative: "#e96bf5",
    finance: "#ffd700", general: "var(--accent)",
  };
  const color = categoryColors[agent.category] || "var(--accent)";

  return (
    <div style={{
      background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 16,
      padding: 20, transition: "all 0.2s", cursor: "default",
    }}
      onMouseEnter={e => e.currentTarget.style.borderColor = "var(--accent)"}
      onMouseLeave={e => e.currentTarget.style.borderColor = "var(--border)"}
    >
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 28 }}>{agent.emoji || "🤖"}</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15 }}>{agent.name}</div>
            <Tag color={color}>{agent.category}</Tag>
          </div>
        </div>
        <Btn variant="danger" onClick={() => onDelete(agent.name)} style={{ padding: "4px 10px", fontSize: 12 }}>✕</Btn>
      </div>

      <p style={{ fontSize: 13, color: "var(--muted)", lineHeight: 1.5, marginBottom: 14 }}>{agent.description}</p>

      {/* Tools */}
      <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 16 }}>
        {agent.tools.map(t => (
          <div key={t.name} style={{
            display: "flex", alignItems: "center", gap: 8,
            background: "var(--surface2)", borderRadius: 8, padding: "6px 10px",
          }}>
            <span style={{ fontSize: 14 }}>{t.icon || "🔧"}</span>
            <div>
              <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text)", fontFamily: "var(--font-mono)" }}>{t.name}</span>
              <span style={{ fontSize: 11, color: "var(--muted)", marginLeft: 6 }}>{t.description}</span>
            </div>
          </div>
        ))}
      </div>

      <Btn variant="success" onClick={() => onChat(agent)} style={{ width: "100%", justifyContent: "center", fontSize: 13 }}>
        💬 Chat with Agent
      </Btn>
    </div>
  );
}

// ─── Chat Panel ───────────────────────────────────────────────────────────────
function ChatPanel({ agent, onClose }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg = { role: "user", content: input.trim() };
    const history = [...messages, userMsg];
    setMessages(history);
    setInput("");
    setLoading(true);

    try {
      const toolDesc = agent.tools.map(t =>
        `${t.icon || "🔧"} ${t.name}: ${t.description} (params: ${t.parameters?.map(p => p.name).join(", ") || "none"})`
      ).join("\n");

      const systemPrompt = `${agent.system_prompt}\n\nYou have access to these tools (describe how you would use them):\n${toolDesc}\n\nNote: In this demo, tools are simulated — describe your reasoning and what result you'd expect.`;

      const apiMessages = history.map(m => ({ role: m.role, content: m.content }));
      const reply = await callClaude(apiMessages, systemPrompt);
      setMessages(prev => [...prev, { role: "assistant", content: reply }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: "assistant", content: `⚠️ Error: ${e.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", zIndex: 100,
      display: "flex", alignItems: "center", justifyContent: "center", padding: 20,
    }}>
      <div className="animate-in" style={{
        background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 20,
        width: "100%", maxWidth: 640, height: "80vh", display: "flex", flexDirection: "column",
        boxShadow: "0 20px 80px rgba(0,0,0,0.6)",
      }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 20px", borderBottom: "1px solid var(--border)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 24 }}>{agent.emoji || "🤖"}</span>
            <div>
              <div style={{ fontWeight: 700 }}>{agent.name}</div>
              <div style={{ fontSize: 12, color: "var(--muted)" }}>{agent.tools.length} tools active</div>
            </div>
          </div>
          <Btn variant="ghost" onClick={onClose} style={{ padding: "6px 12px" }}>✕ Close</Btn>
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: "auto", padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
          {messages.length === 0 && (
            <div style={{ textAlign: "center", color: "var(--muted)", marginTop: 40 }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>{agent.emoji || "🤖"}</div>
              <p style={{ fontSize: 14 }}>Start a conversation with <strong>{agent.name}</strong></p>
              <p style={{ fontSize: 12, marginTop: 4 }}>{agent.description}</p>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} style={{ display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}>
              <div style={{
                maxWidth: "80%", padding: "10px 14px", borderRadius: 14,
                background: m.role === "user" ? "var(--accent)" : "var(--surface2)",
                color: "var(--text)", fontSize: 14, lineHeight: 1.6,
                borderBottomRightRadius: m.role === "user" ? 4 : 14,
                borderBottomLeftRadius: m.role === "assistant" ? 4 : 14,
                whiteSpace: "pre-wrap",
              }}>
                {m.content}
              </div>
            </div>
          ))}
          {loading && (
            <div style={{ display: "flex", gap: 6, padding: "6px 14px", background: "var(--surface2)", borderRadius: 14, alignSelf: "flex-start", width: "fit-content" }}>
              {[0, 1, 2].map(i => (
                <div key={i} style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--muted)", animation: `blink 1.2s ${i * 0.2}s infinite` }} />
              ))}
            </div>
          )}
          <div ref={endRef} />
        </div>

        {/* Input */}
        <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)", display: "flex", gap: 10 }}>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && !e.shiftKey && send()}
            placeholder="Message the agent..."
            style={{
              flex: 1, background: "var(--surface2)", border: "1px solid var(--border)",
              borderRadius: 10, padding: "10px 14px", color: "var(--text)",
              fontFamily: "var(--font-body)", fontSize: 14, outline: "none",
            }}
          />
          <Btn onClick={send} loading={loading} disabled={!input.trim()}>Send ↑</Btn>
        </div>
      </div>
    </div>
  );
}

// ─── Builder Panel ────────────────────────────────────────────────────────────
function BuilderPanel({ onBuild }) {
  const [requirement, setRequirement] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const examples = [
    "An agent that researches companies and summarises news about them",
    "A coding assistant that reviews code, suggests improvements and writes tests",
    "A social media manager that drafts posts and analyses engagement",
    "A financial analyst that tracks stocks and generates reports",
    "A customer support agent that answers FAQs and escalates issues",
  ];

  const extractJSON = (raw) => {
    // Attempt 1: direct parse
    try { return JSON.parse(raw.trim()); } catch {}
    // Attempt 2: strip markdown fences
    const stripped = raw.replace(/```json\s*/gi, "").replace(/```\s*/g, "").trim();
    try { return JSON.parse(stripped); } catch {}
    // Attempt 3: find first { to last }
    const start = raw.indexOf("{");
    const end = raw.lastIndexOf("}");
    if (start !== -1 && end !== -1 && end > start) {
      try { return JSON.parse(raw.slice(start, end + 1)); } catch {}
    }
    // Attempt 4: extract from code blocks
    const blocks = [...raw.matchAll(/```(?:json)?\s*([\s\S]*?)```/gi)];
    for (const b of blocks) {
      try { return JSON.parse(b[1].trim()); } catch {}
    }
    return null;
  };

  const handleBuild = async () => {
    if (!requirement.trim()) return;
    setError(""); setLoading(true);
    try {
      const raw = await callClaude([{ role: "user", content: requirement }], BUILDER_SYSTEM);
      const spec = extractJSON(raw);
      if (!spec) {
        console.error("Raw API response:", raw);
        throw new Error("Could not parse response. Please try again.");
      }
      // Ensure required fields exist with fallbacks
      if (!spec.agent) spec.agent = {};
      if (!spec.tools) spec.tools = [];
      if (!spec.agent.name) spec.agent.name = "CustomAgent";
      if (!spec.agent.description) spec.agent.description = "A custom AI agent.";
      if (!spec.agent.category) spec.agent.category = "general";
      if (!spec.agent.emoji) spec.agent.emoji = "🤖";
      if (!spec.agent.system_prompt) spec.agent.system_prompt = "You are a helpful AI assistant.";
      onBuild(spec);
      setRequirement("");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 20, padding: 28, marginBottom: 32 }}>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 20, fontWeight: 800, marginBottom: 6 }}>✨ Create a New Agent</h2>
        <p style={{ fontSize: 13, color: "var(--muted)" }}>Describe what you need — Claude will design the agent and its tools automatically.</p>
      </div>

      <textarea
        value={requirement}
        onChange={e => setRequirement(e.target.value)}
        placeholder="Describe the agent you need in plain English..."
        rows={3}
        style={{
          width: "100%", background: "var(--surface2)", border: "1px solid var(--border)",
          borderRadius: 10, padding: "12px 14px", color: "var(--text)", fontFamily: "var(--font-body)",
          fontSize: 14, resize: "none", outline: "none", lineHeight: 1.6, marginBottom: 12,
        }}
      />

      {/* Example chips */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 16 }}>
        {examples.map((ex, i) => (
          <button key={i} onClick={() => setRequirement(ex)} style={{
            fontSize: 11, padding: "4px 10px", borderRadius: 20, border: "1px solid var(--border)",
            background: "transparent", color: "var(--muted)", cursor: "pointer", fontFamily: "var(--font-body)",
            transition: "all 0.15s",
          }}
            onMouseEnter={e => { e.target.style.borderColor = "var(--accent)"; e.target.style.color = "var(--accent)"; }}
            onMouseLeave={e => { e.target.style.borderColor = "var(--border)"; e.target.style.color = "var(--muted)"; }}
          >
            {ex.slice(0, 40)}…
          </button>
        ))}
      </div>

      {error && <div style={{ fontSize: 13, color: "var(--danger)", background: "rgba(245,101,101,0.08)", borderRadius: 8, padding: "8px 12px", marginBottom: 12 }}>{error}</div>}

      <Btn onClick={handleBuild} loading={loading} disabled={!requirement.trim()}>
        ⚡ Generate Agent
      </Btn>
    </div>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────
function Dashboard({ user, sessionId, onLogout }) {
  const [agents, setAgents] = useState(DB.agents[user.userId] || []);
  const [chatAgent, setChatAgent] = useState(null);
  const [toast, setToast] = useState(null);

  const showToast = (msg, type = "success") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const handleBuild = (spec) => {
    const newAgent = {
      name: spec.agent.name,
      description: spec.agent.description,
      category: spec.agent.category,
      emoji: spec.agent.emoji || "🤖",
      tags: spec.agent.tags || [],
      system_prompt: spec.agent.system_prompt,
      tools: (spec.tools || []).slice(0, 5),
    };
    const updated = [...agents, newAgent];
    setAgents(updated);
    DB.agents[user.userId] = updated;
    showToast(`✨ ${newAgent.name} created with ${newAgent.tools.length} tools!`);
  };

  const handleDelete = (name) => {
    const updated = agents.filter(a => a.name !== name);
    setAgents(updated);
    DB.agents[user.userId] = updated;
    showToast(`Deleted ${name}`, "danger");
  };

  const categoryCount = agents.reduce((acc, a) => {
    acc[a.category] = (acc[a.category] || 0) + 1;
    return acc;
  }, {});

  return (
    <div style={{ minHeight: "100vh", position: "relative" }}>
      <div className="mesh-bg" />

      {/* Topbar */}
      <div style={{
        position: "sticky", top: 0, zIndex: 50,
        background: "rgba(9,9,15,0.85)", backdropFilter: "blur(12px)",
        borderBottom: "1px solid var(--border)", padding: "0 24px",
      }}>
        <div style={{ maxWidth: 1100, margin: "0 auto", height: 60, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ fontSize: 22 }}>⚡</span>
            <span style={{ fontWeight: 800, fontSize: 18, letterSpacing: "-0.02em" }}>
              Agent<span className="gradient-text">Forge</span>
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div style={{ fontSize: 13, color: "var(--muted)" }}>
              👤 <strong style={{ color: "var(--text)" }}>{user.username}</strong>
            </div>
            <Btn variant="ghost" onClick={onLogout} style={{ padding: "6px 14px", fontSize: 13 }}>Sign Out</Btn>
          </div>
        </div>
      </div>

      {/* Content */}
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "32px 24px", position: "relative", zIndex: 1 }}>

        {/* Stats bar */}
        <div style={{ display: "flex", gap: 16, marginBottom: 32, flexWrap: "wrap" }}>
          {[
            {label: "Can use only 2 agents", value: agents.length,},
            { label: "Agents", value: agents.length, icon: "🤖" },
            { label: "Total Tools", value: agents.reduce((s, a) => s + a.tools.length, 0), icon: "🔧" },
            { label: "Categories", value: Object.keys(categoryCount).length, icon: "📂" },
          ].map(s => (
            <div key={s.label} style={{
              flex: "1 1 140px", background: "var(--surface)", border: "1px solid var(--border)",
              borderRadius: 12, padding: "16px 20px",
            }}>
              <div style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>
                {s.icon} {s.label}
              </div>
              <div style={{ fontSize: 28, fontWeight: 800 }}>{s.value}</div>
            </div>
          ))}
        </div>

        {/* Builder */}
        <BuilderPanel onBuild={handleBuild} />

        {/* Agent grid */}
        {agents.length === 0 ? (
          <div style={{ textAlign: "center", padding: "60px 0", color: "var(--muted)" }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>🚀</div>
            <p style={{ fontSize: 16, fontWeight: 600 }}>No agents yet</p>
            <p style={{ fontSize: 13, marginTop: 6 }}>Describe what you need above and let Claude build your first agent.</p>
          </div>
        ) : (
          <>
            <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16, color: "var(--muted)" }}>
              YOUR AGENTS ({agents.length})
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 16 }}>
              {agents.map((a, i) => (
                <div key={a.name} className="animate-in" style={{ animationDelay: `${i * 0.05}s` }}>
                  <AgentCard agent={a} onDelete={handleDelete} onChat={setChatAgent} />
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Chat panel */}
      {chatAgent && <ChatPanel agent={chatAgent} onClose={() => setChatAgent(null)} />}

      {/* Toast */}
      {toast && (
        <div style={{
          position: "fixed", bottom: 24, right: 24, zIndex: 200,
          background: toast.type === "danger" ? "rgba(245,101,101,0.15)" : "rgba(72,187,120,0.15)",
          border: `1px solid ${toast.type === "danger" ? "var(--danger)" : "var(--success)"}`,
          borderRadius: 12, padding: "12px 18px", fontSize: 13, fontWeight: 600,
          color: toast.type === "danger" ? "var(--danger)" : "var(--success)",
          animation: "fadeUp 0.3s ease",
        }}>
          {toast.msg}
        </div>
      )}
    </div>
  );
}

// ─── Root App ─────────────────────────────────────────────────────────────────
export default function App() {
  injectCSS();
  const [session, setSession] = useState(null); // { user, sessionId }

  if (!session) {
    return <AuthScreen onLogin={setSession} />;
  }

  return (
    <Dashboard
      user={session.user}
      sessionId={session.sessionId}
      onLogout={() => setSession(null)}
    />
  );
}
