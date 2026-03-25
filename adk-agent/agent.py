"""ADK Employee Agent — ADK 1.x compatible.

This script connects a Gemini LLM agent to an MCP server via the McpToolset.
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
from google.adk.agents import LlmAgent

load_dotenv()

# ── Logging Configuration ───────────────────────────────────────────────────
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "agent.log"

logging.basicConfig(
    level=logging.INFO, # Reverted to INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5),
        logging.StreamHandler(sys.stdout)
    ],
    force=True  # Force reconfiguration
)
logger = logging.getLogger("ADKAgent")

logger.info("ADK Agent starting up...")

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioConnectionParams
from google.genai import types as genai_types
from mcp import StdioServerParameters

SERVER_SCRIPT = str(Path(__file__).parent.parent / "mcp-server" / "server.py")

SYSTEM_PROMPT = """
You are an intelligent HR assistant with full access to Acme Corp's employee database.
You can create, read, update, and delete employee records via the tools available to you.

Guidelines:
- When listing employees, present results in a clean, readable markdown table format only.
- Use get_department_stats for summary/overview questions.
- When asked vague questions like "show me the team", list all employees.
"""

APP_NAME = "employee-hr-agent"
USER_ID = "hr-user-001"
SESSION_ID = "session-001"



def build_toolset() -> McpToolset:
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=sys.executable,
                args=[SERVER_SCRIPT],
            )
        )
    )


def build_agent(toolset: McpToolset) -> LlmAgent:
    return LlmAgent(
        model="gemini-2.5-flash",
        name="employee_agent",
        instruction=SYSTEM_PROMPT,
        tools=[toolset],
    )


async def run_interactive():
    toolset = build_toolset()
    agent = build_agent(toolset)

    session_service = InMemorySessionService()
    await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)

    try:
        while True:
            user_input = input("\nYou: ").strip()
            if not user_input or user_input.lower() in {"quit", "exit"}:
                print("Goodbye!")
                break

            message = genai_types.Content(role="user", parts=[genai_types.Part(text=user_input)])
            logger.info(f"User Request: {user_input}")
            print("\nAgent: ", end="", flush=True)
            full_response = ""
            async for event in runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=message):
                if event.is_final_response() and event.content:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            print(part.text, end="")
                            full_response += part.text
            print()
            logger.info(f"Agent Response: {full_response.strip()}")
    finally:
        await toolset.close()


async def run_demo():
    queries = [
        "Show me all employees",
        "List only Engineering department employees",
        "Get details for employee ID 1",
        "Create a new employee: Frank Nguyen, Data Science, Data Scientist, salary 110000, frank@acme.com",
        "Update employee ID 3's salary to 155000 and role to Principal Engineer",
        "Delete employee ID 5",
        "Show department statistics",
        "List all active employees",
    ]

    toolset = build_toolset()
    agent = build_agent(toolset)

    session_service = InMemorySessionService()
    await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)

    try:
        for i, query in enumerate(queries, 1):
            logger.info(f"Demo Request: {query}")
            message = genai_types.Content(role="user", parts=[genai_types.Part(text=query)])
            full_response = ""
            async for event in runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=message):
                if event.is_final_response() and event.content:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            print(f"Agent: {part.text}")
                            full_response += part.text
            logger.info(f"Agent Response: {full_response.strip()}")
            
    finally:
        await toolset.close()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "interactive"

    if "GOOGLE_API_KEY" not in os.environ:
        print("ERROR: Set GOOGLE_API_KEY first.\n")
        print("  PowerShell:   $env:GOOGLE_API_KEY='your-key'")
        print("  CMD:          set GOOGLE_API_KEY=your-key")
        print("  macOS/Linux:  export GOOGLE_API_KEY=your-key\n")
        sys.exit(1)

    if mode == "interactive":
        asyncio.run(run_interactive())
    else:
        asyncio.run(run_demo())
