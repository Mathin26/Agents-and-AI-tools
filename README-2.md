# AgentForge 🤖

**Create and manage Claude-powered AI agents with up to 5 tools each — as a service.**

## Features

- 🧠 **AI-generated agents** — describe what you need in plain English; Claude designs the agent + tools
- 🔧 **5-tool limit** — each agent gets exactly the right set of tools (max 5 per Claude API limits)
- 👤 **Per-user isolation** — each user's agents and tools are stored separately
- 🔐 **Built-in auth** — register / login / session management out of the box
- 💾 **Persistent storage** — JSON-backed registry (swap for any DB in production)
- 🚀 **AgentService façade** — one object to rule them all

---

## Installation

```bash
pip install anthropic          # only hard dependency
# Then copy the agent_forge/ package into your project, or:
pip install -e .               # install from source
```

---

## Quick Start

```python
import os
from agent_forge import AgentService

svc = AgentService(api_key=os.environ["ANTHROPIC_API_KEY"])

# Register and login
user    = svc.register("alice", "alice@example.com", "pass123")
session = svc.login("alice", "pass123")

# Ask Claude to design an agent
agent, tools = svc.create_agent(
    session_id=session.session_id,
    requirement="I need an agent that monitors competitor pricing and alerts me to changes",
)

print(agent.name)          # e.g. CompetitorPricingAgent
for t in tools:
    print(t.name, "—", t.description)

# Run the agent (tools without handlers return placeholder results)
result = svc.run_agent(
    session_id=session.session_id,
    agent_name=agent.name,
    message="Check pricing for ProductX on Amazon and eBay",
)
print(result.output)
```

---

## Architecture

```
agent_forge/
├── __init__.py      # Public API exports
├── tool.py          # Tool + ToolParameter dataclasses
├── agent.py         # Agent — wraps Claude with tools & agentic loop
├── builder.py       # AgentBuilder — generates specs from natural language
├── registry.py      # AgentRegistry — per-user persistent storage
├── auth.py          # UserAuth — register / login / sessions
└── service.py       # AgentService — high-level façade
```

### Core Classes

| Class | Purpose |
|---|---|
| `Tool` | A callable tool (wraps a Python function) with Claude-compatible schema |
| `Agent` | Executes a multi-step agentic loop using Claude + tools |
| `AgentBuilder` | Calls Claude to generate Agent + Tool specs from a requirement |
| `AgentRegistry` | Stores/loads Agent & Tool definitions per user |
| `UserAuth` | Register, login, session management |
| `AgentService` | One-stop façade combining all of the above |

---

## Attaching Real Tool Handlers

```python
from agent_forge import Tool, ToolParameter, AgentService

def fetch_price(symbol: str, exchange: str) -> dict:
    # your real implementation here
    return {"symbol": symbol, "price": 142.50, "exchange": exchange}

price_tool = Tool(
    name="fetch_stock_price",
    description="Fetch the current stock price for a symbol",
    parameters=[
        ToolParameter("symbol", "string", "The stock ticker symbol"),
        ToolParameter("exchange", "string", "Exchange name e.g. NASDAQ"),
    ],
    handler=fetch_price,
)

# Attach to an agent after building
agent, _ = svc.create_agent(session_id=..., requirement="Stock monitoring agent")
agent.add_tool(price_tool)
result = agent.run("What is the price of AAPL on NASDAQ?")
```

---

## Environment Variables

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key (required) |

---

## License

MIT
