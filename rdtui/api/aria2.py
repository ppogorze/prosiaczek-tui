"""aria2 RPC client."""

from typing import Any, Dict, List, Optional

import httpx


class Aria2RPC:
    """Client for interacting with aria2 via JSON-RPC."""

    def __init__(self, url: str, secret: str | None = None):
        """Initialize the aria2 RPC client.

        Args:
            url: aria2 RPC URL (e.g., http://127.0.0.1:6800/jsonrpc)
            secret: Optional RPC secret token
        """
        self.url = url
        self.secret = secret or ""
        self._id = 0
        self._client = httpx.AsyncClient(timeout=15.0)

    def _next_id(self) -> int:
        """Get the next RPC call ID."""
        self._id += 1
        return self._id

    def _auth_token(self) -> List[Any]:
        """Get the authentication token for RPC calls."""
        return [f"token:{self.secret}"] if self.secret else []

    async def _call(self, method: str, params: List[Any] | None = None) -> Any:
        """Make an RPC call to aria2.

        Args:
            method: RPC method name
            params: Method parameters

        Returns:
            RPC result

        Raises:
            RuntimeError: If the RPC call returns an error
        """
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": (self._auth_token() + (params or [])),
        }
        r = await self._client.post(self.url, json=payload)
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise RuntimeError(data["error"])
        return data.get("result")

    async def add_uri(
        self, uris: List[str], out: Optional[str] = None, dir: Optional[str] = None
    ) -> str:
        """Add a download by URI.

        Args:
            uris: List of URIs to download
            out: Output filename
            dir: Download directory

        Returns:
            GID (download identifier)
        """
        options: Dict[str, Any] = {}
        if out:
            options["out"] = out
        if dir:
            options["dir"] = dir
        gid = await self._call("aria2.addUri", [uris, options])
        return gid

    async def tell_status(self, gid: str) -> Dict[str, Any]:
        """Get status of a download.

        Args:
            gid: Download GID

        Returns:
            Download status information
        """
        keys = [
            "status",
            "totalLength",
            "completedLength",
            "downloadSpeed",
            "errorMessage",
            "files",
        ]
        return await self._call("aria2.tellStatus", [gid, keys])

    async def tell_active(self) -> List[Dict[str, Any]]:
        """Get list of active downloads."""
        keys = [
            "gid",
            "status",
            "totalLength",
            "completedLength",
            "downloadSpeed",
            "files",
        ]
        return await self._call("aria2.tellActive", [keys])

    async def tell_waiting(
        self, offset: int = 0, num: int = 100
    ) -> List[Dict[str, Any]]:
        """Get list of waiting downloads.

        Args:
            offset: Offset in the list
            num: Number of items to retrieve
        """
        keys = [
            "gid",
            "status",
            "totalLength",
            "completedLength",
            "downloadSpeed",
            "files",
        ]
        return await self._call("aria2.tellWaiting", [offset, num, keys])

    async def tell_stopped(
        self, offset: int = 0, num: int = 100
    ) -> List[Dict[str, Any]]:
        """Get list of stopped downloads.

        Args:
            offset: Offset in the list
            num: Number of items to retrieve
        """
        keys = [
            "gid",
            "status",
            "totalLength",
            "completedLength",
            "downloadSpeed",
            "files",
            "errorMessage",
        ]
        return await self._call("aria2.tellStopped", [offset, num, keys])

    async def pause(self, gid: str) -> Any:
        """Pause a download.

        Args:
            gid: Download GID
        """
        return await self._call("aria2.pause", [gid])

    async def remove(self, gid: str) -> Any:
        """Remove a download.

        Args:
            gid: Download GID
        """
        # Try remove running task; if already stopped, remove result
        try:
            return await self._call("aria2.remove", [gid])
        except Exception:
            try:
                return await self._call("aria2.removeDownloadResult", [gid])
            except Exception:
                raise

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

