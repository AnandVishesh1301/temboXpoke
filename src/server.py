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

TEMBO_BASE_URL = os.getenv("TEMBO_API_BASE_URL", "https://internal.tembo.io")


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
    Create a Tembo coding task via the public API.

    Arguments:
        prompt: Description of the task to be performed.
        repositories: List of repository URLs the task relates to.
        agent: Optional Tembo agent identifier (e.g. \"claudeCode:claude-4-5-sonnet\").
        branch: Optional git branch to target for this task.
        queue_right_away: Optional flag mapped to Tembo's `queueRightAway`
            (defaults to Tembo's server-side default when omitted).

    Returns:
        A structured dict indicating success or failure. On success:
            {
              \"ok\": True,
              \"task\": <full Tembo response>,
              \"id\": ...,
              \"status\": ...,
              ...
            }
        On error:
            {
              \"ok\": False,
              \"error\": <message>,
              \"status\": <http status, if available>
            }
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

    # Surface key fields as top-level for convenience, keeping full object under \"task\".
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


if __name__ == "__main__":
    # Render provides PORT; default to 8000 for local dev
    port = int(os.getenv("PORT", "8000"))
    mcp.run(transport="http", host="0.0.0.0", port=port)

