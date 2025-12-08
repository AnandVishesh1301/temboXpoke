"""
Tembo Task Manager MCP server entrypoint.

FastMCP server exposed over HTTP (/mcp) that forwards 
`create_tembo_task` tool to the Tembo public API `/task/create`.
"""

from __future__ import annotations

import os
from typing import Any, Dict

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP


# Load local .env for development; on Render, env vars are injected directly.
load_dotenv()

mcp = FastMCP("Tembo Task Manager")

TEMBO_BASE_URL = os.getenv("TEMBO_API_BASE_URL", "https://api.tembo.io")


def _build_tembo_url(path: str) -> str:
    return TEMBO_BASE_URL.rstrip("/") + path


@mcp.tool
def create_tembo_task(
    prompt: str,
    repositories: list[str],
    agent: str | None = None,
    branch: str | None = None,
    queue_right_away: bool | None = None,
) -> Dict[str, Any]:
    """
    Create an automated coding task using a Tembo agent (e.g., Claude-based models).

    This tool submits a request to Tembo's public API (`/task/create`) to have an
    AI-powered coding agent implement a change, fix a bug, refactor code, or add a
    feature in the specified repositories. When the agent completes the work, a
    pull request will be opened in the relevant repository (assuming those repos
    are already configured in Tembo).

    When to use:
      - To automate implementation of issues, features, bug fixes, refactors, or docs changes.
      - When you want Tembo's agent to update code across one or more repositories.

    Arguments:
        prompt (str):
            A clear, detailed summary of the code change or feature to be implemented
            by the agent. This is the primary task description (required).
        repositories (list[str]):
            One or more Git repository URLs that the task should operate on
            (required). Example: ["https://github.com/org/repo"].
        agent (str, optional):
            Specific Tembo agent identifier to use, e.g.
            "claudeCode:claude-4-5-sonnet". If omitted, Tembo's server-configured
            default agent will be used.
        branch (str, optional):
            Git branch to target for the new work / pull request. If omitted, Tembo
            will use its default behavior for branch selection.
        queue_right_away (bool, optional):
            If True, explicitly request immediate queuing of the task by Tembo. If
            omitted, Tembo's default for `queueRightAway` is used (defaults to true
            per current public API docs).

    Returns:
        On success:
            {
              "ok": True,
              "task": <full Tembo API response>,
              "id": "...",
              "status": "...",
              ...
            }

        On error:
            {
              "ok": False,
              "error": <explanation>,
              "status": <http status, if available>
            }

    Example:
        create_tembo_task(
            prompt="Add support for dark mode in the settings page",
            repositories=["https://github.com/me/project"],
            agent="claudeCode:claude-4-5-sonnet",
            branch="feature/dark-mode",
        )
    """
    ### API Reference
    # https://docs.tembo.io/api-reference/public-api/create-task

    api_key = os.getenv("TEMBO_API_KEY")
    if not api_key:
        return {
            "ok": False,
            "error": "Missing TEMBO_API_KEY env",
        }

    if not prompt:
        return {
            "ok": False,
            "error": "prompt is required and must be non-empty.",
        }

    if not repositories:
        return {
            "ok": False,
            "error": "repositories must be a non-empty list of repository URLs.",
        }

    payload: Dict[str, Any] = {
        "prompt": prompt,
        "repositories": repositories,
    }

    if agent is not None:
        payload["agent"] = agent
    if branch is not None:
        payload["branch"] = branch
    if queue_right_away is not None:
        payload["queueRightAway"] = queue_right_away

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    url = _build_tembo_url("/task/create")

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=30.0)
    except httpx.RequestError as exc:
        return {
            "ok": False,
            "error": f"Network error calling Tembo: {exc}",
        }

    # Tembo's Create Task docs specify 200 on success.
    if response.status_code != 200:
        try:
            data = response.json()
        except Exception:
            data = None

        error_message = None
        if isinstance(data, dict):
            error_message = data.get("error")

        return {
            "ok": False,
            "status": response.status_code,
            "error": error_message or response.text,
        }

    try:
        data = response.json()
    except Exception as exc:
        return {
            "ok": False,
            "status": response.status_code,
            "error": f"Failed to parse Tembo response JSON: {exc}",
        }

    # Surface key fields as top-level for convenience, keeping full object under "task".
    result: Dict[str, Any] = {
        "ok": True,
        "task": data,
    }

    if isinstance(data, dict):
        for field in (
            "id",
            "status",
            "title",
            "description",
            "createdAt",
            "updatedAt",
            "organizationId",
        ):
            if field in data:
                result[field] = data[field]

    return result


