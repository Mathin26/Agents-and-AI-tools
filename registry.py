"""
AgentRegistry — Persistent (JSON-backed) store for agents and tools,
scoped per user.
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from .agent import Agent
from .tool import Tool


class AgentRegistry:
    """
    Stores and retrieves Agent and Tool definitions for each user.

    Persistence is a simple JSON file (one per user) in a configurable
    data directory. Swap for a database adapter in production.

    Usage:
        registry = AgentRegistry(data_dir="./data")
        registry.save_agent(agent, user_id="user_123")
        agents = registry.list_agents(user_id="user_123")
        agent  = registry.get_agent("MyAgent", user_id="user_123")
    """

    def __init__(self, data_dir: str = "./agent_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _user_path(self, user_id: str) -> Path:
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)
        return self.data_dir / f"{safe_id}.json"

    def _load_user_data(self, user_id: str) -> Dict:
        path = self._user_path(user_id)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"agents": {}, "tools": {}}

    def _save_user_data(self, user_id: str, data: Dict) -> None:
        path = self._user_path(user_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Agent CRUD
    # ------------------------------------------------------------------

    def save_agent(self, agent: Agent, user_id: str) -> None:
        """Persist an agent definition for the given user."""
        data = self._load_user_data(user_id)
        data["agents"][agent.name] = agent.to_dict()
        self._save_user_data(user_id, data)

    def get_agent(self, agent_name: str, user_id: str) -> Optional[Agent]:
        """Load an agent by name for the given user, or None if not found."""
        data = self._load_user_data(user_id)
        agent_dict = data["agents"].get(agent_name)
        if not agent_dict:
            return None
        tools = [Tool.from_dict(t) for t in agent_dict.get("tools", [])]
        return Agent(
            name=agent_dict["name"],
            description=agent_dict["description"],
            system_prompt=agent_dict["system_prompt"],
            tools=tools,
            model=agent_dict.get("model", Agent.DEFAULT_MODEL),
            max_iterations=agent_dict.get("max_iterations", Agent.MAX_ITERATIONS),
            max_tokens=agent_dict.get("max_tokens", 4096),
            owner_id=agent_dict.get("owner_id"),
            category=agent_dict.get("category", "general"),
            tags=agent_dict.get("tags", []),
        )

    def delete_agent(self, agent_name: str, user_id: str) -> bool:
        data = self._load_user_data(user_id)
        if agent_name in data["agents"]:
            del data["agents"][agent_name]
            self._save_user_data(user_id, data)
            return True
        return False

    def list_agents(self, user_id: str) -> List[Dict]:
        """Return lightweight summaries of all agents for the given user."""
        data = self._load_user_data(user_id)
        return [
            {
                "name": a["name"],
                "description": a["description"],
                "category": a.get("category", "general"),
                "tags": a.get("tags", []),
                "tool_count": len(a.get("tools", [])),
            }
            for a in data["agents"].values()
        ]

    # ------------------------------------------------------------------
    # Tool CRUD
    # ------------------------------------------------------------------

    def save_tool(self, tool: Tool, user_id: str) -> None:
        data = self._load_user_data(user_id)
        data["tools"][tool.name] = tool.to_dict()
        self._save_user_data(user_id, data)

    def get_tool(self, tool_name: str, user_id: str) -> Optional[Tool]:
        data = self._load_user_data(user_id)
        tool_dict = data["tools"].get(tool_name)
        return Tool.from_dict(tool_dict) if tool_dict else None

    def list_tools(self, user_id: str) -> List[Dict]:
        data = self._load_user_data(user_id)
        return list(data["tools"].values())

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self, user_id: str) -> Dict:
        data = self._load_user_data(user_id)
        return {
            "user_id": user_id,
            "agent_count": len(data["agents"]),
            "tool_count": len(data["tools"]),
        }
