"""Lightweight ``requests`` compatibility shim built on ``urllib``."""

from __future__ import annotations

import json
import socket
import types
from dataclasses import dataclass
from typing import Any, Dict, Iterator, Mapping, Optional
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

__all__ = [
    "RequestException",
    "Timeout",
    "HTTPError",
    "Response",
    "get",
    "head",
    "post",
    "Session",
    "exceptions",
]


class RequestException(Exception):
    """Base exception raised for network errors."""


class Timeout(RequestException):
    """Raised when a request times out."""


class HTTPError(RequestException):
    """Raised for non-success HTTP status codes."""

    def __init__(self, status: int, message: str, url: str) -> None:
        super().__init__(f"HTTP {status} for url {url}: {message}")
        self.status = status
        self.url = url
        self.message = message


@dataclass
class _PreparedRequest:
    url: str
    data: Optional[bytes]
    headers: Dict[str, str]
    method: str


class Response:
    """Subset of ``requests.Response`` used by the Tenos project."""

    def __init__(
        self,
        *,
        url: str,
        status: int,
        reason: str,
        headers: Mapping[str, str],
        body: Optional[bytes],
        stream_handle: Optional[urllib_request.addinfourl],
    ) -> None:
        self.url = url
        self.status_code = status
        self.reason = reason
        self.headers: Dict[str, str] = {k: v for k, v in headers.items()}
        self._body = body
        self._stream = stream_handle

    # ------------------------------------------------------------------
    def raise_for_status(self) -> None:
        if 400 <= self.status_code:
            raise HTTPError(self.status_code, self.reason or "", self.url)

    # ------------------------------------------------------------------
    @property
    def content(self) -> bytes:
        if self._body is None and self._stream is not None:
            self._body = self._stream.read()
            self.close()
        return self._body or b""

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.content.decode("utf-8"))

    # ------------------------------------------------------------------
    def iter_content(self, chunk_size: int = 8192) -> Iterator[bytes]:
        if chunk_size <= 0:
            chunk_size = 8192
        if self._stream is None:
            data = self.content
            for idx in range(0, len(data), chunk_size):
                yield data[idx : idx + chunk_size]
            return

        try:
            while True:
                chunk = self._stream.read(chunk_size)
                if not chunk:
                    break
                yield chunk
        finally:
            self.close()

    # ------------------------------------------------------------------
    def close(self) -> None:
        if self._stream is not None:
            try:
                self._stream.close()
            finally:
                self._stream = None

    # Context manager support -------------------------------------------------
    def __enter__(self) -> "Response":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
        return False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _prepare_url(url: str, params: Optional[Mapping[str, Any]]) -> str:
    if not params:
        return url
    query = urllib_parse.urlencode({k: v for k, v in params.items() if v is not None})
    if not query:
        return url
    separator = "&" if urllib_parse.urlparse(url).query else "?"
    return f"{url}{separator}{query}"


def _merge_headers(base: Optional[Mapping[str, str]], extra: Optional[Mapping[str, str]]) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    if base:
        headers.update(base)
    if extra:
        headers.update({k: v for k, v in extra.items() if v is not None})
    return headers


def _prepare_request(
    method: str,
    url: str,
    *,
    params: Optional[Mapping[str, Any]] = None,
    data: Any = None,
    json_data: Any = None,
    headers: Optional[Mapping[str, str]] = None,
    session_headers: Optional[Mapping[str, str]] = None,
) -> _PreparedRequest:
    final_url = _prepare_url(url, params)
    body: Optional[bytes] = None
    final_headers = _merge_headers(session_headers, headers)

    if json_data is not None:
        body = json.dumps(json_data).encode("utf-8")
        final_headers.setdefault("Content-Type", "application/json")
    elif data is not None:
        if isinstance(data, (bytes, bytearray)):
            body = bytes(data)
        else:
            body = str(data).encode("utf-8")

    final_headers.setdefault("User-Agent", "TenosAI-HTTP/1.0")

    return _PreparedRequest(final_url, body, final_headers, method.upper())


