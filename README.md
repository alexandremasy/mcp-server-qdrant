# mcp-server-qdrant (fork)

Fork of [qdrant/mcp-server-qdrant](https://github.com/qdrant/mcp-server-qdrant), patched to query
pre-existing Qdrant collections created outside of this MCP server, and to embed through a remote
Ollama instance instead of an in-process model.

## Why this fork

The upstream package assumes it owns the Qdrant collection it queries, and it embeds with FastEmbed
(a model downloaded and run inside the server process). Connecting to a collection built by another
pipeline (e.g. n8n) breaks on four points:

| Issue | Upstream | This fork |
|---|---|---|
| **Vector name** | Derived as `fast-<model-name>` | Configurable via `QDRANT_VECTOR_NAME` |
| **Payload key** | Expects a `document` field | Falls back to `text` if `document` is absent |
| **Embeddings** | FastEmbed only, in-process | `EMBEDDING_PROVIDER=ollama` calls a remote Ollama; FastEmbed is now an optional extra |
| **Port** | `AsyncQdrantClient` with `https://host` fails (qdrant-client 1.18.0 bug) | Requires an explicit `:443` in the URL |

It also adds a `qdrant-delete` tool, which upstream does not have.

## Changes from upstream

### `mcp_server_qdrant/settings.py`
- `QdrantSettings.vector_name` — `Field(default=None, validation_alias="QDRANT_VECTOR_NAME")`
- `EmbeddingProviderSettings` — `provider_type` (`EMBEDDING_PROVIDER`), `ollama_url` (`OLLAMA_URL`),
  `ollama_vector_size` (`OLLAMA_VECTOR_SIZE`)

### `mcp_server_qdrant/qdrant.py`
- `QdrantConnector.__init__` takes `vector_name_override: str | None = None`
- `store()`, `search()`, `_ensure_collection_exists()` use `self._vector_name_override or self._embedding_provider.get_vector_name()`
- `search()` result mapping falls back: `payload.get("document") or payload.get("text")`
- Added `delete()` — by point IDs, by payload filter, or clear-all

### `mcp_server_qdrant/embeddings/ollama.py` (new)
`OllamaProvider` — POSTs to `{OLLAMA_URL}/api/embed`, no model loaded in-process. It does **not**
contact Ollama at startup, so the server starts fine even when Ollama is unreachable (see the
verification note below).

### `mcp_server_qdrant/mcp_server.py`
- Passes `qdrant_settings.vector_name` as 7th argument to `QdrantConnector()`
- Registers the `qdrant-delete` tool (skipped when `QDRANT_READ_ONLY=true`)

### `pyproject.toml`
FastEmbed moved out of `dependencies` into `[project.optional-dependencies] fastembed`.

## Tools exposed

| Tool | Available when |
|---|---|
| `qdrant-find` | always |
| `qdrant-store` | `QDRANT_READ_ONLY` is not `true` |
| `qdrant-delete` | `QDRANT_READ_ONLY` is not `true` — takes `point_ids`, `payload_filter`, or `clear_all` (exactly one) |

## Installation & registration in Claude Code

### Step 1 — Install as an editable uv tool

```bash
uv tool install --editable /path/to/this/fork
```

Editable means any change to the source is live immediately — no reinstall. This installs the
Ollama path only. For FastEmbed instead:

```bash
uv tool install --editable '/path/to/this/fork[fastembed]'
```

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
claude mcp add --scope user qdrant \
  -e QDRANT_URL=https://your-qdrant-host:443 \
  -e "QDRANT_API_KEY=<your-api-key>" \
  -e COLLECTION_NAME=library \
  -e QDRANT_VECTOR_NAME=dense \
  -e EMBEDDING_PROVIDER=ollama \
  -e OLLAMA_URL=https://your-ollama-host \
  -e EMBEDDING_MODEL=nomic-embed-text \
  -e OLLAMA_VECTOR_SIZE=768 \
  -- /full/path/to/mcp-server-qdrant
```

> **Use the full path** — Claude Code may not inherit your shell PATH.

### Step 4 — Verify

`claude mcp get qdrant` shows `Status: ✓ Connected`, but that only proves the process starts —
the Ollama provider is lazy, so a dead embedding host still reports green. Confirm the real chain
with an actual `qdrant-find` call, or out of band:

```bash
curl -s "$OLLAMA_URL/api/embed" -H 'Content-Type: application/json' \
  -d '{"model":"nomic-embed-text","input":["test"]}' | head -c 120
```

## Configuration reference

| Variable | Required | Description |
|---|---|---|
| `QDRANT_URL` | ✓ | Include `:443` for HTTPS (qdrant-client 1.18+ bug with a bare hostname) |
| `QDRANT_API_KEY` | if auth | Qdrant API key |
| `COLLECTION_NAME` | ✓ | Target collection |
| `QDRANT_VECTOR_NAME` | ✓ | Must match the named vector in the collection (e.g. `dense`) |
| `EMBEDDING_PROVIDER` | ✓ | `ollama` or `fastembed` (default: `fastembed`, which is not installed unless you asked for the extra) |
| `EMBEDDING_MODEL` | ✓ | `nomic-embed-text` for Ollama; `nomic-ai/nomic-embed-text-v1.5` for FastEmbed |
| `OLLAMA_URL` | if ollama | Ollama base URL (default: `http://localhost:11434`) |
| `OLLAMA_VECTOR_SIZE` | if ollama | Embedding dimension, must match the collection (default: `768`) |
| `QDRANT_SEARCH_LIMIT` | — | Max results per search (default: `10`) |
| `QDRANT_READ_ONLY` | — | `true` disables `qdrant-store` and `qdrant-delete` |
| `QDRANT_ALLOW_ARBITRARY_FILTER` | — | `true` exposes a raw Qdrant filter argument on `qdrant-find` |

`QDRANT_VECTOR_NAME` and `OLLAMA_VECTOR_SIZE` must match how the collection was created. For the
`reports-pipeline` library collection: `dense`, 768 dimensions, cosine.

The embedding model must be the one the collection was indexed with — Ollama `nomic-embed-text`
and FastEmbed `nomic-ai/nomic-embed-text-v1.5` are the same underlying model, so either can query
a collection built with the other.

## Keeping up with upstream

```bash
git remote add upstream https://github.com/qdrant/mcp-server-qdrant.git   # once
git fetch upstream
git rebase upstream/main
```

The fork stays deliberately small — targeted patches plus one new provider, easy to rebase.
