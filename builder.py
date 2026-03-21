"""
AgentBuilder — Uses Claude to auto-generate Agent + Tool definitions from
a natural-language requirement description.
"""

from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Optional
import anthropic

from .agent import Agent
from .tool import Tool, ToolParameter


_BUILDER_SYSTEM = """\
You are AgentForge, an AI system that designs specialised AI agents.

Given a user's requirement, you output a JSON specification for ONE agent
that has between 1 and 5 tools (no more than 5 tools total).

Respond ONLY with valid JSON matching this exact structure — no markdown,
no commentary, just raw JSON:

{
  "agent": {
    "name": "CamelCaseName",
    "description": "One sentence describing the agent.",
    "category": "one of: productivity | research | data | communication | code | creative | finance | general",
    "tags": ["tag1", "tag2"],
    "system_prompt": "A detailed system prompt for the agent (2-5 sentences).",
    "model": "claude-sonnet-4-20250514",
    "max_iterations": 8,
    "max_tokens": 4096
  },
  "tools": [
    {
      "name": "snake_case_tool_name",
      "description": "What this tool does.",
      "category": "tool category",
      "tags": [],
      "parameters": [
        {
          "name": "param_name",
          "type": "string",
          "description": "What this param is.",
          "required": true
        }
      ]
    }
  ]
}

Rules:
- tools array must have 1–5 items, never more than 5.
- All names must be unique.
- system_prompt must clearly describe the agent's purpose and persona.
- Parameters must have type from: string | number | boolean | array | object.
- Make the agent genuinely useful for the stated requirement.
"""


class AgentBuilder:
    """
    Generates Agent + Tool configurations from natural-language requirements
    by calling the Claude API.

    Usage:
        builder = AgentBuilder(api_key="sk-ant-...")
        agent, tools = builder.build("I need an agent that researches companies")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
    ):
        api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(
        self,
        requirement: str,
        owner_id: Optional[str] = None,
        extra_context: Optional[str] = None,
    ) -> tuple[Agent, List[Tool]]:
        """
        Generate an Agent and its Tools from a natural-language requirement.

        Returns:
            (agent, tools) — Agent instance (tools already attached) + raw Tool list
        """
        prompt = requirement
        if extra_context:
            prompt = f"{extra_context}\n\nRequirement: {requirement}"

        spec = self._generate_spec(prompt)
        return self._build_from_spec(spec, owner_id=owner_id)

    def build_from_spec(self, spec: Dict[str, Any], owner_id: Optional[str] = None) -> tuple[Agent, List[Tool]]:
        """Build from a pre-existing spec dict (e.g. loaded from storage)."""
        return self._build_from_spec(spec, owner_id=owner_id)

    def refine(
        self,
        existing_agent: Agent,
        feedback: str,
        owner_id: Optional[str] = None,
    ) -> tuple[Agent, List[Tool]]:
        """
        Refine an existing agent definition based on feedback.
        """
        context = (
            f"Existing agent specification:\n{json.dumps(existing_agent.to_dict(), indent=2)}\n\n"
            f"User feedback / change request: {feedback}"
        )
        return self.build(feedback, owner_id=owner_id, extra_context=context)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _generate_spec(self, prompt: str) -> Dict[str, Any]:
        response = self._client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=_BUILDER_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1])
        return json.loads(raw)

    def _build_from_spec(
        self, spec: Dict[str, Any], owner_id: Optional[str] = None
    ) -> tuple[Agent, List[Tool]]:
        tool_list: List[Tool] = []
        for t in spec.get("tools", [])[:5]:  # enforce max 5
            params = [
                ToolParameter(
                    name=p["name"],
                    type=p.get("type", "string"),
                    description=p.get("description", ""),
                    required=p.get("required", True),
                )
                for p in t.get("parameters", [])
            ]
            tool_list.append(
                Tool(
                    name=t["name"],
                    description=t["description"],
                    parameters=params,
                    category=t.get("category", "general"),
                    tags=t.get("tags", []),
                )
            )

        agent_spec = spec["agent"]
        agent = Agent(
            name=agent_spec["name"],
            description=agent_spec["description"],
            system_prompt=agent_spec["system_prompt"],
            tools=tool_list,
            model=agent_spec.get("model", Agent.DEFAULT_MODEL),
            max_iterations=agent_spec.get("max_iterations", Agent.MAX_ITERATIONS),
            max_tokens=agent_spec.get("max_tokens", 4096),
            owner_id=owner_id,
            category=agent_spec.get("category", "general"),
            tags=agent_spec.get("tags", []),
        )
        return agent, tool_list
