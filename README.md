# mcp-server-qdrant (fork)

Fork of [qdrant-ai/mcp-server-qdrant](https://github.com/qdrant-ai/mcp-server-qdrant) with three patches for querying pre-existing Qdrant collections created outside of this MCP server.

## Why this fork

The upstream package assumes it owns the Qdrant collection it queries. When connecting to a collection created by another pipeline (e.g. n8n), three incompatibilities arise:

| Issue | Upstream | This fork |
|---|---|---|
| **Vector name** | Derived as `fast-<model-name>` | Configurable via `QDRANT_VECTOR_NAME` env var |
| **Payload key** | Expects `document` field | Falls back to `text` if `document` is absent |
| **Port** | `AsyncQdrantClient` with `https://host` fails (qdrant-client 1.18.0 bug) | Requires explicit `:443` in URL |

## Changes from upstream

### `mcp_server_qdrant/settings.py`
Added `vector_name` field to `QdrantSettings`:
```python
vector_name: str | None = Field(default=None, validation_alias="QDRANT_VECTOR_NAME")
```

### `mcp_server_qdrant/qdrant.py`
- Added `vector_name_override: str | None = None` parameter to `QdrantConnector.__init__`
- `store()`, `search()`, `_ensure_collection_exists()` use `self._vector_name_override or self._embedding_provider.get_vector_name()`
- `search()` result mapping falls back: `payload.get("document") or payload.get("text")`

### `mcp_server_qdrant/mcp_server.py`
Passes `qdrant_settings.vector_name` as 7th argument to `QdrantConnector()`.

### `mcp_server_qdrant/embeddings/fastembed.py`
Reverted to clean upstream state (no env var hacks at the provider level).

## Installation

```bash
uv tool install --editable /path/to/this/fork
```

This creates an editable install — source changes are live immediately without reinstall.

## Configuration

```json
{
  "type": "stdio",
  "command": "/Users/<you>/.local/bin/mcp-server-qdrant",
  "args": [],
  "env": {
    "QDRANT_URL": "https://your-qdrant-host:443",
    "QDRANT_API_KEY": "<your-api-key>",
    "QDRANT_VECTOR_NAME": "dense",
    "EMBEDDING_MODEL": "BAAI/bge-base-en-v1.5",
    "COLLECTION_NAME": "your-collection"
  }
}
```

`QDRANT_VECTOR_NAME` must match the vector name used when the collection was created. For collections built with BGE models via n8n, this is typically `dense`.

## Keeping up with upstream

```bash
git fetch upstream
git rebase upstream/main
```

The fork is minimal by design — 3 targeted changes, easy to rebase.
