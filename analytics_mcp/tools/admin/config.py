# Copyright 2025 Google LLC All Rights Reserved.
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

"""Read-only GA4 Admin tools for data streams and change history.

These complement the reporting tools by exposing property configuration that
the Data API can't see: data stream setup, the per-stream gtag snippet, and the
Change History (who changed what, and when). All are read-only and work with the
existing analytics.readonly scope.

Note: "connected site tags" are intentionally absent — the GA4 Admin API exposes
no method for them, so they can only be inspected in the GA4 Admin UI.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from analytics_mcp.tools.client import create_admin_alpha_api_client
from analytics_mcp.tools.utils import construct_property_rn, proto_to_dict
from google.analytics import admin_v1alpha


def _account_rn(account_id: int | str) -> str:
    return f"accounts/{str(account_id).strip().split('/')[-1]}"


def _data_stream_rn(property_id: int | str, data_stream_id: int | str) -> str:
    ds = str(data_stream_id).strip().split("/")[-1]
    return f"{construct_property_rn(property_id)}/dataStreams/{ds}"


def _parse_time(value: str) -> datetime:
    """Parses an ISO 8601 string to a timezone-aware datetime (assumes UTC)."""
    dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


async def list_data_streams(property_id: int | str) -> List[Dict[str, Any]]:
    """Lists the data streams (web/app) configured for a GA4 property.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
    """
    request = admin_v1alpha.ListDataStreamsRequest(
        parent=construct_property_rn(property_id)
    )

    def _sync_call():
        pager = create_admin_alpha_api_client().list_data_streams(request=request)
        return [proto_to_dict(page) for page in pager]

    return await asyncio.to_thread(_sync_call)


async def get_data_stream(
    property_id: int | str, data_stream_id: int | str
) -> Dict[str, Any]:
    """Returns configuration for a single data stream, including its measurement ID.

    Args:
        property_id: The Google Analytics property ID (number or 'properties/NUMBER').
        data_stream_id: The numeric data stream ID.
    """
    request = admin_v1alpha.GetDataStreamRequest(
        name=_data_stream_rn(property_id, data_stream_id)
    )

    def _sync_call():
        return proto_to_dict(
            create_admin_alpha_api_client().get_data_stream(request=request)
        )

    return await asyncio.to_thread(_sync_call)


async def get_global_site_tag(
    property_id: int | str, data_stream_id: int | str
) -> Dict[str, Any]:
    """Returns the gtag (G-XXXX) snippet for a web data stream.

    This is the tag GA4 tells you to install on the site. It does NOT include
    'connected site tags', which the Admin API does not expose.

    Args:
        property_id: The Google Analytics property ID (number or 'properties/NUMBER').
        data_stream_id: The numeric web data stream ID.
    """
    request = admin_v1alpha.GetGlobalSiteTagRequest(
        name=f"{_data_stream_rn(property_id, data_stream_id)}/globalSiteTag"
    )

    def _sync_call():
        return proto_to_dict(
            create_admin_alpha_api_client().get_global_site_tag(request=request)
        )

    return await asyncio.to_thread(_sync_call)


async def search_change_history_events(
    account_id: int | str,
    property_id: Optional[int | str] = None,
    resource_types: Optional[List[str]] = None,
    actions: Optional[List[str]] = None,
    actor_email: Optional[str] = None,
    earliest_change_time: Optional[str] = None,
    latest_change_time: Optional[str] = None,
    page_size: int = 200,
) -> List[Dict[str, Any]]:
    """Searches the GA4 Change History (who changed what configuration, and when).

    Change History is scoped to an account. Filter by property, resource type,
    action, actor, and time window to pinpoint a specific change.

    Args:
        account_id: The numeric GA4 account ID (parent of the change history).
        property_id: Optional property to scope to (number or 'properties/NUMBER').
        resource_types: Optional list of resource types to filter, e.g.
          ["DATA_STREAM", "GOOGLE_ADS_LINK", "PROPERTY", "ATTRIBUTION_SETTINGS",
          "BIGQUERY_LINK", "ENHANCED_MEASUREMENT_SETTINGS"].
        actions: Optional list of actions: "CREATED", "UPDATED", "DELETED".
        actor_email: Optional email of the user who made the change.
        earliest_change_time: Optional ISO 8601 lower bound, e.g. "2026-07-04T00:00:00Z".
        latest_change_time: Optional ISO 8601 upper bound, e.g. "2026-07-06T00:00:00Z".
        page_size: Max events to return (default 200).
    """
    kwargs: Dict[str, Any] = {
        "account": _account_rn(account_id),
        "page_size": page_size,
    }
    if property_id is not None:
        kwargs["property"] = construct_property_rn(property_id)
    if resource_types:
        kwargs["resource_type"] = [
            admin_v1alpha.ChangeHistoryResourceType[r.strip().upper()]
            for r in resource_types
        ]
    if actions:
        kwargs["action"] = [
            admin_v1alpha.ActionType[a.strip().upper()] for a in actions
        ]
    if actor_email:
        kwargs["actor_email"] = actor_email
    if earliest_change_time:
        kwargs["earliest_change_time"] = _parse_time(earliest_change_time)
    if latest_change_time:
        kwargs["latest_change_time"] = _parse_time(latest_change_time)

    request = admin_v1alpha.SearchChangeHistoryEventsRequest(**kwargs)

    def _sync_call():
        pager = create_admin_alpha_api_client().search_change_history_events(
            request=request
        )
        return [proto_to_dict(page) for page in pager]

    return await asyncio.to_thread(_sync_call)
