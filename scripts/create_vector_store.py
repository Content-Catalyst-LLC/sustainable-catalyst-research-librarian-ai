#!/usr/bin/env python3
"""Create or update the Sustainable Catalyst Research Librarian OpenAI vector store.

Usage:
  export OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
  python3 scripts/create_vector_store.py knowledge/sustainable-catalyst-knowledge-seed.md

Optional:
  export OPENAI_VECTOR_STORE_ID="vs_..."   # add files to an existing vector store
  export VECTOR_STORE_NAME="Sustainable Catalyst Research Librarian Knowledge Base"

Dependencies:
  python3 -m pip install requests
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

try:
    import requests
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Missing dependency: requests. Install with: python3 -m pip install requests") from exc

API_BASE = "https://api.openai.com/v1"
DEFAULT_NAME = "Sustainable Catalyst Research Librarian Knowledge Base"


def headers(api_key: str, json_mode: bool = True) -> Dict[str, str]:
    base = {"Authorization": f"Bearer {api_key}"}
    if json_mode:
        base["Content-Type"] = "application/json"
    return base


def request_json(method: str, url: str, api_key: str, **kwargs: Any) -> Dict[str, Any]:
    response = requests.request(method, url, headers=headers(api_key), timeout=60, **kwargs)
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text}
    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"{method} {url} failed: HTTP {response.status_code}: {json.dumps(payload, indent=2)}")
    return payload


def create_vector_store(api_key: str, name: str) -> str:
    payload = request_json(
        "POST",
        f"{API_BASE}/vector_stores",
        api_key,
        data=json.dumps({"name": name}),
    )
    vector_store_id = payload.get("id")
    if not vector_store_id:
        raise RuntimeError(f"Vector store creation did not return an id: {payload}")
    return vector_store_id


def upload_file(api_key: str, path: Path) -> str:
    with path.open("rb") as file_obj:
        response = requests.post(
            f"{API_BASE}/files",
            headers=headers(api_key, json_mode=False),
            files={"file": (path.name, file_obj)},
            data={"purpose": "assistants"},
            timeout=120,
        )
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text}
    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"File upload failed for {path}: HTTP {response.status_code}: {json.dumps(payload, indent=2)}")
    file_id = payload.get("id")
    if not file_id:
        raise RuntimeError(f"File upload did not return an id: {payload}")
    return file_id


def add_file_to_vector_store(api_key: str, vector_store_id: str, file_id: str) -> str:
    payload = request_json(
        "POST",
        f"{API_BASE}/vector_stores/{vector_store_id}/files",
        api_key,
        data=json.dumps({"file_id": file_id}),
    )
    vector_store_file_id = payload.get("id") or file_id
    return vector_store_file_id


def get_vector_store_file(api_key: str, vector_store_id: str, vector_store_file_id: str) -> Dict[str, Any]:
    return request_json(
        "GET",
        f"{API_BASE}/vector_stores/{vector_store_id}/files/{vector_store_file_id}",
        api_key,
    )


def wait_until_ready(api_key: str, vector_store_id: str, vector_store_file_id: str, timeout_seconds: int = 300) -> Dict[str, Any]:
    start = time.time()
    last_payload: Optional[Dict[str, Any]] = None
    while time.time() - start < timeout_seconds:
        payload = get_vector_store_file(api_key, vector_store_id, vector_store_file_id)
        last_payload = payload
        status = payload.get("status")
        print(f"  status for {vector_store_file_id}: {status}")
        if status == "completed":
            return payload
        if status in {"failed", "cancelled"}:
            raise RuntimeError(f"Vector store file processing ended with status {status}: {json.dumps(payload, indent=2)}")
        time.sleep(5)
    raise TimeoutError(f"Timed out waiting for vector store file to finish. Last response: {json.dumps(last_payload, indent=2)}")


def default_seed_path() -> Path:
    return Path(__file__).resolve().parents[1] / "knowledge" / "sustainable-catalyst-knowledge-seed.md"


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or update the Sustainable Catalyst OpenAI vector store.")
    parser.add_argument("files", nargs="*", help="Files to upload. Defaults to the bundled Sustainable Catalyst knowledge seed markdown.")
    parser.add_argument("--name", default=os.getenv("VECTOR_STORE_NAME", DEFAULT_NAME), help="Vector store name when creating a new store.")
    parser.add_argument("--vector-store-id", default=os.getenv("OPENAI_VECTOR_STORE_ID", ""), help="Existing vector store id. If omitted, a new vector store is created.")
    parser.add_argument("--no-wait", action="store_true", help="Do not poll until indexing is complete.")
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] = sys.argv[1:]) -> int:
    args = parse_args(argv)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("OPENAI_API_KEY is required.", file=sys.stderr)
        return 2

    paths = [Path(p).expanduser().resolve() for p in args.files] if args.files else [default_seed_path()]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        print("Missing file(s):\n" + "\n".join(missing), file=sys.stderr)
        return 2

    vector_store_id = args.vector_store_id.strip()
    if vector_store_id:
        print(f"Using existing vector store: {vector_store_id}")
    else:
        vector_store_id = create_vector_store(api_key, args.name)
        print(f"Created vector store: {vector_store_id}")

    added = []
    for path in paths:
        print(f"Uploading {path.name}...")
        file_id = upload_file(api_key, path)
        print(f"  file id: {file_id}")
        vector_store_file_id = add_file_to_vector_store(api_key, vector_store_id, file_id)
        print(f"  vector store file id: {vector_store_file_id}")
        if not args.no_wait:
            wait_until_ready(api_key, vector_store_id, vector_store_file_id)
        added.append({"path": str(path), "file_id": file_id, "vector_store_file_id": vector_store_file_id})

    print("\nDone.")
    print(json.dumps({"vector_store_id": vector_store_id, "files": added}, indent=2))
    print("\nCopy the vector_store_id into WordPress → Settings → Research Librarian AI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
