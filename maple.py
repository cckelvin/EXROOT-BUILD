import os
import json
import subprocess
import requests
from pathlib import Path


# ============================================================
# EXROOT MAPLE
# Groq + GPT-OSS-120B + Airtable + Windows OS
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE = os.getenv("AIRTABLE_TABLE", "Commands")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"


# ------------------------------------------------------------
# Airtable
# ------------------------------------------------------------

def get_airtable_knowledge(command):
    if not AIRTABLE_TOKEN or not AIRTABLE_BASE_ID:
        return "No Airtable configuration was provided."

    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE}"

    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}"
    }

    params = {
        "maxRecords": 100
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        knowledge = []

        for record in data.get("records", []):
            fields = record.get("fields", {})

            knowledge.append({
                "command": fields.get("Command", ""),
                "description": fields.get("Description", ""),
                "instructions": fields.get("Instructions", ""),
                "examples": fields.get("Examples", ""),
                "os": fields.get("OS", "Windows")
            })

        return json.dumps(knowledge, indent=2)

    except Exception as e:
        return f"Airtable error: {e}"


# ------------------------------------------------------------
# Groq / GPT-OSS-120B
# ------------------------------------------------------------

def ask_maple(user_command, airtable_knowledge):

    if not GROQ_API_KEY:
        return {
            "type": "error",
            "message": "GROQ_API_KEY is not configured."
        }

    system_prompt = """
You are Maple, the intelligence engine of EXROOT.

EXROOT is a Windows-native AI terminal.

The user gives you commands such as:

cve mkdir proj
cve ls
cve cd proj
cve touch test.txt

Airtable contains the knowledge and instructions that guide you.

You have direct access to the Windows operating system through Python.

IMPORTANT:

You are not merely explaining commands.

You must determine what the user wants and perform the operation.

Return ONLY valid JSON.

For an operation that should execute on Windows, return:

{
    "action": "execute",
    "type": "filesystem",
    "operation": "mkdir",
    "path": "proj"
}

For listing a directory:

{
    "action": "execute",
    "type": "filesystem",
    "operation": "ls",
    "path": "."
}

For changing directory:

{
    "action": "execute",
    "type": "filesystem",
    "operation": "cd",
    "path": "proj"
}

For creating a file:

{
    "action": "execute",
    "type": "filesystem",
    "operation": "touch",
    "path": "test.txt"
}

For running a Windows program or command when necessary:

{
    "action": "execute",
    "type": "process",
    "command": "..."
}

For normal conversation:

{
    "action": "respond",
    "message": "..."
}

Do not return Markdown.
Do not wrap JSON in ```.

The user's command has priority, but Airtable provides the command knowledge and rules.
"""

    user_prompt = f"""
AIRTABLE KNOWLEDGE:

{airtable_knowledge}

USER COMMAND:

{user_command}
"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        "temperature": 0,
        "max_tokens": 1000
    }

    try:
        response = requests.post(
            GROQ_URL,
            headers=headers,
            json=payload,
            timeout=120
        )

        response.raise_for_status()

        data = response.json()

        content = data["choices"][0]["message"]["content"]

        return json.loads(content)

    except json.JSONDecodeError:
        return {
            "type": "error",
            "message": "Maple returned invalid JSON.",
            "raw": content if "content" in locals() else ""
        }

    except Exception as e:
        return {
            "type": "error",
            "message": str(e)
        }


# ------------------------------------------------------------
# WINDOWS OS
# ------------------------------------------------------------

def execute_filesystem(operation, path="."):

    path = os.path.expandvars(os.path.expanduser(path))

    try:

        if operation == "mkdir":

            Path(path).mkdir(
                parents=True,
                exist_ok=True
            )

            return f"Directory created: {path}"

        elif operation == "ls":

            target = Path(path)

            if not target.exists():
                return f"Path does not exist: {path}"

            items = []

            for item in target.iterdir():

                if item.is_dir():
                    items.append(f"<DIR>  {item.name}")
                else:
                    items.append(f"        {item.name}")

            return "\n".join(items) if items else "(empty)"

        elif operation == "cd":

            target = Path(path).resolve()

            if not target.exists():
                return f"Directory does not exist: {target}"

            if not target.is_dir():
                return f"Not a directory: {target}"

            os.chdir(target)

            return f"Changed directory to: {target}"

        elif operation == "touch":

            file_path = Path(path)

            file_path.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            file_path.touch(
                exist_ok=True
            )

            return f"File created: {file_path}"

        elif operation == "rm":

            target = Path(path)

            if target.is_dir():
                import shutil
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
            else:
                return f"Path does not exist: {path}"

            return f"Removed: {path}"

        else:

            return f"Unknown filesystem operation: {operation}"

    except Exception as e:

        return f"Windows filesystem error: {e}"


# ------------------------------------------------------------
# WINDOWS PROCESS
# ------------------------------------------------------------

def execute_process(command):

    try:

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )

        output = result.stdout

        if result.stderr:
            output += result.stderr

        return output.strip()

    except Exception as e:

        return f"Process error: {e}"


# ------------------------------------------------------------
# MAPLE EXECUTION ENGINE
# ------------------------------------------------------------

def process_command(user_command):

    airtable = get_airtable_knowledge(user_command)

    decision = ask_maple(
        user_command,
        airtable
    )

    if decision.get("action") == "respond":

        return decision.get(
            "message",
            ""
        )

    if decision.get("action") == "execute":

        execution_type = decision.get("type")

        if execution_type == "filesystem":

            operation = decision.get(
                "operation"
            )

            path = decision.get(
                "path",
                "."
            )

            return execute_filesystem(
                operation,
                path
            )

        if execution_type == "process":

            command = decision.get(
                "command",
                ""
            )

            return execute_process(
                command
            )

    if decision.get("action") == "error":

        return decision.get(
            "message",
            "Unknown Maple error."
        )

    return f"Maple returned an unknown action:\n{decision}"
