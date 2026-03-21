"""
Tool — Defines a callable tool that agents can use.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ToolParameter:
    """Describes a single parameter for a tool."""
    name: str
    type: str  # "string", "number", "boolean", "array", "object"
    description: str
    required: bool = True
    enum: Optional[List[Any]] = None
    default: Optional[Any] = None

    def to_json_schema(self) -> Dict[str, Any]:
        schema: Dict[str, Any] = {
            "type": self.type,
            "description": self.description,
        }
        if self.enum:
            schema["enum"] = self.enum
        if self.default is not None:
            schema["default"] = self.default
        return schema


class Tool:
    """
    Represents an AI-callable tool that wraps a Python function.

    Usage:
        def search_web(query: str) -> str:
            return f"Results for {query}"

        tool = Tool(
            name="search_web",
            description="Search the web for information",
            parameters=[ToolParameter("query", "string", "The search query")],
            handler=search_web,
        )
    """

    def __init__(
        self,
        name: str,
        description: str,
        parameters: Optional[List[ToolParameter]] = None,
        handler: Optional[Callable[..., Any]] = None,
        category: str = "general",
        tags: Optional[List[str]] = None,
    ):
        self.name = name
        self.description = description
        self.parameters: List[ToolParameter] = parameters or []
        self.handler = handler
        self.category = category
        self.tags: List[str] = tags or []
        self._call_count = 0

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def __call__(self, **kwargs: Any) -> Any:
        """Execute the tool with the given keyword arguments."""
        if self.handler is None:
            raise RuntimeError(f"Tool '{self.name}' has no handler registered.")
        self._call_count += 1
        return self.handler(**kwargs)

    def execute(self, arguments: Dict[str, Any]) -> Any:
        """Execute the tool given a dict of arguments (as returned by Claude)."""
        return self(**arguments)

    # ------------------------------------------------------------------
    # Claude API schema
    # ------------------------------------------------------------------

    def to_claude_schema(self) -> Dict[str, Any]:
        """Return the tool definition dict accepted by the Claude /v1/messages API."""
        required = [p.name for p in self.parameters if p.required]
        properties = {p.name: p.to_json_schema() for p in self.parameters}
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "tags": self.tags,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "required": p.required,
                }
                for p in self.parameters
            ],
            "call_count": self._call_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Tool":
        params = [
            ToolParameter(
                name=p["name"],
                type=p["type"],
                description=p["description"],
                required=p.get("required", True),
            )
            for p in data.get("parameters", [])
        ]
        return cls(
            name=data["name"],
            description=data["description"],
            parameters=params,
            category=data.get("category", "general"),
            tags=data.get("tags", []),
        )

    def __repr__(self) -> str:
        return f"Tool(name={self.name!r}, category={self.category!r}, params={len(self.parameters)})"
