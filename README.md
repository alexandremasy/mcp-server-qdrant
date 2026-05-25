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

## Installation & registration in Claude Code

### Step 1 — Install as an editable uv tool

```bash
uv tool install --editable /path/to/this/fork
```

This installs `mcp-server-qdrant` as a global command. Because it's editable, any change to the source is live immediately — no reinstall needed.

### Step 2 — Find the installed binary

```bash
# macOS / Linux
which mcp-server-qdrant

# Windows
where mcp-server-qdrant
# → C:\Users\<you>\.local\bin\mcp-server-qdrant.exe
```

### Step 3 — Register in Claude Code

```bash
claude mcp add \
  -e QDRANT_URL=https://your-qdrant-host:443 \
  -e "QDRANT_API_KEY=<your-api-key>" \
  -e COLLECTION_NAME=library \
  -e QDRANT_VECTOR_NAME=dense \
  -e "EMBEDDING_MODEL=nomic-ai/nomic-embed-text-v1.5" \
  --scope user \
  qdrant -- /full/path/to/mcp-server-qdrant
```

> **Use the full path** — Claude Code may not inherit your shell PATH.

Verify: `claude mcp get qdrant` — should show `Status: ✓ Connected`.

## Configuration reference

| Variable | Required | Description |
|---|---|---|
| `QDRANT_URL` | ✓ | Include `:443` for HTTPS (qdrant-client 1.18+ bug with bare hostname) |
| `QDRANT_API_KEY` | if auth | Qdrant API key |
| `COLLECTION_NAME` | ✓ | Target collection |
| `QDRANT_VECTOR_NAME` | ✓ | Must match the named vector in the collection (e.g. `dense`) |
| `EMBEDDING_MODEL` | ✓ | FastEmbed model — use `nomic-ai/nomic-embed-text-v1.5` for collections built with Ollama `nomic-embed-text` |
| `QDRANT_READ_ONLY` | — | Set `true` to disable the `qdrant-store` tool |

`QDRANT_VECTOR_NAME` must match the vector name used when the collection was created. For the `reports-pipeline` library collection, this is `dense`.

## Keeping up with upstream

```bash
git fetch upstream
git rebase upstream/main
```

The fork is minimal by design — 3 targeted changes, easy to rebase.
