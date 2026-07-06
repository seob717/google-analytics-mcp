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

"""Write tools for Google Tag Manager configuration.

Create/update happen inside a workspace and do not affect the live container
until a version is created and published. Delete and publish are destructive
and require GTM_MCP_ALLOW_DESTRUCTIVE=1 in the server environment.
"""

import asyncio
from typing import Any, Dict

from tagmanager_mcp.tools.client import tagmanager
from tagmanager_mcp.tools.utils import (
    container_path,
    ensure_destructive_allowed,
    entity_path,
    version_path,
    workspace_path,
)


async def _run(fn):
    return await asyncio.to_thread(lambda: fn().execute())


def _workspaces(svc):
    return svc.accounts().containers().workspaces()


# --- tags ---------------------------------------------------------------------


async def create_tag(
    account_id: int | str,
    container_id: int | str,
    workspace_id: int | str,
    tag: Dict[str, Any],
) -> Dict[str, Any]:
    """Creates a tag in a workspace.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
        workspace_id: The numeric GTM workspace ID.
        tag: The GTM Tag resource body, e.g.
          {"name": "GA4 event", "type": "gaawe", "parameter": [...]}.
          See https://developers.google.com/tag-platform/tag-manager/api/v2/reference/accounts/containers/workspaces/tags.
    """
    parent = workspace_path(account_id, container_id, workspace_id)
    return await _run(lambda: _workspaces(tagmanager()).tags().create(parent=parent, body=tag))


async def update_tag(
    account_id: int | str,
    container_id: int | str,
    workspace_id: int | str,
    tag_id: int | str,
    tag: Dict[str, Any],
) -> Dict[str, Any]:
    """Updates (replaces) an existing tag.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
        workspace_id: The numeric GTM workspace ID.
        tag_id: The numeric tag ID.
        tag: The full GTM Tag resource body to write.
    """
    path = entity_path(account_id, container_id, workspace_id, "tags", tag_id)
    return await _run(lambda: _workspaces(tagmanager()).tags().update(path=path, body=tag))


async def delete_tag(
    account_id: int | str,
    container_id: int | str,
    workspace_id: int | str,
    tag_id: int | str,
) -> Dict[str, Any]:
    """Deletes a tag. Destructive: requires GTM_MCP_ALLOW_DESTRUCTIVE=1.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
        workspace_id: The numeric GTM workspace ID.
        tag_id: The numeric tag ID.
    """
    ensure_destructive_allowed("delete_tag")
    path = entity_path(account_id, container_id, workspace_id, "tags", tag_id)
    await _run(lambda: _workspaces(tagmanager()).tags().delete(path=path))
    return {"deleted": path}


# --- triggers -----------------------------------------------------------------


async def create_trigger(
    account_id: int | str,
    container_id: int | str,
    workspace_id: int | str,
    trigger: Dict[str, Any],
) -> Dict[str, Any]:
    """Creates a trigger in a workspace.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
        workspace_id: The numeric GTM workspace ID.
        trigger: The GTM Trigger resource body, e.g.
          {"name": "All Pages", "type": "pageview"}.
    """
    parent = workspace_path(account_id, container_id, workspace_id)
    return await _run(
        lambda: _workspaces(tagmanager()).triggers().create(parent=parent, body=trigger)
    )


async def update_trigger(
    account_id: int | str,
    container_id: int | str,
    workspace_id: int | str,
    trigger_id: int | str,
    trigger: Dict[str, Any],
) -> Dict[str, Any]:
    """Updates (replaces) an existing trigger.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
        workspace_id: The numeric GTM workspace ID.
        trigger_id: The numeric trigger ID.
        trigger: The full GTM Trigger resource body to write.
    """
    path = entity_path(account_id, container_id, workspace_id, "triggers", trigger_id)
    return await _run(
        lambda: _workspaces(tagmanager()).triggers().update(path=path, body=trigger)
    )


