"""Model, paths and limits for the agent team. One model for every agent."""

import os
import sys
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

BACKEND_DIR = Path(__file__).resolve().parent
HW5_DIR = BACKEND_DIR.parent
PROMPTS_DIR = BACKEND_DIR / "prompts"
AUDIT_PATH = Path(os.getenv("CAMPUS_AUDIT_PATH") or HW5_DIR / "output" / "audit_trail.json")

# MCP server: same script as .mcp.json, so agents and Claude Code share one tool layer.
# Python to start it with: $MCP_PYTHON if set, else a dedicated mcp_server/.venv if one
# exists, else the same Python running the backend (requirements.txt installs fastmcp).
_MCP_VENV = HW5_DIR / "mcp_server" / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
MCP_PYTHON = Path(os.getenv("MCP_PYTHON") or (_MCP_VENV if _MCP_VENV.exists() else sys.executable))
MCP_SCRIPT = HW5_DIR / "mcp_server" / "server.py"

# API key: repository-root .env (AI Yale SOM/.env), with an optional HW5/.env override.
load_dotenv(HW5_DIR.parent / ".env")
load_dotenv(HW5_DIR / ".env", override=True)

MODEL_NAME = "gpt-5.6-luna"  # the only model any agent uses

# ---------- token and loop limits ----------
# The usage object is shared across delegations, so these caps cover the WHOLE team
# for one ticket run, not each agent separately.
TEAM_LIMITS = UsageLimits(
    request_limit=30,          # model calls across all agents
    tool_calls_limit=60,       # MCP + delegation calls across all agents
    total_tokens_limit=250_000,
)
MAX_DELEGATION_DEPTH = 3       # boss -> accounting -> facilities is the deepest chain allowed
MAX_DELEGATIONS_PER_RUN = 8    # total hand-offs in one run
MODEL_SETTINGS = {"max_tokens": 4000, "timeout": 60}  # per model call
AGENT_RETRIES = 2              # bad tool args / bad output retries per agent
AUDIT_TEXT_LIMIT = 2000        # characters kept per text or tool result in the audit trail


def build_model() -> OpenAIChatModel:
    key = os.getenv("PORTKEY_API_KEY")
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is missing from the repository-root .env")
    client = AsyncOpenAI(
        api_key=key,
        base_url=os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1"),
        default_headers={"x-portkey-provider": os.getenv("PORTKEY_PROVIDER", "openai")},
    )
    return OpenAIChatModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))
