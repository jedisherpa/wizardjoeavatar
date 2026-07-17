const COMMAND_ROUTES = Object.freeze({
  action: "/api/avatar/wizard/action",
  gaze: "/api/avatar/wizard/gaze",
  move: "/api/avatar/wizard/move",
  path: "/api/avatar/wizard/path",
  expression: "/api/avatar/wizard/expression",
  speak: "/api/avatar/wizard/speak",
  "speech-stop": "/api/avatar/wizard/speech-stop",
  pose: "/api/avatar/wizard/pose",
  control: "/api/avatar/wizard/control",
  stop: "/api/avatar/wizard/stop",
  reset: "/api/avatar/wizard/reset",
});

function tauriInvoke() {
  return window.__TAURI__?.core?.invoke
    || window.__TAURI__?.invoke
    || window.__TAURI_INTERNALS__?.invoke
    || null;
}

function queryDescriptor() {
  const query = new URLSearchParams(location.search);
  const browserDemo = query.get("browserDemo") === "1" || query.get("demo") === "1";
  const baseUrl = query.get("runtimeBase") || query.get("baseUrl");
  const websocketUrl = query.get("wsUrl");
  if (!browserDemo && !baseUrl && !websocketUrl) return null;
  return { browserDemo, baseUrl, websocketUrl };
}

function normalizeDescriptor(value = {}) {
  const baseUrl = value.baseUrl || value.base_url || value.httpBaseUrl || value.http_base_url || "";
  const websocketUrl = value.websocketUrl
    || value.websocket_url
    || value.frameUrl
    || value.frame_url
    || "";
  const isTauri = Boolean(value.isTauri || value.is_tauri);
  return {
    baseUrl: String(baseUrl).replace(/\/$/, ""),
    websocketUrl: String(websocketUrl),
    appVersion: String(value.appVersion || value.app_version || "unknown"),
    browserDemo: Boolean(value.browserDemo || value.browser_demo),
    isTauri,
    httpTransport: String(value.httpTransport || value.http_transport || (isTauri ? "invoke" : "fetch")),
    frameTransport: String(value.frameTransport
      || value.frame_transport
      || (isTauri ? "tauri-event" : "websocket")),
    frameEventName: String(value.frameEventName || value.frame_event_name || "companion-frame"),
  };
}

export async function resolveRuntimeDescriptor() {
  const query = queryDescriptor();
  if (query) return normalizeDescriptor(query);

  const injected = window.__WIZARD_COMPANION_RUNTIME__;
  if (injected) return normalizeDescriptor({ ...injected, isTauri: Boolean(tauriInvoke()) });

  const invoke = tauriInvoke();
  if (invoke) {
    for (const command of [
      "companion_runtime_descriptor",
      "get_runtime_descriptor",
      "companion_get_runtime_descriptor",
      "runtime_descriptor",
    ]) {
      try {
        return normalizeDescriptor({ ...(await invoke(command)), isTauri: true });
      } catch {
        // Supports either shell command name while the lifecycle shell is integrated independently.
      }
    }
  }

  if (location.protocol === "http:" || location.protocol === "https:") {
    return normalizeDescriptor({ baseUrl: location.origin });
  }
  return normalizeDescriptor({ browserDemo: true });
}

export class RuntimeClient {
  constructor(descriptor) {
    this.descriptor = descriptor;
    this.invoke = tauriInvoke();
    this.mockState = {
      facing: "forward",
      gaze_target: "viewer",
      action: "idle",
      expression: "neutral",
      mouth: "closed",
      pose_id: "front_idle",
      animation_clip_id: "idle_front",
      animation_node_id: "ground_idle",
      world_position: { x: 0, z: 5 },
      simulation_tick: 0,
      state_revision: 0,
      semantic_cue: "none",
      semantic_gesture: "none",
      semantic_transition: "inactive",
      semantic_advisory_active: false,
      airborne: false,
      control_source: null,
    };
    this.mockPermissionWorld = { status: "empty", state: null, projection: null };
    this.mockReplay = [
      { record_type: "header", record_sequence: 0, simulation_tick: 0, payload: { schema_version: 1, seed: 7 } },
    ];
  }

