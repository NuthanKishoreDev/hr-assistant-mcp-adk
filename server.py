"""
Employee MCP Server
Exposes CRUD tools over MCP protocol (stdio transport).
"""

import json
import sys
from mcp.server.fastmcp import FastMCP

# ── In-memory employee store ────────────────────────────────────────────────
_NEXT_ID = 6

EMPLOYEES: dict[int, dict] = {
    1: {"id": 1, "name": "Alice Johnson",  "department": "Engineering",  "role": "Senior Engineer",      "salary": 120000, "email": "alice@acme.com",   "status": "active"},
    2: {"id": 2, "name": "Bob Martinez",   "department": "Marketing",    "role": "Marketing Manager",    "salary": 95000,  "email": "bob@acme.com",     "status": "active"},
    3: {"id": 3, "name": "Carol Williams", "department": "Engineering",  "role": "Staff Engineer",       "salary": 145000, "email": "carol@acme.com",   "status": "active"},
    4: {"id": 4, "name": "David Kim",      "department": "HR",           "role": "HR Specialist",        "salary": 75000,  "email": "david@acme.com",   "status": "active"},
    5: {"id": 5, "name": "Eva Chen",       "department": "Finance",      "role": "Finance Analyst",      "salary": 88000,  "email": "eva@acme.com",     "status": "inactive"},
}

# ── FastMCP app ──────────────────────────────────────────────────────────────
mcp = FastMCP("employee-crud-server")


@mcp.tool()
def list_employees(department: str = "", status: str = "") -> str:
    """
    List all employees, optionally filtered by department or status.

    Args:
        department: Filter by department name (optional, case-insensitive).
        status: Filter by status — 'active' or 'inactive' (optional).

    Returns:
        JSON array of matching employees.
    """
    results = list(EMPLOYEES.values())
    if department:
        results = [e for e in results if e["department"].lower() == department.lower()]
    if status:
        results = [e for e in results if e["status"].lower() == status.lower()]
    return json.dumps(results, indent=2)


@mcp.tool()
def get_employee(employee_id: int) -> str:
    """
    Get a single employee by ID.

    Args:
        employee_id: The numeric employee ID.

    Returns:
        JSON object of the employee, or an error message.
    """
    emp = EMPLOYEES.get(employee_id)
    if not emp:
        return json.dumps({"error": f"Employee {employee_id} not found."})
    return json.dumps(emp, indent=2)


@mcp.tool()
def create_employee(
    name: str,
    department: str,
    role: str,
    salary: int,
    email: str,
    status: str = "active",
) -> str:
    """
    Create a new employee record.

    Args:
        name: Full name of the employee.
        department: Department name (e.g. Engineering, Marketing, HR, Finance).
        role: Job title / role.
        salary: Annual salary in USD (integer).
        email: Work email address.
        status: Employment status — 'active' or 'inactive'. Defaults to 'active'.

    Returns:
        JSON object of the newly created employee including their assigned ID.
    """
    global _NEXT_ID
    emp = {
        "id": _NEXT_ID,
        "name": name,
        "department": department,
        "role": role,
        "salary": salary,
        "email": email,
        "status": status,
    }
    EMPLOYEES[_NEXT_ID] = emp
    _NEXT_ID += 1
    return json.dumps({"created": True, "employee": emp}, indent=2)


@mcp.tool()
def update_employee(
    employee_id: int,
    name: str = "",
    department: str = "",
    role: str = "",
    salary: int = 0,
    email: str = "",
    status: str = "",
) -> str:
    """
    Update one or more fields of an existing employee.  Only pass fields you want to change.

    Args:
        employee_id: ID of the employee to update.
        name: New full name (optional).
        department: New department (optional).
        role: New role/title (optional).
        salary: New annual salary (optional, pass 0 to skip).
        email: New email address (optional).
        status: New status — 'active' or 'inactive' (optional).

    Returns:
        JSON object with the updated employee record.
    """
    emp = EMPLOYEES.get(employee_id)
    if not emp:
        return json.dumps({"error": f"Employee {employee_id} not found."})

    if name:        emp["name"]       = name
    if department:  emp["department"] = department
    if role:        emp["role"]       = role
    if salary > 0:  emp["salary"]     = salary
    if email:       emp["email"]      = email
    if status:      emp["status"]     = status

    return json.dumps({"updated": True, "employee": emp}, indent=2)


@mcp.tool()
def delete_employee(employee_id: int) -> str:
    """
    Permanently delete an employee record.

    Args:
        employee_id: ID of the employee to delete.

    Returns:
        JSON confirmation or an error message.
    """
    if employee_id not in EMPLOYEES:
        return json.dumps({"error": f"Employee {employee_id} not found."})
    removed = EMPLOYEES.pop(employee_id)
    return json.dumps({"deleted": True, "employee": removed}, indent=2)


@mcp.tool()
def get_department_stats() -> str:
    """
    Return headcount and average salary per department.

    Returns:
        JSON object keyed by department name.
    """
    stats: dict[str, dict] = {}
    for emp in EMPLOYEES.values():
        dept = emp["department"]
        if dept not in stats:
            stats[dept] = {"headcount": 0, "total_salary": 0, "active": 0}
        stats[dept]["headcount"]    += 1
        stats[dept]["total_salary"] += emp["salary"]
        if emp["status"] == "active":
            stats[dept]["active"] += 1

    result = {}
    for dept, s in stats.items():
        result[dept] = {
            "headcount":      s["headcount"],
            "active":         s["active"],
            "avg_salary":     round(s["total_salary"] / s["headcount"]),
        }
    return json.dumps(result, indent=2)


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="stdio")