def _execute_request(
    prepared: _PreparedRequest,
    *,
    timeout: Optional[float],
    stream: bool,
) -> Response:
    request = urllib_request.Request(
        prepared.url,
        data=prepared.data,
        headers=prepared.headers,
        method=prepared.method,
    )

    try:
        response = urllib_request.urlopen(request, timeout=timeout)
    except socket.timeout as exc:
        raise Timeout(str(exc)) from exc
    except urllib_error.HTTPError as exc:
        raise HTTPError(exc.code, exc.reason, prepared.url) from exc
    except urllib_error.URLError as exc:
        raise RequestException(str(exc.reason)) from exc

    if stream:
        return Response(
            url=prepared.url,
            status=response.status,
            reason=getattr(response, "reason", ""),
            headers=response.headers,
            body=None,
            stream_handle=response,
        )

    body = response.read()
    headers = response.headers
    reason = getattr(response, "reason", "")
    response.close()
    return Response(
        url=prepared.url,
        status=response.status,
        reason=reason,
        headers=headers,
        body=body,
        stream_handle=None,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def request(
    method: str,
    url: str,
    *,
    params: Optional[Mapping[str, Any]] = None,
    data: Any = None,
    json: Any = None,
    headers: Optional[Mapping[str, str]] = None,
    timeout: Optional[float] = None,
    stream: bool = False,
    allow_redirects: bool = True,  # present for compatibility
    session_headers: Optional[Mapping[str, str]] = None,
) -> Response:
    prepared = _prepare_request(
        method,
        url,
        params=params,
        data=data,
        json_data=json,
        headers=headers,
        session_headers=session_headers,
    )
    return _execute_request(prepared, timeout=timeout, stream=stream)


def get(
    url: str,
    *,
    params: Optional[Mapping[str, Any]] = None,
    headers: Optional[Mapping[str, str]] = None,
    timeout: Optional[float] = None,
    stream: bool = False,
    allow_redirects: bool = True,
) -> Response:
    return request(
        "GET",
        url,
        params=params,
        headers=headers,
        timeout=timeout,
        stream=stream,
        allow_redirects=allow_redirects,
    )


def head(
    url: str,
    *,
    headers: Optional[Mapping[str, str]] = None,
    timeout: Optional[float] = None,
    allow_redirects: bool = True,
) -> Response:
    return request("HEAD", url, headers=headers, timeout=timeout, allow_redirects=allow_redirects)


def post(
    url: str,
    *,
    data: Any = None,
    json: Any = None,
    headers: Optional[Mapping[str, str]] = None,
    timeout: Optional[float] = None,
    stream: bool = False,
    allow_redirects: bool = True,
) -> Response:
    return request(
        "POST",
        url,
        data=data,
        json=json,
        headers=headers,
        timeout=timeout,
        stream=stream,
        allow_redirects=allow_redirects,
    )


class Session:
    """Lightweight session with persistent headers."""

    def __init__(self) -> None:
        self.headers: Dict[str, str] = {}

    def get(
        self,
        url: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        stream: bool = False,
        allow_redirects: bool = True,
    ) -> Response:
        return request(
            "GET",
            url,
            params=params,
            headers=headers,
            timeout=timeout,
            stream=stream,
            allow_redirects=allow_redirects,
            session_headers=self.headers,
        )

    def post(
        self,
        url: str,
        *,
        data: Any = None,
        json: Any = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        stream: bool = False,
        allow_redirects: bool = True,
    ) -> Response:
        return request(
            "POST",
            url,
            data=data,
            json=json,
            headers=headers,
            timeout=timeout,
            stream=stream,
            allow_redirects=allow_redirects,
            session_headers=self.headers,
        )

    def close(self) -> None:
        """Included for compatibility with ``requests.Session``."""
        self.headers.clear()


exceptions = types.SimpleNamespace(
    RequestException=RequestException,
    Timeout=Timeout,
    HTTPError=HTTPError,
)

