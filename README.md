# Tembo Task Manager MCP for Poke

An MCP server that lets you create and queue Tembo coding tasks directly from Poke, then let Tembo open pull requests in your GitHub repos. SHIP FROM YOUR DMs!!!

## Features

- MCP tool: `create_tembo_task`
  - Calls Tembo’s public API `POST /task/create` with:
    - `prompt`
    - optional `repositories`, `agent`, `branch`, `queueRightAway`
  - Uses `TEMBO_API_KEY` (and optional `TEMBO_API_BASE_URL`) from the environment.
- MCP tool: `create_tembo_automation`
  - Calls Tembo’s public API `POST /automation` with:
    - `name`, `aim`, `cron` (required)
    - optional `mcp_servers`, `agent`, `triggers`, `extra_json_content`
  - Creates scheduled automations that run on a cron schedule.
  - Uses `TEMBO_API_KEY` from the environment.
- MCP tool: `check_pr_mergeable`
  - Calls GitHub’s REST API `GET /repos/{owner}/{repo}/pulls/{pull_number}`.
  - Returns whether a PR is cleanly mergeable or has merge conflicts between its head and base branches.
  - Uses `GITHUB_TOKEN` from the environment with “Pull requests: read” scope.

For the full API shape, see Tembo’s API docs: https://docs.tembo.io/api-reference/public-api

## Local setup

```bash
git clone https://github.com/AnandVishesh1301/temboXpoke.git
cd temboXpoke
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file:

```env
TEMBO_API_KEY=your_tembo_api_key
TEMBO_API_BASE_URL=https://api.tembo.io
```

Run the server:

```bash
python src/server.py
```

This starts a FastMCP HTTP server on `http://localhost:8000/mcp`.

## Deploying to Render

This repo includes a `render.yaml` modeled on InteractionCo’s MCP server template.

High level:

- Connect the repo in Render as a Python **Web Service**.
- Build command: `pip install -r requirements.txt` (Render UI or `render.yaml`).
- Start command: `python src/server.py`.
- Set environment variables in the Render dashboard:
  - `TEMBO_API_KEY`
  - `TEMBO_API_BASE_URL` (usually `https://api.tembo.io`)
  - `GITHUB_TOKEN` (GitHub PAT with at least “Pull requests: read” access)

Once live, your MCP endpoint will be:

```text
https://<your-service-name>.onrender.com/mcp
```

## Using from Poke

In Poke:

1. Go to **Settings → Integrations → Custom MCP Servers**.
2. Add a new integration:
   - Name: `Tembo Task Manager`
   - Server URL: `https://<your-service-name>.onrender.com/mcp`
   - API key: leave empty (Tembo auth is handled on the server side).
3. In a conversation, ask Poke (in natural language) to:
   - use the `create_tembo_task` tool to create and queue a Tembo coding task for your repo,
   - use the `create_tembo_automation` tool to set up scheduled automations that run on a cron schedule, or
   - use the `check_pr_mergeable` tool to see whether a specific GitHub pull request is cleanly mergeable or has conflicts.

Tembo will pick up created tasks, run the agent, and open PRs in the configured repositories.

## Self‑hosting for other Tembo accounts

If someone else wants to use this MCP with **their own** Tembo organization:

1. Fork or clone this repo.
2. Set `TEMBO_API_KEY` (and optional `TEMBO_API_BASE_URL`) for their Tembo account.
3. Deploy their own copy (Render or elsewhere).
4. Point their Poke integration at their own `/mcp` URL.

Your MCP code stays the same; the Tembo org is determined entirely by the API key in the environment.