@mcp.tool
def create_tembo_automation(
    name: str,
    aim: str,
    cron: str,
    mcp_servers: list[str] | None = None,
    agent: str | None = None,
    triggers: list[Dict[str, Any]] | None = None,
    extra_json_content: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    
    """
    Create a scheduled Tembo automation using the public `/automation` API.

    This tool submits a request to Tembo's public API (`POST /automation`) to
    create an automation that runs on the schedule you specify and performs
    whatever ongoing work you describe as its aim.

    When to use:
      - To set up a recurring automation that should run on a cron schedule.
      - When you want Tembo to continuously perform a specific task or workflow.

    Arguments:
        name (str):
            Human‑readable name for the automation shown in Tembo's UI (required).
        aim (str):
            Natural‑language description of what the automation should do each
            time it runs. This is stored under `jsonContent.aim` (required).
        cron (str):
            Cron expression defining how frequently the automation should run
            (for example, "0 * * * *" for hourly). This is used to build the
            `schedules` array (required).
        mcp_servers (list[str], optional):
            List of MCP server identifiers this automation is allowed to call,
            passed through to the `mcpServers` field.
        agent (str, optional):
            Specific Tembo agent identifier to use for the automation, e.g.
            "claudeCode:claude-4-5-sonnet". If omitted, Tembo's defaults apply.
        triggers (list[dict], optional):
            Advanced: raw trigger objects to send as the `triggers` array.
            Each item should follow the API schema for triggers
            (see Tembo docs `integrationId`, `name`, `filters`).
        extra_json_content (dict, optional):
            Additional arbitrary JSON to merge into `jsonContent` alongside
            the `aim` field. Keys here must be JSON‑serializable.

    Returns:
        On success:
            {
              "ok": True,
              "automation": <full Tembo API response>,
              "id": "...",
              "name": "...",
              ...
            }

        On error:
            {
              "ok": False,
              "error": <explanation>,
              "status": <http status, if available>
            }

    API reference:
        https://api.tembo.io/#tag/public-api/post/automation
    """
    
    api_key = os.getenv("TEMBO_API_KEY")
    if not api_key:
        return {
            "ok": False,
            "error": "Missing TEMBO_API_KEY env",
        }

    if not name:
        return {
            "ok": False,
            "error": "name is required and must be non-empty.",
        }

    if not aim:
        return {
            "ok": False,
            "error": "aim is required and must be non-empty.",
        }

    if not cron:
        return {
            "ok": False,
            "error": "cron is required and must be a non-empty cron expression string.",
        }

    json_content: Dict[str, Any] = {"aim": aim}

    if extra_json_content is not None:
        if not isinstance(extra_json_content, dict):
            return {
                "ok": False,
                "error": "extra_json_content must be an object (dict) if provided.",
            }
        json_content.update(extra_json_content)

    payload: Dict[str, Any] = {
        "name": name,
        "jsonContent": json_content,
        "schedules": [
            {
                "cron": cron,
            }
        ],
    }

    if mcp_servers is not None:
        payload["mcpServers"] = mcp_servers

    if agent is not None:
        payload["agent"] = agent

    if triggers is not None:
        payload["triggers"] = triggers

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    url = _build_tembo_url("/automation")

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=30.0)
    except httpx.RequestError as exc:
        return {
            "ok": False,
            "error": f"Network error calling Tembo: {exc}",
        }

    if response.status_code != 200:
        try:
            data = response.json()
        except Exception:
            data = None

        error_message = None
        if isinstance(data, dict):
            error_message = data.get("error") or data.get("message")

        return {
            "ok": False,
            "status": response.status_code,
            "error": error_message or response.text,
        }

    try:
        data = response.json()
    except Exception as exc:
        return {
            "ok": False,
            "status": response.status_code,
            "error": f"Failed to parse Tembo response JSON: {exc}",
        }

    result: Dict[str, Any] = {
        "ok": True,
        "automation": data,
    }

    if isinstance(data, dict):
        for field in (
            "id",
            "name",
            "createdAt",
            "updatedAt",
            "enabledAt",
            "agent",
            "solutionType",
            "organizationId",
            "templateId",
            "archivedAt",
        ):
            if field in data:
                result[field] = data[field]

    return result