  async request(path, options = {}) {
    if (this.descriptor.browserDemo) return this.mockRequest(path, options);
    if (this.invoke && this.descriptor.httpTransport === "invoke") {
      try {
        return await this.invokeRequest(path, options);
      } catch (error) {
        if (!this.descriptor.baseUrl) throw error;
      }
    }
    return this.fetchRequest(path, options);
  }

  async invokeRequest(path, options) {
    const request = {
      path,
      method: options.method || "GET",
      body: options.body === undefined ? null : options.body,
      responseType: options.responseType || "json",
    };
    const aliases = [
      "companion_http_request",
      "authenticated_runtime_request",
      "runtime_request",
    ];
    let lastError = null;
    for (const command of aliases) {
      for (const args of [{ request }, request]) {
        try {
          const result = await this.invoke(command, args);
          if (typeof result !== "string") return result;
          if (options.responseType === "text") return result;
          try {
            return JSON.parse(result);
          } catch {
            return result;
          }
        } catch (error) {
          lastError = error;
        }
      }
    }
    throw lastError;
  }

  async fetchRequest(path, options) {
    const headers = new Headers(options.headers || {});
    if (options.body !== undefined) headers.set("content-type", "application/json");
    const response = await fetch(`${this.descriptor.baseUrl}${path}`, {
      method: options.method || "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      cache: "no-store",
    });
    if (!response.ok) throw new Error(`Runtime request failed (${response.status})`);
    if (options.responseType === "text") return response.text();
    return response.json();
  }

  async command(type, payload = {}) {
    const movement = {
      "walk-left": { move_x: -1, move_z: 0 },
      "walk-right": { move_x: 1, move_z: 0 },
      "walk-forward": { move_x: 0, move_z: -1 },
      "walk-backward": { move_x: 0, move_z: 1 },
    }[type];
    if (movement) {
      return this.command("control", {
        source_kind: "keyboard",
        source_id: "companion-stage",
        source_sequence: Date.now(),
        source_epoch: "companion-window",
        lease_id: "companion-stage-movement",
        ttl_ms: 350,
        intent: { ...movement, speed_mode: "walk", mobility_request: "keep", held_actions: [] },
      });
    }
    const route = COMMAND_ROUTES[type];
    if (!route) throw new Error(`Unknown command ${type}`);
    return this.request(route, { method: "POST", body: payload });
  }

  async shellAction(name, payload = {}) {
    if (!this.invoke) return false;
    const aliases = {
      open_prism_gt: ["open_prism_gt", "companion_open_prism_gt"],
      restart_engine: ["restart_engine", "companion_restart_engine"],
      open_logs: ["open_logs", "companion_open_logs"],
      set_reactions_paused: ["set_reactions_paused", "companion_set_reactions_paused"],
      set_launch_at_login: ["set_launch_at_login", "companion_set_launch_at_login"],
      launch_at_login_status: ["launch_at_login_status", "companion_launch_at_login_status"],
      copy_safe_diagnostics: ["copy_safe_diagnostics", "companion_copy_safe_diagnostics"],
    }[name] || [name];
    let lastError = null;
    for (const command of aliases) {
      try {
        const result = await this.invoke(command, payload);
        return result ?? true;
      } catch (error) {
        lastError = error;
      }
    }
    throw lastError;
  }

