
import os
import json
import shlex
import subprocess
from pathlib import Path

import requests


# ============================================================
# EXROOT MAPLE
# Airtable Command Registry
# Groq / GPT-OSS-120B
# Direct Windows OS execution
# ============================================================


# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE = os.getenv("AIRTABLE_TABLE", "Commands")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

MODEL = "openai/gpt-oss-120b"


# ============================================================
# AIRTABLE
# ============================================================

def get_airtable_command(command_name):

    if not AIRTABLE_TOKEN:
        return {
            "error": "AIRTABLE_TOKEN is not configured."
        }

    if not AIRTABLE_BASE_ID:
        return {
            "error": "AIRTABLE_BASE_ID is not configured."
        }

    url = (
        f"https://api.airtable.com/v0/"
        f"{AIRTABLE_BASE_ID}/"
        f"{AIRTABLE_TABLE}"
    )

    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}"
    }

    params = {
        "maxRecords": 100,
        "filterByFormula": (
            f"LOWER({{command}})=LOWER('{command_name}')"
        )
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

        records = data.get("records", [])

        if not records:

            return {
                "error": f"Command not found in Airtable: {command_name}"
            }

        record = records[0]

        fields = record.get("fields", {})

        return {
            "command": fields.get("command", ""),
            "category": fields.get("category", ""),
            "description": fields.get("description", ""),
            "host_access": fields.get("host access", ""),
            "risk_level": fields.get("risk level", ""),
            "syntax": fields.get("syntax", ""),
            "instructions": fields.get("instructions", ""),
            "api_function": fields.get("API Function", ""),
            "confirmation": fields.get("confirmation", "")
        }

    except Exception as e:

        return {
            "error": f"Airtable error: {e}"
        }


# ============================================================
# GROQ / MAPLE
# ============================================================

def ask_maple(user_command, command_name, arguments, knowledge):

    if not GROQ_API_KEY:

        return {
            "action": "error",
            "message": "GROQ_API_KEY is not configured."
        }

    system_prompt = """
You are Maple, the intelligence engine of EXROOT.

EXROOT is an AI-native Windows terminal.

You receive a CVE command from the user.

Airtable is the EXROOT command registry.
It tells you what the command means and which API function
should perform it.

You must decide what operation the user wants.

The Windows operation is performed directly by the EXROOT
runtime after you return the structured decision.

IMPORTANT RULES:

1. Return ONLY valid JSON.
2. Do not return Markdown.
3. Do not put JSON inside ``` blocks.
4. Use the Airtable API Function when one is provided.
5. Preserve the user's arguments.
6. Do not ask for confirmation.
7. Do not merely explain the command when an operation
   should be performed.
8. For normal conversation, return a response action.

For an executable operation return:

{
    "action": "execute",
    "api_function": "filesystem.mkdir",
    "arguments": {
        "path": "proj"
    }
}

For a normal response return:

{
    "action": "respond",
    "message": "..."
}

For an error return:

{
    "action": "error",
    "message": "..."
}
"""

    user_prompt = f"""
COMMAND REGISTRY ENTRY:

{json.dumps(knowledge, indent=2)}

COMMAND NAME:

{command_name}

COMMAND ARGUMENTS:

{json.dumps(arguments)}

FULL USER COMMAND:

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
            "action": "error",
            "message": "Maple returned invalid JSON.",
            "raw": content if "content" in locals() else ""
        }

    except Exception as e:

        return {
            "action": "error",
            "message": str(e)
        }


# ============================================================
# WINDOWS FILESYSTEM API
# ============================================================

def filesystem_mkdir(path):

    try:

        target = Path(path).expanduser()

        target.mkdir(
            parents=True,
            exist_ok=True
        )

        return f"Directory created: {target.resolve()}"

    except Exception as e:

        return f"mkdir error: {e}"


def filesystem_ls(path="."):

    try:

        target = Path(path).expanduser()

        if not target.exists():

            return f"Path does not exist: {target}"

        if not target.is_dir():

            return f"Not a directory: {target}"

        items = []

        for item in sorted(
            target.iterdir(),
            key=lambda x: (not x.is_dir(), x.name.lower())
        ):

            if item.is_dir():

                items.append(
                    f"<DIR>  {item.name}"
                )

            else:

                items.append(
                    f"        {item.name}"
                )

        if not items:

            return "(empty)"

        return "\n".join(items)

    except Exception as e:

        return f"ls error: {e}"


def filesystem_cd(path):

    try:

        target = Path(path).expanduser().resolve()

        if not target.exists():

            return f"Directory does not exist: {target}"

        if not target.is_dir():

            return f"Not a directory: {target}"

        os.chdir(target)

        return f"Changed directory to: {target}"

    except Exception as e:

        return f"cd error: {e}"


def filesystem_touch(path):

    try:

        target = Path(path).expanduser()

        target.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        target.touch(
            exist_ok=True
        )

        return f"File created: {target.resolve()}"

    except Exception as e:

        return f"touch error: {e}"


def filesystem_rm(path):

    try:

        target = Path(path).expanduser()

        if not target.exists():

            return f"Path does not exist: {target}"

        if target.is_dir():

            import shutil

            shutil.rmtree(target)

        else:

            target.unlink()

        return f"Removed: {target}"

    except Exception as e:

        return f"rm error: {e}"


# ============================================================
# WINDOWS PROCESS API
# ============================================================

def process_execute(command):

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

            if output:
                output += "\n"

            output += result.stderr

        if not output:

            return f"Process exited with code {result.returncode}"

        return output.strip()

    except Exception as e:

        return f"Process error: {e}"


# ============================================================
# API FUNCTION REGISTRY
# ============================================================

API_FUNCTIONS = {

    "filesystem.mkdir":
        lambda args: filesystem_mkdir(
            args.get("path", ".")
        ),

    "filesystem.ls":
        lambda args: filesystem_ls(
            args.get("path", ".")
        ),

    "filesystem.cd":
        lambda args: filesystem_cd(
            args.get("path", ".")
        ),

    "filesystem.touch":
        lambda args: filesystem_touch(
            args.get("path", "")
        ),

    "filesystem.rm":
        lambda args: filesystem_rm(
            args.get("path", "")
        ),

    "process.execute":
        lambda args: process_execute(
            args.get("command", "")
        )
}


# ============================================================
# CVE COMMAND PARSER
# ============================================================

def parse_cve_command(user_command):

    try:

        parts = shlex.split(
            user_command,
            posix=False
        )

    except ValueError as e:

        return {
            "error": f"Command parsing error: {e}"
        }

    if not parts:

        return {
            "error": "Empty command."
        }

    if parts[0].lower() != "cve":

        return {
            "error": "EXROOT commands must begin with: cve"
        }

    if len(parts) < 2:

        return {
            "error": "No CVE command was provided."
        }

    command_name = parts[1].lower()

    arguments = parts[2:]

    return {
        "command": command_name,
        "arguments": arguments
    }


# ============================================================
# MAPLE EXECUTION
# ============================================================

def execute_maple_decision(decision):

    action = decision.get("action")

    # --------------------------------------------------------
    # NORMAL RESPONSE
    # --------------------------------------------------------

    if action == "respond":

        return decision.get(
            "message",
            ""
        )

    # --------------------------------------------------------
    # ERROR
    # --------------------------------------------------------

    if action == "error":

        return decision.get(
            "message",
            "Maple error."
        )

    # --------------------------------------------------------
    # DIRECT EXECUTION
    # --------------------------------------------------------

    if action == "execute":

        api_function = decision.get(
            "api_function"
        )

        arguments = decision.get(
            "arguments",
            {}
        )

        if not api_function:

            return "Maple did not provide an API function."

        executor = API_FUNCTIONS.get(
            api_function
        )

        if not executor:

            return (
                f"Unknown EXROOT API function: "
                f"{api_function}"
            )

        try:

            return executor(arguments)

        except Exception as e:

            return (
                f"Execution error in "
                f"{api_function}: {e}"
            )

    return (
        "Maple returned an unknown action: "
        + json.dumps(decision)
    )


# ============================================================
# MAIN MAPLE PIPELINE
# ============================================================

def process_command(user_command):

    # --------------------------------------------------------
    # 1. Parse CVE
    # --------------------------------------------------------

    parsed = parse_cve_command(
        user_command
    )

    if "error" in parsed:

        return parsed["error"]

    command_name = parsed["command"]

    raw_arguments = parsed["arguments"]

    # --------------------------------------------------------
    # 2. Load command knowledge from Airtable
    # --------------------------------------------------------

    knowledge = get_airtable_command(
        command_name
    )

    if "error" in knowledge:

        return knowledge["error"]

    # --------------------------------------------------------
    # 3. Convert positional arguments into useful arguments
    # --------------------------------------------------------

    arguments = {}

    if raw_arguments:

        # Most CVE filesystem commands use
        # their first argument as the path.

        arguments["path"] = raw_arguments[0]

        if len(raw_arguments) > 1:

            arguments["extra"] = raw_arguments[1:]

    # --------------------------------------------------------
    # 4. Ask Maple / GPT-OSS-120B
    # --------------------------------------------------------

    decision = ask_maple(
        user_command,
        command_name,
        arguments,
        knowledge
    )

    # --------------------------------------------------------
    # 5. Directly execute Maple's decision
    # --------------------------------------------------------

    return execute_maple_decision(
        decision
    )
