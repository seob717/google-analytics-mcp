# Copyright 2026 seob717
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Singleton MCP server that registers the Google Tag Manager tools."""

import json
import sys

from mcp import types as mcp_types
from mcp.server.lowlevel import Server

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type

from tagmanager_mcp.tools import read, write

# All exposed tool functions, in a sensible discovery-first order.
_FUNCTIONS = [
    read.list_accounts,
    read.list_containers,
    read.get_container,
    read.list_workspaces,
    read.get_workspace,
    read.list_tags,
    read.get_tag,
    read.list_triggers,
    read.get_trigger,
    read.list_variables,
    read.get_variable,
    read.list_built_in_variables,
    read.list_versions,
    read.get_version,
    read.get_live_version,
    write.create_tag,
    write.update_tag,
    write.delete_tag,
    write.create_trigger,
    write.update_trigger,
    write.delete_trigger,
    write.create_variable,
    write.update_variable,
    write.delete_variable,
    write.create_workspace,
    write.create_version,
    write.publish_version,
]

tools = [FunctionTool(fn) for fn in _FUNCTIONS]
tool_map = {t.name: t for t in tools}

app = Server(name="Google Tag Manager MCP Server")


def _sanitize_additional_properties(node) -> None:
    """Forces additionalProperties to a boolean, which some MCP clients require."""
    if not isinstance(node, dict):
        return
    if "additionalProperties" in node and not isinstance(
        node["additionalProperties"], bool
    ):
        node["additionalProperties"] = True
    for child in node.values():
        if isinstance(child, dict):
            _sanitize_additional_properties(child)
        elif isinstance(child, list):
            for element in child:
                _sanitize_additional_properties(element)


mcp_tools = [adk_to_mcp_tool_type(tool) for tool in tools]

for tool in mcp_tools:
    # ADK emits {} for no-parameter tools; MCP clients expect an object schema.
    if tool.inputSchema == {}:
        tool.inputSchema = {"type": "object", "properties": {}}
    # Union type hints (e.g. `str | None`) can emit a spurious "type": "null".
    for prop in tool.inputSchema.get("properties", {}).values():
        if "anyOf" in prop and prop.get("type") == "null":
            del prop["type"]
    _sanitize_additional_properties(tool.inputSchema)


@app.list_tools()
async def list_tools() -> list[mcp_types.Tool]:
    return mcp_tools


@app.call_tool()
async def call_mcp_tool(name: str, arguments: dict) -> list[mcp_types.Content]:
    if name not in tool_map:
        error = {"error": f"Tool '{name}' not implemented by this server."}
        return [mcp_types.TextContent(type="text", text=json.dumps(error))]

    try:
        response = await tool_map[name].run_async(args=arguments, tool_context=None)
        return [
            mcp_types.TextContent(type="text", text=json.dumps(response, indent=2, default=str))
        ]
    except Exception as e:
        print(f"MCP Server: error executing '{name}': {e}", file=sys.stderr)
        error = {"error": f"Failed to execute tool '{name}': {str(e)}"}
        return [mcp_types.TextContent(type="text", text=json.dumps(error))]
