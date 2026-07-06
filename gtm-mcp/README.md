# Google Tag Manager MCP Server (read + write)

A local [MCP](https://modelcontextprotocol.io) server that exposes the
[Google Tag Manager API v2](https://developers.google.com/tag-platform/tag-manager/api/v2)
to LLM clients (Claude Desktop, Claude Code CLI, …). It runs as a stdio
subprocess — no hosting, no ports — and authenticates with your local
[Application Default Credentials (ADC)](https://cloud.google.com/docs/authentication/provide-credentials-adc).

> This package lives inside the `google-analytics-mcp` fork for now and is
> designed to be extracted into its own repository later: it has no imports
> from the sibling `analytics_mcp` package and ships its own `pyproject.toml`.

## Tools 🛠️

All IDs are the **numeric** GTM IDs (not the public `GTM-XXXX` code). Discover
them with `list_accounts` → `list_containers` → `list_workspaces`.

**Read:** `list_accounts`, `list_containers`, `get_container`, `list_workspaces`,
`get_workspace`, `list_tags`, `get_tag`, `list_triggers`, `get_trigger`,
`list_variables`, `get_variable`, `list_built_in_variables`, `list_versions`,
`get_version`, `get_live_version`

**Write** (workspace-scoped; nothing goes live until you create + publish a
version): `create_tag`, `update_tag`, `delete_tag`, `create_trigger`,
`update_trigger`, `delete_trigger`, `create_variable`, `update_variable`,
`delete_variable`, `create_workspace`, `create_version`, `publish_version`

### Destructive-operation guard 🔒

`delete_*` and `publish_version` refuse to run unless the server environment
sets `GTM_MCP_ALLOW_DESTRUCTIVE=1`. Create/update are always allowed but only
affect a workspace until published.

## Setup

1. Enable the **Tag Manager API** in your Google Cloud project.
2. Configure ADC with the Tag Manager scopes:

   ```shell
   gcloud auth application-default login \
     --scopes \
     https://www.googleapis.com/auth/tagmanager.readonly,\
   https://www.googleapis.com/auth/tagmanager.edit.containers,\
   https://www.googleapis.com/auth/tagmanager.edit.containerversions,\
   https://www.googleapis.com/auth/tagmanager.publish,\
   https://www.googleapis.com/auth/cloud-platform
   ```

3. Install the server (from this fork, until it has its own repo):

   ```shell
   uv tool install "git+https://github.com/seob717/google-analytics-mcp.git@feat/google-ads-mcp-setup#subdirectory=gtm-mcp"
   ```

4. Register it with the Claude Code CLI (user scope):

   ```shell
   claude mcp add-json -s user tagmanager-mcp '{
     "command": "'"$HOME"'/.local/bin/tagmanager-mcp",
     "args": [],
     "env": {
       "GOOGLE_APPLICATION_CREDENTIALS": "'"$HOME"'/.config/gcloud/application_default_credentials.json",
       "GOOGLE_CLOUD_PROJECT": "YOUR_PROJECT_ID"
     }
   }'
   ```

   To enable delete/publish, add `"GTM_MCP_ALLOW_DESTRUCTIVE": "1"` to `env`.

   For Claude Desktop, add the same block under `mcpServers` in
   `claude_desktop_config.json`.

## Development

```shell
uv sync --extra dev
uv run pytest
```
