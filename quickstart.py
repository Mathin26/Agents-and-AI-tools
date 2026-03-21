"""
examples/quickstart.py — End-to-end demo of the AgentForge library.

Set ANTHROPIC_API_KEY before running:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python examples/quickstart.py
"""

import os
import sys

# Allow running from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent_forge import AgentService


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠  Set ANTHROPIC_API_KEY environment variable first.")
        sys.exit(1)

    # ---------------------------------------------------------------
    # 1. Create the service
    # ---------------------------------------------------------------
    svc = AgentService(api_key=api_key, data_dir="./quickstart_data")

    # ---------------------------------------------------------------
    # 2. Register + login a user
    # ---------------------------------------------------------------
    try:
        user = svc.register("demo_user", "demo@example.com", "password123")
        print(f"✅  Registered user: {user.username}  (id={user.user_id})")
    except ValueError:
        print("ℹ  User already exists, logging in ...")

    session = svc.login("demo_user", "password123")
    print(f"✅  Session: {session.session_id[:16]}...")

    # ---------------------------------------------------------------
    # 3. Ask Claude to design an agent
    # ---------------------------------------------------------------
    requirement = (
        "I need an agent that helps me analyse stock market data. "
        "It should be able to fetch stock prices, calculate moving averages, "
        "identify trends, and generate buy/sell signals."
    )
    print(f"\n📝  Building agent for requirement:\n   {requirement}\n")

    agent, tools = svc.create_agent(
        session_id=session.session_id,
        requirement=requirement,
    )

    print(f"🤖  Created agent: {agent.name}")
    print(f"   Description : {agent.description}")
    print(f"   Category    : {agent.category}")
    print(f"   Tools ({len(tools)}):")
    for t in tools:
        print(f"     • {t.name}: {t.description}")

    # ---------------------------------------------------------------
    # 4. List all saved agents
    # ---------------------------------------------------------------
    agents = svc.list_agents(session_id=session.session_id)
    print(f"\n📦  Saved agents for {session.session_id[:8]}...: {len(agents)}")
    for a in agents:
        print(f"     • {a['name']} ({a['tool_count']} tools)")

    # ---------------------------------------------------------------
    # 5. Show stats
    # ---------------------------------------------------------------
    stats = svc.stats(session_id=session.session_id)
    print(f"\n📊  Stats: {stats}")

    # ---------------------------------------------------------------
    # 6. Logout
    # ---------------------------------------------------------------
    svc.logout(session.session_id)
    print("\n✅  Logged out. Done!")


if __name__ == "__main__":
    main()
