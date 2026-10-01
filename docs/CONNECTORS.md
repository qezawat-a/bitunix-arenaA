# Connectors and generation

Upload configuration JSON to Telegram or place it in the configured workspace. Do not embed keys in JSON/URLs.
`auth_env` references a **locally exported** environment variable (e.g. in the process/container env).
`.env` settings fields are not automatically exported as arbitrary connector env variables.

MCP streamable HTTP:

```json
{"name":"notes","url":"https://your-mcp.example/mcp","auth_env":"NOTES_TOKEN","protocol":"mcp"}
```

Then `/mcp add uploads/notes.json`, inspect `/approval <id>`, approve. Initialization uses MCP JSON-RPC,
retains session/protocol headers, supports JSON/SSE responses and paginated tools/list. Stdio/legacy SSE transports are not supported.
Remote tool descriptions/results are untrusted; tool calls always require approval, regardless of read-only annotations.

Generic app HTTP connector:

```json
{"name":"video","url":"https://your-adapter.example/jobs","auth_env":"VIDEO_API_TOKEN","protocol":"http"}
```

`/app_connector add uploads/video.json`. Set `VIDEO_CONNECTOR=video` locally.
The video adapter must implement POST JSON `{"operation":"generate_video","prompt":"..."}` and return a JSON
job/result. It is responsible for its own provider model ID, rendering/polling/download contract. The bot reports the real returned
result, not a fake completed video. Other app connectors accept an approved JSON `payload` at their configured URL.

Search adapter contract:

- Configure `SEARCH_URL` and optional `SEARCH_API_KEY` locally.
- POST `{"query":"...","limit":8}`.
- Return `{"results":[{"title":"...","url":"https://...","snippet":"..."}]}`.
- `/deepsearch` requests query-transmission approval, then asks the model to compare and cite real returned URLs.

Generators:

- Images: `IMAGE_MODEL` must be advertised; OpenAI-compatible `/images/generations`, one image, `b64_json` response required.
- Speech: `TTS_MODEL` must be advertised; configure `TTS_VOICE`; `/audio/speech`, MP3 response.
- `/generator image model <id>`, `/generator tts model <id>`, `/generator tts voice <name>` change this process only.
- No model/voice fallback. Unsupported native payloads must use an explicit app adapter.
- Files/code/docs: UTF-8 `.md/.txt/.py/.js/.ts/.json/.html/.css/.csv/.yaml/.yml`. No automatic execution.
- Binary DOCX/PDF, provider-specific video models/polling and singing are not native capabilities of this implementation.
- Generated artifacts are sent after an approved operation succeeds. API/provider errors are not reported as success.