  mockRequest(path, options) {
    if (path === "/api/companion/health") {
      return {
        schema_version: 1,
        status: "ready",
        runtime_epoch: "browser-preview",
        protocol_version: 1,
        character_id: "asciline-wizard-v1",
        frame_hub_running: true,
        connector_enabled: true,
        engine_version: "browser-preview",
      };
    }
    if (path === "/api/avatar/wizard/state") {
      return {
        state: { ...this.mockState },
        diagnostics: {
          pose_id: this.mockState.pose_id,
          animation_clip_id: this.mockState.animation_clip_id,
          animation_node_id: this.mockState.animation_node_id,
          mouth_state: this.mockState.mouth,
          current_action: this.mockState.action,
        },
        media: { status: "waiting", active: false, source: null, scheduler_state: "no_session" },
      };
    }
    if (path === "/api/avatar/wizard/poses") {
      return {
        poses: [
          "front_idle",
          "explaining",
          "magic_cast",
          "front_point_direct_staff_held",
          "front_thinking_hand_chin_wings",
          "front_victory_cast",
        ],
      };
    }
    if (path === "/api/avatar/wizard/character") {
      return {
        schema_version: 1,
        character_id: "wizard-joe-v1",
        display_name: "Wizard Joe",
        capabilities: ["actions", "speech_overlay", "progressive_text_preview"],
      };
    }
    if (path === "/api/avatar/wizard/replay") {
      return `${this.mockReplay.map((record) => JSON.stringify(record)).join("\n")}\n`;
    }
    if (path === "/api/avatar/wizard/permission-world" && options.method !== "POST") {
      return this.mockPermissionWorld;
    }
    if (options.method === "POST") {
      this.mockState.simulation_tick += 1;
      this.mockState.state_revision += 1;
      if (path.endsWith("/stop")) this.mockState.action = "idle";
      if (path.endsWith("/action")) this.mockState.action = options.body.action || "idle";
      if (path.endsWith("/gaze")) this.mockState.gaze_target = options.body.target || "viewer";
      if (path.endsWith("/move")) {
        this.mockState.world_position = { x: options.body.x, z: options.body.z };
        this.mockState.action = "walking";
      }
      if (path.endsWith("/path")) {
        const destination = options.body.points?.at(-1);
        if (destination) this.mockState.world_position = { ...destination };
        this.mockState.action = "walking";
      }
      if (path.endsWith("/expression")) this.mockState.expression = options.body.expression || "neutral";
      if (path.endsWith("/speak")) {
        this.mockState.action = "speaking";
        this.mockState.mouth = "open_small";
      }
      if (path.endsWith("/speech-stop")) {
        this.mockState.action = "idle";
        this.mockState.mouth = "closed";
      }
      if (path.endsWith("/pose")) {
        this.mockState.action = options.body.pose_id ? "posing" : "idle";
        this.mockState.pose_id = options.body.pose_id || "front_idle";
      }
      if (path.endsWith("/control")) {
        const intent = options.body.intent || {};
        const mobility = options.body.intent?.mobility_request;
        if (mobility === "takeoff") this.mockState.airborne = true;
        if (mobility === "land") this.mockState.airborne = false;
        if (intent.move_x || intent.move_z) this.mockState.action = "walking";
      }
      if (path === "/api/avatar/wizard/director/permission-world") {
        const permission = options.body.permissions?.[0];
        this.mockPermissionWorld = {
          status: "ready",
          state: null,
          projection: null,
          simulation_state: options.body,
          simulation_projection: {
            affordances: permission ? [{
              capability_kind: permission.capability_kind,
              permission_posture: permission.posture,
              scope_class: permission.required_scope_class,
              expiry_class: permission.expires_at_ms === null
                ? "unbounded"
                : permission.expires_at_ms <= Date.now() ? "expired" : "current",
            }] : [],
          },
        };
        return this.mockPermissionWorld;
      }
      this.mockReplay.push({
        record_type: "command",
        record_sequence: this.mockReplay.length,
        simulation_tick: this.mockState.simulation_tick,
        payload: { route: path.split("/").at(-1) },
      });
      return { ...this.mockState };
    }
    return {};
  }
}

export { normalizeDescriptor };
