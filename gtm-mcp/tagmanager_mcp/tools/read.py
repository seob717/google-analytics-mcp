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

"""Read-only tools for inspecting Google Tag Manager configuration.

All IDs are the numeric GTM IDs (not the public 'GTM-XXXX' code). Use
`list_accounts` → `list_containers` → `list_workspaces` to discover them.
"""

import asyncio
from typing import Any, Dict, List

from tagmanager_mcp.tools.client import tagmanager
from tagmanager_mcp.tools.utils import (
    account_path,
    container_path,
    entity_path,
    version_path,
    workspace_path,
)


async def _call(fn):
    return await asyncio.to_thread(lambda: fn().execute())


async def list_accounts() -> List[Dict[str, Any]]:
    """Lists the GTM accounts the authenticated user can access."""
    res = await _call(lambda: tagmanager().accounts().list())
    return res.get("account", [])


async def list_containers(account_id: int | str) -> List[Dict[str, Any]]:
    """Lists containers in an account.

    Args:
        account_id: The numeric GTM account ID.
    """
    parent = account_path(account_id)
    res = await _call(lambda: tagmanager().accounts().containers().list(parent=parent))
    return res.get("container", [])


async def get_container(
    account_id: int | str, container_id: int | str
) -> Dict[str, Any]:
    """Returns details for a single container.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
    """
    path = container_path(account_id, container_id)
    return await _call(lambda: tagmanager().accounts().containers().get(path=path))


async def list_workspaces(
    account_id: int | str, container_id: int | str
) -> List[Dict[str, Any]]:
    """Lists workspaces in a container.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
    """
    parent = container_path(account_id, container_id)
    res = await _call(
        lambda: tagmanager().accounts().containers().workspaces().list(parent=parent)
    )
    return res.get("workspace", [])


async def get_workspace(
    account_id: int | str, container_id: int | str, workspace_id: int | str
) -> Dict[str, Any]:
    """Returns details for a single workspace.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
        workspace_id: The numeric GTM workspace ID.
    """
    path = workspace_path(account_id, container_id, workspace_id)
    return await _call(
        lambda: tagmanager().accounts().containers().workspaces().get(path=path)
    )


def _workspaces(svc):
    return svc.accounts().containers().workspaces()


async def list_tags(
    account_id: int | str, container_id: int | str, workspace_id: int | str
) -> List[Dict[str, Any]]:
    """Lists tags in a workspace.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
        workspace_id: The numeric GTM workspace ID.
    """
    parent = workspace_path(account_id, container_id, workspace_id)
    res = await _call(lambda: _workspaces(tagmanager()).tags().list(parent=parent))
    return res.get("tag", [])


async def get_tag(
    account_id: int | str,
    container_id: int | str,
    workspace_id: int | str,
    tag_id: int | str,
) -> Dict[str, Any]:
    """Returns details for a single tag.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
        workspace_id: The numeric GTM workspace ID.
        tag_id: The numeric tag ID.
    """
    path = entity_path(account_id, container_id, workspace_id, "tags", tag_id)
    return await _call(lambda: _workspaces(tagmanager()).tags().get(path=path))


async def list_triggers(
    account_id: int | str, container_id: int | str, workspace_id: int | str
) -> List[Dict[str, Any]]:
    """Lists triggers in a workspace.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
        workspace_id: The numeric GTM workspace ID.
    """
    parent = workspace_path(account_id, container_id, workspace_id)
    res = await _call(lambda: _workspaces(tagmanager()).triggers().list(parent=parent))
    return res.get("trigger", [])


async def get_trigger(
    account_id: int | str,
    container_id: int | str,
    workspace_id: int | str,
    trigger_id: int | str,
) -> Dict[str, Any]:
    """Returns details for a single trigger.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
        workspace_id: The numeric GTM workspace ID.
        trigger_id: The numeric trigger ID.
    """
    path = entity_path(account_id, container_id, workspace_id, "triggers", trigger_id)
    return await _call(lambda: _workspaces(tagmanager()).triggers().get(path=path))


async def list_variables(
    account_id: int | str, container_id: int | str, workspace_id: int | str
) -> List[Dict[str, Any]]:
    """Lists user-defined variables in a workspace.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
        workspace_id: The numeric GTM workspace ID.
    """
    parent = workspace_path(account_id, container_id, workspace_id)
    res = await _call(lambda: _workspaces(tagmanager()).variables().list(parent=parent))
    return res.get("variable", [])


async def get_variable(
    account_id: int | str,
    container_id: int | str,
    workspace_id: int | str,
    variable_id: int | str,
) -> Dict[str, Any]:
    """Returns details for a single variable.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
        workspace_id: The numeric GTM workspace ID.
        variable_id: The numeric variable ID.
    """
    path = entity_path(account_id, container_id, workspace_id, "variables", variable_id)
    return await _call(lambda: _workspaces(tagmanager()).variables().get(path=path))


async def list_built_in_variables(
    account_id: int | str, container_id: int | str, workspace_id: int | str
) -> List[Dict[str, Any]]:
    """Lists the enabled built-in variables in a workspace.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
        workspace_id: The numeric GTM workspace ID.
    """
    parent = workspace_path(account_id, container_id, workspace_id)
    res = await _call(
        lambda: _workspaces(tagmanager()).built_in_variables().list(parent=parent)
    )
    return res.get("builtInVariable", [])


async def list_versions(
    account_id: int | str, container_id: int | str
) -> List[Dict[str, Any]]:
    """Lists container version headers (id, name, and metadata) for a container.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
    """
    parent = container_path(account_id, container_id)
    res = await _call(
        lambda: tagmanager().accounts().containers().version_headers().list(parent=parent)
    )
    return res.get("containerVersionHeader", [])


async def get_version(
    account_id: int | str, container_id: int | str, version_id: int | str
) -> Dict[str, Any]:
    """Returns a full container version, including all tags/triggers/variables.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
        version_id: The numeric container version ID.
    """
    path = version_path(account_id, container_id, version_id)
    return await _call(lambda: tagmanager().accounts().containers().versions().get(path=path))


async def get_live_version(
    account_id: int | str, container_id: int | str
) -> Dict[str, Any]:
    """Returns the currently published (live) container version.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
    """
    parent = container_path(account_id, container_id)
    return await _call(
        lambda: tagmanager().accounts().containers().versions().live(parent=parent)
    )