async def delete_trigger(
    account_id: int | str,
    container_id: int | str,
    workspace_id: int | str,
    trigger_id: int | str,
) -> Dict[str, Any]:
    """Deletes a trigger. Destructive: requires GTM_MCP_ALLOW_DESTRUCTIVE=1.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
        workspace_id: The numeric GTM workspace ID.
        trigger_id: The numeric trigger ID.
    """
    ensure_destructive_allowed("delete_trigger")
    path = entity_path(account_id, container_id, workspace_id, "triggers", trigger_id)
    await _run(lambda: _workspaces(tagmanager()).triggers().delete(path=path))
    return {"deleted": path}


# --- variables ----------------------------------------------------------------


async def create_variable(
    account_id: int | str,
    container_id: int | str,
    workspace_id: int | str,
    variable: Dict[str, Any],
) -> Dict[str, Any]:
    """Creates a user-defined variable in a workspace.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
        workspace_id: The numeric GTM workspace ID.
        variable: The GTM Variable resource body, e.g.
          {"name": "My DLV", "type": "v", "parameter": [...]}.
    """
    parent = workspace_path(account_id, container_id, workspace_id)
    return await _run(
        lambda: _workspaces(tagmanager()).variables().create(parent=parent, body=variable)
    )


async def update_variable(
    account_id: int | str,
    container_id: int | str,
    workspace_id: int | str,
    variable_id: int | str,
    variable: Dict[str, Any],
) -> Dict[str, Any]:
    """Updates (replaces) an existing variable.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
        workspace_id: The numeric GTM workspace ID.
        variable_id: The numeric variable ID.
        variable: The full GTM Variable resource body to write.
    """
    path = entity_path(account_id, container_id, workspace_id, "variables", variable_id)
    return await _run(
        lambda: _workspaces(tagmanager()).variables().update(path=path, body=variable)
    )


async def delete_variable(
    account_id: int | str,
    container_id: int | str,
    workspace_id: int | str,
    variable_id: int | str,
) -> Dict[str, Any]:
    """Deletes a variable. Destructive: requires GTM_MCP_ALLOW_DESTRUCTIVE=1.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
        workspace_id: The numeric GTM workspace ID.
        variable_id: The numeric variable ID.
    """
    ensure_destructive_allowed("delete_variable")
    path = entity_path(account_id, container_id, workspace_id, "variables", variable_id)
    await _run(lambda: _workspaces(tagmanager()).variables().delete(path=path))
    return {"deleted": path}


# --- workspaces & versions ----------------------------------------------------


async def create_workspace(
    account_id: int | str,
    container_id: int | str,
    name: str,
    description: str | None = None,
) -> Dict[str, Any]:
    """Creates a new workspace in a container.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
        name: Display name for the workspace.
        description: Optional workspace description.
    """
    parent = container_path(account_id, container_id)
    body: Dict[str, Any] = {"name": name}
    if description is not None:
        body["description"] = description
    return await _run(
        lambda: _workspaces(tagmanager()).create(parent=parent, body=body)
    )


async def create_version(
    account_id: int | str,
    container_id: int | str,
    workspace_id: int | str,
    name: str | None = None,
    notes: str | None = None,
) -> Dict[str, Any]:
    """Creates a container version from a workspace's current changes.

    This snapshots the workspace but does not publish it.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
        workspace_id: The numeric GTM workspace ID.
        name: Optional name for the new version.
        notes: Optional notes for the new version.
    """
    path = workspace_path(account_id, container_id, workspace_id)
    body: Dict[str, Any] = {}
    if name is not None:
        body["name"] = name
    if notes is not None:
        body["notes"] = notes
    return await _run(
        lambda: _workspaces(tagmanager()).create_version(path=path, body=body)
    )


async def publish_version(
    account_id: int | str, container_id: int | str, version_id: int | str
) -> Dict[str, Any]:
    """Publishes a container version, making it live. Destructive: requires
    GTM_MCP_ALLOW_DESTRUCTIVE=1.

    Args:
        account_id: The numeric GTM account ID.
        container_id: The numeric GTM container ID.
        version_id: The numeric container version ID to publish.
    """
    ensure_destructive_allowed("publish_version")
    path = version_path(account_id, container_id, version_id)
    return await _run(
        lambda: tagmanager().accounts().containers().versions().publish(path=path)
    )
