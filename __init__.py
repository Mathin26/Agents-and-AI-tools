"""
AgentForge — A Python library for creating and managing Claude-powered AI agents and tools.
"""

from .agent import Agent
from .tool import Tool
from .registry import AgentRegistry
from .builder import AgentBuilder
from .auth import UserAuth, User
from .service import AgentService

__version__ = "1.0.0"
__all__ = [
    "Agent",
    "Tool",
    "AgentRegistry",
    "AgentBuilder",
    "UserAuth",
    "User",
    "AgentService",
]
