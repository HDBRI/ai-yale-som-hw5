"""The five Campus Customs agents. Each role lives in its own module."""

from importlib import import_module

from pydantic_ai import Agent

from ..models import AgentReport, Role, TeamDeps


def get_agent(role: Role) -> Agent[TeamDeps, AgentReport]:
    return import_module(f"{__name__}.{role}").agent
