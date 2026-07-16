"""Sync wrapper around the Supabase Storage client.

Sync (not async): the main callers are Celery tasks doing CPU-bound CV work
with no event loop of their own. An async API endpoint that needs this
should call it via FastAPI's run_in_threadpool so it doesn't block the loop.
"""

import structlog
from supabase import Client, create_client

from app.config import settings

log = structlog.get_logger()

_LIST_PAGE_SIZE = 100


class StorageClient:
    def __init__(self) -> None:
        client: Client = create_client(settings.supabase_url, settings.supabase_service_key)
        self._bucket = client.storage.from_(settings.storage_bucket)

    def create_signed_upload_url(self, key: str) -> dict[str, str]:
        """One-time URL + token the caller (browser) uploads directly to."""
        try:
            result = self._bucket.create_signed_upload_url(key)
        except Exception:
            log.exception("storage.signed_upload_url.failed", key=key)
            raise
        log.info("storage.signed_upload_url.created", key=key)
        return result

    def create_signed_read_url(self, key: str, expires_in: int) -> str:
        try:
            result = self._bucket.create_signed_url(key, expires_in)
        except Exception:
            log.exception("storage.signed_read_url.failed", key=key)
            raise
        log.info("storage.signed_read_url.created", key=key, expires_in=expires_in)
        return result["signedURL"]

    def create_signed_read_urls(self, keys: list[str], expires_in: int) -> dict[str, str]:
        """Batch-signs many read URLs in one request (e.g. a gallery page).

        Returns a key -> signed URL mapping instead of a list, since a
        gallery needs to pair each URL back up with its photo anyway.
        """
        if not keys:
            return {}
        try:
            results = self._bucket.create_signed_urls(keys, expires_in)
        except Exception:
            log.exception("storage.signed_read_urls.failed", count=len(keys))
            raise
        log.info("storage.signed_read_urls.created", count=len(keys), expires_in=expires_in)
        return {item["path"]: item["signedURL"] for item in results}

    def download_to_path(self, key: str, local_path: str) -> None:
        try:
            data = self._bucket.download(key)
            with open(local_path, "wb") as f:
                f.write(data)
        except Exception:
            log.exception("storage.object.download_failed", key=key)
            raise
        log.info("storage.object.downloaded", key=key, size_bytes=len(data))

    def delete_prefix(self, prefix: str) -> int:
        try:
            keys = self._list_keys(prefix)
            if keys:
                self._bucket.remove(keys)
        except Exception:
            log.exception("storage.prefix.delete_failed", prefix=prefix)
            raise
        log.info("storage.prefix.deleted", prefix=prefix, count=len(keys))
        return len(keys)

    def _list_keys(self, prefix: str) -> list[str]:
        """Recursively collects file keys under a prefix.

        list() only returns one folder level at a time, with subfolders
        coming back as entries with id=None, so nested prefixes (e.g. the
        per-photo face-crop folders) need a recursive walk.
        """
        keys: list[str] = []
        offset = 0
        while True:
            entries = self._bucket.list(prefix, {"limit": _LIST_PAGE_SIZE, "offset": offset})
            if not entries:
                break
            for entry in entries:
                entry_path = f"{prefix.rstrip('/')}/{entry['name']}"
                if entry.get("id") is None:
                    keys.extend(self._list_keys(entry_path))
                else:
                    keys.append(entry_path)
            if len(entries) < _LIST_PAGE_SIZE:
                break
            offset += _LIST_PAGE_SIZE
        return keys

    def object_exists(self, key: str) -> bool:
        try:
            return self._bucket.exists(key)
        except Exception:
            log.exception("storage.object.exists_check_failed", key=key)
            raise


storage_client = StorageClient()
