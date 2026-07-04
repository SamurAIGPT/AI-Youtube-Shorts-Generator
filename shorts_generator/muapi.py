"""Thin MuAPI client: submit a job, poll until it finishes, return the result."""
import time
from typing import Any, Dict, Optional

import requests

from .config import (
    MUAPI_BASE_URL,
    POLL_INTERVAL_SECONDS,
    POLL_TIMEOUT_SECONDS,
    require_api_key,
)


class MuAPIError(RuntimeError):
    pass


def _headers() -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "x-api-key": require_api_key(),
    }


def submit(endpoint: str, payload: Dict[str, Any], retries: int = 3) -> str:
    """POST to /api/v1/{endpoint} and return the request_id; retry transient errors."""
    url = f"{MUAPI_BASE_URL}/{endpoint.lstrip('/')}"
    last_err: Optional[Exception] = None
    for _ in range(retries):
        try:
            resp = requests.post(url, json=payload, headers=_headers(), timeout=120)
            if resp.status_code >= 400:
                raise MuAPIError(f"{endpoint} submit failed [{resp.status_code}]: {resp.text}")
            data = resp.json()
            request_id = data.get("request_id") or data.get("id")
            if not request_id:
                raise MuAPIError(f"{endpoint} response had no request_id: {data}")
            return str(request_id)
        except (requests.Timeout, requests.ConnectionError) as e:
            last_err = e
            time.sleep(2)
    raise MuAPIError(f"{endpoint} submit failed after {retries} retries: {last_err}")


def fetch_result(request_id: str, retries: int = 3) -> Dict[str, Any]:
    """GET the latest result for a request_id; retry on transient timeouts."""
    url = f"{MUAPI_BASE_URL}/predictions/{request_id}/result"
    last_err: Optional[Exception] = None
    for _ in range(retries):
        try:
            resp = requests.get(url, headers=_headers(), timeout=90)
            if resp.status_code >= 400:
                raise MuAPIError(f"poll failed [{resp.status_code}]: {resp.text}")
            return resp.json()
        except (requests.Timeout, requests.ConnectionError) as e:
            last_err = e
            time.sleep(2)
    raise MuAPIError(f"poll failed after {retries} retries: {last_err}")


def poll(
    request_id: str,
    interval: float = POLL_INTERVAL_SECONDS,
    timeout: float = POLL_TIMEOUT_SECONDS,
    label: Optional[str] = None,
) -> Dict[str, Any]:
    """Block until the prediction is done; return the final payload."""
    deadline = time.time() + timeout
    last_status = None
    while time.time() < deadline:
        data = fetch_result(request_id)
        status = (data.get("status") or "").lower()
        if status and status != last_status:
            print(f"[muapi] {label or request_id}: {status}", flush=True)
            last_status = status

        if status in ("completed", "succeeded", "success"):
            return data
        if status in ("failed", "error"):
            raise MuAPIError(f"{label or request_id} failed: {data}")

        time.sleep(interval)

    raise MuAPIError(f"{label or request_id} timed out after {timeout}s")


def run(
    endpoint: str,
    payload: Dict[str, Any],
    label: Optional[str] = None,
    interval: float = POLL_INTERVAL_SECONDS,
    timeout: float = POLL_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """Submit then poll. Returns the final result payload."""
    request_id = submit(endpoint, payload)
    return poll(request_id, interval=interval, timeout=timeout, label=label or endpoint)
