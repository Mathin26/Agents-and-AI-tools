"""
AgentService — High-level facade that combines UserAuth, AgentBuilder,
and AgentRegistry into one easy-to-use service object.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

from .agent import Agent, AgentResult
from .auth import UserAuth, User, Session
from .builder import AgentBuilder
from .registry import AgentRegistry
from .tool import Tool


class AgentService:
    """
    All-in-one service for agent creation and execution.

    Usage:
        svc = AgentService(api_key="sk-ant-...", data_dir="./data")

        # Register / login
        user  = svc.register("alice", "alice@example.com", "password")
        session = svc.login("alice", "password")

        # Build an agent from a natural-language requirement
        agent, tools = svc.create_agent(
            session_id=session.session_id,
            requirement="I need an agent that monitors RSS feeds and summarises news",
        )

        # Run the agent
        result = svc.run_agent(session_id=session.session_id,
                               agent_name=agent.name,
                               message="Summarise today's AI news")
        print(result.output)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        data_dir: str = "./service_data",
    ):
        self._auth = UserAuth(data_dir=f"{data_dir}/auth")
        self._registry = AgentRegistry(data_dir=f"{data_dir}/agents")
        self._builder = AgentBuilder(api_key=api_key)
        self._api_key = api_key

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------

    def register(self, username: str, email: str, password: str) -> User:
        return self._auth.register(username, email, password)

    def login(self, username: str, password: str) -> Session:
        return self._auth.login(username, password)

    def logout(self, session_id: str) -> None:
        self._auth.logout(session_id)

    def _require_user(self, session_id: str) -> User:
        user = self._auth.get_session_user(session_id)
        if not user:
            raise PermissionError("Invalid or expired session.")
        return user

    # ------------------------------------------------------------------
    # Agent management
    # ------------------------------------------------------------------

    def create_agent(
        self,
        session_id: str,
        requirement: str,
    ) -> Tuple[Agent, List[Tool]]:
        """Use Claude to auto-generate an agent from a requirement string."""
        user = self._require_user(session_id)
        agent, tools = self._builder.build(requirement, owner_id=user.user_id)
        self._registry.save_agent(agent, user_id=user.user_id)
        return agent, tools

    def list_agents(self, session_id: str) -> List[Dict]:
        user = self._require_user(session_id)
        return self._registry.list_agents(user_id=user.user_id)

    def get_agent(self, session_id: str, agent_name: str) -> Optional[Agent]:
        user = self._require_user(session_id)
        return self._registry.get_agent(agent_name, user_id=user.user_id)

    def delete_agent(self, session_id: str, agent_name: str) -> bool:
        user = self._require_user(session_id)
        return self._registry.delete_agent(agent_name, user_id=user.user_id)

    def refine_agent(
        self,
        session_id: str,
        agent_name: str,
        feedback: str,
    ) -> Tuple[Agent, List[Tool]]:
        """Refine an existing agent based on feedback, saving as a new version."""
        user = self._require_user(session_id)
        existing = self._registry.get_agent(agent_name, user_id=user.user_id)
        if not existing:
            raise ValueError(f"Agent '{agent_name}' not found.")
        new_agent, tools = self._builder.refine(existing, feedback, owner_id=user.user_id)
        self._registry.save_agent(new_agent, user_id=user.user_id)
        return new_agent, tools

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run_agent(
        self,
        session_id: str,
        agent_name: str,
        message: str,
        api_key: Optional[str] = None,
    ) -> AgentResult:
        """Run a saved agent with a message."""
        user = self._require_user(session_id)
        agent = self._registry.get_agent(agent_name, user_id=user.user_id)
        if not agent:
            raise ValueError(f"Agent '{agent_name}' not found.")
        key = api_key or self._api_key
        if key:
            import anthropic
            agent._client = anthropic.Anthropic(api_key=key)
        return agent.run(message)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self, session_id: str) -> Dict[str, Any]:
        user = self._require_user(session_id)
        return self._registry.stats(user_id=user.user_id)
