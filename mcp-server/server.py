"""
Employee MCP Server
Exposes CRUD tools over MCP protocol (stdio transport).
"""

import json
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from mcp.server.fastmcp import FastMCP

# ── Logging Configuration ───────────────────────────────────────────────────
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
log_file = os.path.join(log_dir, "server.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    ],
    force=True  # Ensure logging is reconfigured
)
logger = logging.getLogger("EmployeeServer")
logger.info("Employee MCP Server initializing...")

# ── Data File Path ──────────────────────────────────────────────────────────
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "employees.json")

def load_employees() -> dict[int, dict]:
    """Load employees from JSON file."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                data = json.load(f)
                return {e["id"]: e for e in data}
            except json.JSONDecodeError:
                return {}
    return {}

def save_employees():
    """Save employees to JSON file."""
    with open(DATA_FILE, "w") as f:
        json.dump(list(EMPLOYEES.values()), f, indent=2)


# Initial load
EMPLOYEES: dict[int, dict] = load_employees()
_NEXT_ID = max(EMPLOYEES.keys() or [0]) + 1

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
    logger.info(f"Request: list_employees(department='{department}', status='{status}')")
    results = list(EMPLOYEES.values())
    if department:
        results = [e for e in results if e["department"].lower() == department.lower()]
    if status:
        results = [e for e in results if e["status"].lower() == status.lower()]
    
    response = json.dumps(results, indent=2)
    logger.info(f"Response: {len(results)} employees returned")
    return response


@mcp.tool()
def get_employee(employee_id: int) -> str:
    """
    Get a single employee by ID.

    Args:
        employee_id: The numeric employee ID.

    Returns:
        JSON object of the employee, or an error message.
    """
    logger.info(f"Request: get_employee(id={employee_id})")
    emp = EMPLOYEES.get(employee_id)
    if not emp:
        res = json.dumps({"error": f"Employee {employee_id} not found."})
        logger.warning(f"Response: Employee {employee_id} not found")
        return res
    
    response = json.dumps(emp, indent=2)
    logger.info(f"Response: Success for employee {employee_id}")
    return response


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
    logger.info(f"Request: create_employee(name='{name}', dept='{department}', role='{role}')")
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
    save_employees()
    
    response = json.dumps({"created": True, "employee": emp}, indent=2)
    logger.info(f"Response: Created employee with ID={emp['id']}")
    return response


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
    logger.info(f"Request: update_employee(id={employee_id}, updates={{'name': '{name}', 'status': '{status}'}})")
    emp = EMPLOYEES.get(employee_id)
    if not emp:
        res = json.dumps({"error": f"Employee {employee_id} not found."})
        logger.warning(f"Response: Failed update for ID={employee_id} (not found)")
        return res

    if name:        emp["name"]       = name
    if department:  emp["department"] = department
    if role:        emp["role"]       = role
    if salary > 0:  emp["salary"]     = salary
    if email:       emp["email"]      = email
    if status:      emp["status"]     = status

    save_employees()
    response = json.dumps({"updated": True, "employee": emp}, indent=2)
    logger.info(f"Response: Updated employee ID={employee_id}")
    return response


@mcp.tool()
def delete_employee(employee_id: int) -> str:
    """
    Permanently delete an employee record.

    Args:
        employee_id: ID of the employee to delete.

    Returns:
        JSON confirmation or an error message.
    """
    logger.info(f"Request: delete_employee(id={employee_id})")
    if employee_id not in EMPLOYEES:
        res = json.dumps({"error": f"Employee {employee_id} not found."})
        logger.warning(f"Response: Failed delete for ID={employee_id} (not found)")
        return res
    removed = EMPLOYEES.pop(employee_id)
    save_employees()
    
    response = json.dumps({"deleted": True, "employee": removed}, indent=2)
    logger.info(f"Response: Deleted employee ID={employee_id}")
    return response


@mcp.tool()
def get_department_stats() -> str:
    """
    Return headcount and average salary per department.

    Returns:
        JSON object keyed by department name.
    """
    logger.info("Request: get_department_stats()")
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
            "avg_salary":     round(s["total_salary"] / s["headcount"]) if s["headcount"] > 0 else 0,
        }
    
    response = json.dumps(result, indent=2)
    logger.info(f"Response: Returned stats for {len(result)} departments")
    return response


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="stdio")
