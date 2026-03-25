"""
Pure MCP Client (no ADK)
========================
Demonstrates connecting directly to the Employee MCP server
and calling each CRUD tool manually.
"""

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_SCRIPT = str(Path(__file__).parent / "mcp-server" / "server.py")


def pretty(data) -> str:
    """Pretty-print JSON or plain text."""
    try:
        parsed = json.loads(data) if isinstance(data, str) else data
        return json.dumps(parsed, indent=2)
    except Exception:
        return str(data)


async def call(session: ClientSession, tool: str, **kwargs) -> str:
    """Call a tool and return the text result."""
    result = await session.call_tool(tool, arguments=kwargs)
    if result.content:
        return result.content[0].text
    return ""


async def main():
    params = StdioServerParameters(command=sys.executable, args=[SERVER_SCRIPT])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # ── Discover tools ──────────────────────────────────────────────
            tools_list = await session.list_tools()
            print("═" * 60)
            print("  MCP Employee Server — Available Tools")
            print("═" * 60)
            for t in tools_list.tools:
                print(f"  • {t.name}: {t.description.splitlines()[0]}")
            print()

            # ── READ: List all employees ────────────────────────────────────
            print("─" * 60)
            print("1. LIST ALL EMPLOYEES")
            print("─" * 60)
            resp = await call(session, "list_employees")
            employees = json.loads(resp)
            print(f"  {'ID':<4} {'Name':<20} {'Dept':<15} {'Role':<25} {'Salary':>9} {'Status'}")
            print(f"  {'─'*4} {'─'*20} {'─'*15} {'─'*25} {'─'*9} {'─'*8}")
            for e in employees:
                print(f"  {e['id']:<4} {e['name']:<20} {e['department']:<15} {e['role']:<25} ${e['salary']:>8,} {e['status']}")

            # ── READ: Get single employee ───────────────────────────────────
            print("\n─" * 60)
            print("2. GET EMPLOYEE ID=1")
            print("─" * 60)
            resp = await call(session, "get_employee", employee_id=1)
            print(pretty(resp))

            # ── CREATE ──────────────────────────────────────────────────────
            print("\n─" * 60)
            print("3. CREATE NEW EMPLOYEE")
            print("─" * 60)
            resp = await call(
                session,
                "create_employee",
                name="Frank Nguyen",
                department="Data Science",
                role="Data Scientist",
                salary=110000,
                email="frank@acme.com",
                status="active",
            )
            result = json.loads(resp)
            new_id = result["employee"]["id"]
            print(pretty(resp))

            # ── READ: Verify creation ───────────────────────────────────────
            print("\n─" * 60)
            print(f"4. VERIFY — GET EMPLOYEE ID={new_id}")
            print("─" * 60)
            resp = await call(session, "get_employee", employee_id=new_id)
            print(pretty(resp))

            # ── UPDATE ──────────────────────────────────────────────────────
            print("\n─" * 60)
            print("5. UPDATE EMPLOYEE ID=3 (promote + raise)")
            print("─" * 60)
            resp = await call(
                session,
                "update_employee",
                employee_id=3,
                role="Principal Engineer",
                salary=155000,
            )
            print(pretty(resp))

            # ── FILTER: Engineering dept ────────────────────────────────────
            print("\n─" * 60)
            print("6. LIST ENGINEERING DEPARTMENT")
            print("─" * 60)
            resp = await call(session, "list_employees", department="Engineering")
            eng = json.loads(resp)
            for e in eng:
                print(f"  [{e['id']}] {e['name']} — {e['role']} (${e['salary']:,})")

            # ── DELETE ──────────────────────────────────────────────────────
            print("\n─" * 60)
            print("7. DELETE EMPLOYEE ID=5")
            print("─" * 60)
            resp = await call(session, "delete_employee", employee_id=5)
            print(pretty(resp))

            # ── STATS ───────────────────────────────────────────────────────
            print("\n─" * 60)
            print("8. DEPARTMENT STATISTICS")
            print("─" * 60)
            resp = await call(session, "get_department_stats")
            stats = json.loads(resp)
            print(f"  {'Department':<20} {'Headcount':>10} {'Active':>8} {'Avg Salary':>12}")
            print(f"  {'─'*20} {'─'*10} {'─'*8} {'─'*12}")
            for dept, s in stats.items():
                print(f"  {dept:<20} {s['headcount']:>10} {s['active']:>8} ${s['avg_salary']:>10,}")

            print("\n  ✅  All CRUD operations completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
