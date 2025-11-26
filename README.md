# Tembo Task Manager MCP for Poke

An MCP server that lets you create and queue Tembo coding tasks directly from Poke, then let Tembo open pull requests in your GitHub repos. SHIP FROM YOUR DMs!!!

## Features

- Single MCP tool: `create_tembo_task`.
- Calls Tembo’s public API `POST /task/create` with:
  - `prompt`
  - `repositories`
  - optional `agent`, `branch`, `queueRightAway`
- Uses `TEMBO_API_KEY` (and optional `TEMBO_API_BASE_URL`) from the environment.

For the full API shape, see Tembo’s Create Task docs: https://docs.tembo.io/api-reference/public-api/create-task

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
3. In a conversation, ask Poke (in natural language) to use the `Tembo Task Manager` integration’s `create_tembo_task` tool to create and queue a task for your repo.

Tembo will pick up the task, run the agent, and open a PR in the configured repository.

## Self‑hosting for other Tembo accounts

If someone else wants to use this MCP with **their own** Tembo organization:

1. Fork or clone this repo.
2. Set `TEMBO_API_KEY` (and optional `TEMBO_API_BASE_URL`) for their Tembo account.
3. Deploy their own copy (Render or elsewhere).
4. Point their Poke integration at their own `/mcp` URL.

Your MCP code stays the same; the Tembo org is determined entirely by the API key in the environment.



