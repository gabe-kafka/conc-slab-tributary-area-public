"""Vercel Blob REST API helpers for Python (no JS SDK needed)."""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.parse
from typing import Optional

BLOB_API_URL = "https://vercel.com/api/blob"
BLOB_API_VERSION = "12"


def _token() -> str:
    return os.environ["BLOB_READ_WRITE_TOKEN"]


def _base_headers(token: Optional[str] = None) -> dict:
    return {
        "Authorization": f"Bearer {token or _token()}",
        "x-api-version": BLOB_API_VERSION,
    }


def blob_put(
    pathname: str,
    data: bytes,
    *,
    access: str = "public",
    content_type: str = "application/octet-stream",
    add_random_suffix: bool = True,
) -> dict:
    """Upload bytes to Vercel Blob. Returns dict with url, downloadUrl, pathname."""
    params = urllib.parse.urlencode({"pathname": pathname})
    url = f"{BLOB_API_URL}/?{params}"
    headers = {
        **_base_headers(),
        "x-vercel-blob-access": access,
        "x-content-type": content_type,
        "x-add-random-suffix": "1" if add_random_suffix else "0",
    }
    req = urllib.request.Request(url, data=data, method="PUT", headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def blob_delete(urls: list[str] | str) -> None:
    """Delete one or more blobs by URL."""
    if isinstance(urls, str):
        urls = [urls]
    url = f"{BLOB_API_URL}/delete"
    headers = {
        **_base_headers(),
        "Content-Type": "application/json",
    }
    body = json.dumps({"urls": urls}).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers=headers)
    with urllib.request.urlopen(req) as resp:
        resp.read()


def blob_download(blob_url: str) -> bytes:
    """Download blob content. Uses auth header for private blobs."""
    headers = {"Authorization": f"Bearer {_token()}"}
    req = urllib.request.Request(blob_url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return resp.read()
