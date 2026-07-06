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

import pytest

from tagmanager_mcp.tools import utils


def test_path_builders_accept_ints_and_strings():
    assert utils.account_path(6) == "accounts/6"
    assert utils.container_path(6, 42) == "accounts/6/containers/42"
    assert (
        utils.workspace_path("6", "42", "3")
        == "accounts/6/containers/42/workspaces/3"
    )
    assert (
        utils.version_path(6, 42, 9)
        == "accounts/6/containers/42/versions/9"
    )
    assert (
        utils.entity_path(6, 42, 3, "tags", 11)
        == "accounts/6/containers/42/workspaces/3/tags/11"
    )


def test_norm_extracts_trailing_id_from_full_path():
    assert utils.container_path(6, "accounts/6/containers/42") == (
        "accounts/6/containers/42"
    )


def test_norm_rejects_non_numeric():
    with pytest.raises(ValueError):
        utils.account_path("not-a-number")


def test_destructive_gate_disabled_by_default(monkeypatch):
    monkeypatch.delenv("GTM_MCP_ALLOW_DESTRUCTIVE", raising=False)
    assert utils.destructive_allowed() is False
    with pytest.raises(PermissionError):
        utils.ensure_destructive_allowed("delete_tag")


def test_destructive_gate_enabled_by_env(monkeypatch):
    monkeypatch.setenv("GTM_MCP_ALLOW_DESTRUCTIVE", "1")
    assert utils.destructive_allowed() is True
    # Should not raise.
    utils.ensure_destructive_allowed("publish_version")
