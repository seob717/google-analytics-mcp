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

"""Common utilities for the Google Tag Manager MCP server."""

import os


def _norm(value: int | str, label: str) -> str:
    """Normalizes a GTM numeric ID to a bare string.

    Accepts an int, a bare number string, or a full resource path; returns the
    trailing numeric segment as a string.
    """
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        tail = value.strip().rstrip("/").split("/")[-1]
        if tail.isdigit():
            return tail
    raise ValueError(f"Invalid {label}: {value!r}. Expected a number.")


def account_path(account_id: int | str) -> str:
    """Returns 'accounts/{account_id}'."""
    return f"accounts/{_norm(account_id, 'account_id')}"


def container_path(account_id: int | str, container_id: int | str) -> str:
    """Returns 'accounts/{a}/containers/{c}'."""
    return f"{account_path(account_id)}/containers/{_norm(container_id, 'container_id')}"


def workspace_path(
    account_id: int | str, container_id: int | str, workspace_id: int | str
) -> str:
    """Returns the workspace resource path."""
    return (
        f"{container_path(account_id, container_id)}"
        f"/workspaces/{_norm(workspace_id, 'workspace_id')}"
    )


def version_path(
    account_id: int | str, container_id: int | str, version_id: int | str
) -> str:
    """Returns the container version resource path."""
    return (
        f"{container_path(account_id, container_id)}"
        f"/versions/{_norm(version_id, 'version_id')}"
    )


def entity_path(
    account_id: int | str,
    container_id: int | str,
    workspace_id: int | str,
    kind: str,
    entity_id: int | str,
) -> str:
    """Returns a workspace-scoped entity path (tags/triggers/variables)."""
    return (
        f"{workspace_path(account_id, container_id, workspace_id)}"
        f"/{kind}/{_norm(entity_id, kind)}"
    )


def destructive_allowed() -> bool:
    """Whether destructive operations (delete/publish) are enabled."""
    return os.environ.get("GTM_MCP_ALLOW_DESTRUCTIVE") == "1"


def ensure_destructive_allowed(action: str) -> None:
    """Raises PermissionError unless destructive operations are enabled.

    Guards delete/publish so they can't run unless the operator opts in with
    GTM_MCP_ALLOW_DESTRUCTIVE=1.
    """
    if not destructive_allowed():
        raise PermissionError(
            f"'{action}' is a destructive operation and is disabled. "
            "Set GTM_MCP_ALLOW_DESTRUCTIVE=1 in the server environment to enable it."
        )
