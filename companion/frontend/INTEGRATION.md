# Companion Frontend Bridge Contract

The companion backend requires bearer headers and literal-loopback origins in
companion mode. A Tauri WebView cannot set an `Authorization` header on a
browser `WebSocket`, and its application origin is not a literal-loopback HTTP
origin. The shell must therefore provide one of the authenticated transports
below. Credentials remain launch-scoped and are never stored in these assets.

## Preferred Tauri bridge

The runtime descriptor carries transport metadata and dynamic loopback URLs,
but never credentials. The frontend selects `httpTransport: "invoke"` and
`frameTransport: "tauri-event"` for a descriptor returned by Tauri unless the
descriptor explicitly overrides them. Rust owns every bearer header and keeps
the app-control credential outside WebView state, URLs, logs, and assets.

HTTP commands, tried in order:

- `companion_http_request`
- `authenticated_runtime_request`
- `runtime_request`

Each receives either `{ request: { path, method, body } }` or the request fields
at the top level. The Rust side owns the bearer header and returns parsed JSON
or a JSON string.

Frame commands:

- Start: `start_companion_frame_stream` or `companion_start_frame_stream`
- Resync: `resync_companion_frame_stream` or `companion_resync_frame_stream`
- Stop: `stop_companion_frame_stream` or `companion_stop_frame_stream`

Start receives `{ eventName }`. The default event name is `companion-frame`.
Events may carry the ASCILINE `INIT` string directly, a byte array directly, or
an object shaped as `{ type: "text", data }` or
`{ type: "binary", data | base64 }`.

## Shell-owned proxy alternative

A shell-owned literal-loopback proxy may perform authentication and origin
handling instead. Its descriptor must explicitly set:

```json
{
  "httpTransport": "fetch",
  "frameTransport": "websocket",
  "baseUrl": "http://127.0.0.1:<proxy-port>",
  "websocketUrl": "ws://127.0.0.1:<proxy-port>/frames"
}
```

The browser fallback (`?browserDemo=1`) requires neither bridge and remains
available for frontend QA.
