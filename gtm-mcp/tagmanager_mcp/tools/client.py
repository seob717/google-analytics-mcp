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

"""Client initialization for the Google Tag Manager API (v2)."""

import contextlib
import subprocess
import threading
from importlib import metadata
from unittest.mock import patch

import google.auth
from googleapiclient.discovery import build

# Scopes for reading and editing containers, plus creating/publishing versions.
# Deleting workspace entities (tags/triggers/variables) is covered by
# edit.containers; only whole-container deletion would need delete.containers,
# which this server does not expose.
SCOPES = [
    "https://www.googleapis.com/auth/tagmanager.readonly",
    "https://www.googleapis.com/auth/tagmanager.edit.containers",
    "https://www.googleapis.com/auth/tagmanager.edit.containerversions",
    "https://www.googleapis.com/auth/tagmanager.publish",
]


def _version() -> str:
    try:
        return metadata.version("tagmanager-mcp")
    except Exception:
        return "unknown"


_lock = threading.Lock()
_service = None


@contextlib.contextmanager
def _prevent_stdio_inheritance():
    """Stops child processes (e.g. gcloud) from inheriting stdio handles.

    Mirrors the analytics-mcp fix for a Windows deadlock where
    google.auth.default() spawns gcloud without redirecting stdin.
    """
    original_popen = subprocess.Popen

    def safe_popen(*args, **kwargs):
        if kwargs.get("stdin") is None:
            kwargs["stdin"] = subprocess.DEVNULL
        return original_popen(*args, **kwargs)

    with patch("subprocess.Popen", new=safe_popen):
        yield


def tagmanager():
    """Returns a cached Google Tag Manager API (v2) service, built lazily."""
    global _service
    with _lock:
        if _service is None:
            with _prevent_stdio_inheritance():
                credentials, _ = google.auth.default(scopes=SCOPES)
            _service = build(
                "tagmanager",
                "v2",
                credentials=credentials,
                cache_discovery=False,
            )
        return _service