@mcp.tool
def check_pr_mergeable(
    repo_owner: str,
    repo_name: str,
    pr_number: int,
) -> Dict[str, Any]:
    """
    Check whether a GitHub pull request is cleanly mergeable or has merge conflicts.

    This tool calls GitHub's Pulls API (`GET /repos/{owner}/{repo}/pulls/{pull_number}`)
    and inspects the `mergeable` and `mergeable_state` fields to determine if the PR is
    cleanly mergeable, still being computed, or blocked by conflicts between the head
    and base branches.

    When to use:
      - Before triggering an automated change (e.g., a Tembo task) that targets the PR's base branch.
      - When you want to quickly confirm in chat whether a PR is currently safe to merge.
      - When triaging PRs to see which ones are clean vs. blocked by conflicts.

    Arguments:
        repo_owner (str):
            GitHub organization or user that owns the repository
            (for example, "tembo-io").
        repo_name (str):
            Repository name within that owner
            (for example, "temboXpoke").
        pr_number (int):
            Pull request number to inspect; must be a positive integer.

    Returns:
        On success:
            {
              "ok": True,
              "pr_number": <int>,
              "has_conflict": <bool | None>,  # True, False, or None if GitHub is still computing
              "mergeable": <bool | None>,
              "mergeable_state": <str | None>,
              "pr_url": <str | None>,
              "message": <human-readable summary>,
              "head_ref": <str | None>,
              "base_ref": <str | None>,
            }
        on error:
            {
              "ok": False,
              "error": <explanation>,
              "status": <http status, if available>,
            }

    Notes:
        Requires the `GITHUB_TOKEN` environment variable to be set with at least
        "Pull requests: read" access for the relevant repository.
    """
    ### API Reference docs:
    # https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return {
            "ok": False,
            "error": (
                "GITHUB_TOKEN environment variable not set. "
                "Create a fine-grained PAT with at least 'Pull requests: read' "
                "access for the relevant repositories."
            ),
        }

    if pr_number <= 0:
        return {
            "ok": False,
            "error": "pr_number must be a positive integer.",
        }

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pr_number}"

    try:
        response = httpx.get(url, headers=headers, timeout=15.0)
    except httpx.RequestError as exc:
        return {
            "ok": False,
            "error": f"Network error calling GitHub: {exc}",
        }

    if response.status_code == 404:
        return {
            "ok": False,
            "error": f"PR #{pr_number} not found in {repo_owner}/{repo_name}.",
        }

    if response.status_code in (401, 403):
        # Authentication / authorization issue – surface a clear hint about token scopes.
        try:
            data = response.json()
        except Exception:
            data = None

        message = None
        if isinstance(data, dict):
            message = data.get("message")

        return {
            "ok": False,
            "status": response.status_code,
            "error": (
                message
                or f"GitHub authentication/authorization error ({response.status_code}). "
                "Ensure GITHUB_TOKEN has access to this repository and 'Pull requests: read' scope."
            ),
        }

    if response.status_code != 200:
        return {
            "ok": False,
            "status": response.status_code,
            "error": f"GitHub API error: {response.status_code} {response.text}",
        }

    try:
        pr_data = response.json()
    except Exception as exc:
        return {
            "ok": False,
            "status": response.status_code,
            "error": f"Failed to parse GitHub PR JSON: {exc}",
        }

    mergeable = pr_data.get("mergeable")  # true, false, or null (while computing)
    mergeable_state = pr_data.get("mergeable_state")
    pr_url = pr_data.get("html_url")

    base = pr_data.get("base") or {}
    head = pr_data.get("head") or {}
    base_ref = base.get("ref")
    head_ref = head.get("ref")

    has_conflict: bool | None
    status_msg: str

    if mergeable is None:
        # GitHub is still computing mergeability; caller can retry later if needed.
        status_msg = (
            f"GitHub is still computing mergeability for PR #{pr_number}. "
            "Try again in a few seconds."
        )
        has_conflict = None
    elif mergeable is False or mergeable_state == "dirty":
        status_msg = (
            f"PR #{pr_number} has merge conflicts between "
            f"`{head_ref}` and `{base_ref}`."
        )
        has_conflict = True
    else:
        status_msg = (
            f"PR #{pr_number} is clean and mergeable between "
            f"`{head_ref}` and `{base_ref}`."
        )
        has_conflict = False

    return {
        "ok": True,
        "pr_number": pr_number,
        "has_conflict": has_conflict,
        "mergeable": mergeable,
        "mergeable_state": mergeable_state,
        "pr_url": pr_url,
        "message": status_msg,
        "head_ref": head_ref,
        "base_ref": base_ref,
    }


if __name__ == "__main__":
    # Render provides PORT; default to 8000 for local dev
    port = int(os.getenv("PORT", "8000"))
    mcp.run(transport="http", host="0.0.0.0", port=port)

