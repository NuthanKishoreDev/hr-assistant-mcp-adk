import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioConnectionParams
import logging
from logging.handlers import RotatingFileHandler
from mcp import StdioServerParameters

load_dotenv(Path(__file__).parent / ".env")

# ── Logging Configuration ───────────────────────────────────────────────────
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "agent.log"

logging.basicConfig(
    level=logging.INFO, # Keep root at INFO to avoid noise from other libraries
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5),
        logging.StreamHandler(sys.stdout)
    ],
    force=True
)
# Enable detailed ADK logs for LLM requests/responses
logging.getLogger("google_adk").setLevel(logging.DEBUG)

logger = logging.getLogger("MCPAgent")

logger.info("HR Assistant Agent initializing...")

SERVER_SCRIPT = str(Path(__file__).parent.parent / "mcp-server" / "server.py")

toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=[SERVER_SCRIPT],
        )
    )
)

root_agent = Agent(
    model='gemini-2.5-flash',
    name='root_agent',
    description='You are an intelligent HR assistant with full access to Acme Corp\'s employee database.',
    instruction="""
    You are an intelligent HR assistant with full access to Acme Corp's employee database.
You can create, read, update, and delete employee records via the tools available to you.

Guidelines:
- When listing employees, present results in a clean, readable table.
- Use get_department_stats for summary/overview questions.
- When asked vague questions like "show me the team", list all employees.
    """,
    tools=[toolset],
)
