"""Real-Debrid API client."""

from typing import Any, Dict, List

import httpx

API_BASE = "https://api.real-debrid.com/rest/1.0"


class RDClient:
    """Client for interacting with the Real-Debrid API."""

    def __init__(self, token: str):
        """Initialize the Real-Debrid client.

        Args:
            token: Real-Debrid API token
        """
        self.token = token
        self._client = httpx.AsyncClient(
            base_url=API_BASE,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def _get(self, path: str, **kwargs):
        """Make a GET request to the API."""
        r = await self._client.get(path, **kwargs)
        r.raise_for_status()
        return r.json()

    async def _post(self, path: str, data: Dict[str, Any] | None = None):
        """Make a POST request to the API."""
        r = await self._client.post(path, data=data)
        r.raise_for_status()
        try:
            return r.json()
        except Exception:
            return {}

    async def _delete(self, path: str):
        """Make a DELETE request to the API."""
        r = await self._client.delete(path)
        # RD returns 204 No Content on success for delete endpoints
        if r.status_code not in (200, 204):
            r.raise_for_status()
        try:
            return r.json()
        except Exception:
            return {}

    # --- API Endpoints ---

    async def user(self) -> Dict[str, Any]:
        """Get user information."""
        return await self._get("/user")

    async def torrents(self) -> List[Dict[str, Any]]:
        """Get list of user's torrents."""
        return await self._get("/torrents")

    async def torrent_info(self, tid: str) -> Dict[str, Any]:
        """Get detailed information about a torrent.

        Args:
            tid: Torrent ID
        """
        return await self._get(f"/torrents/info/{tid}")

    async def add_magnet(self, magnet: str) -> Dict[str, Any]:
        """Add a magnet link.

        Args:
            magnet: Magnet URI
        """
        return await self._post("/torrents/addMagnet", data={"magnet": magnet})

    async def select_all(self, tid: str) -> Dict[str, Any]:
        """Select all files in a torrent.

        Args:
            tid: Torrent ID
        """
        return await self._post(f"/torrents/selectFiles/{tid}", data={"files": "all"})

    async def delete_torrent(self, tid: str) -> Dict[str, Any]:
        """Delete a torrent.

        Args:
            tid: Torrent ID
        """
        return await self._delete(f"/torrents/delete/{tid}")

    async def unrestrict_link(self, link: str) -> Dict[str, Any]:
        """Unrestrict a link (convert to direct download).

        Args:
            link: URL to unrestrict
        """
        return await self._post("/unrestrict/link", data={"link": link})

    async def add_torrent_bytes(
        self, data: bytes, filename: str = "upload.torrent"
    ) -> Dict[str, Any]:
        """Upload a .torrent file.

        Args:
            data: Torrent file bytes
            filename: Filename for the upload
        """
        files = {"file": (filename, data, "application/x-bittorrent")}
        r = await self._client.post("/torrents/addTorrent", files=files)
        r.raise_for_status()
        try:
            return r.json()
        except Exception:
            return {}

    async def add_torrent_from_url(self, url: str) -> Dict[str, Any]:
        """Download a .torrent file from URL and upload to Real-Debrid.

        Args:
            url: URL to .torrent file
        """
        resp = await self._client.get(url)
        resp.raise_for_status()
        fname = url.split("/")[-1] or "upload.torrent"
        return await self.add_torrent_bytes(resp.content, fname)

