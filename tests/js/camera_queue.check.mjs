// Behavioural check of the browser camera queue (run by tests/test_camera_queue_js.py with Node; exits non-zero on failure).
import assert from "node:assert/strict";
import { fetchCameraFrame, beginExclusive, endExclusive } from "../../medidispense-ui/src/pages/TabletIdentification/cameraCapture.js";

let active = 0, maxActive = 0, calls = [], behaviour = () => ({ ok: true, blob: new Blob([new Uint8Array(10)]) });

globalThis.fetch = (url, { signal } = {}) => new Promise((resolve, reject) => {
  active += 1; maxActive = Math.max(maxActive, active); calls.push(url);
  const finish = (fn) => { active -= 1; fn(); };
  const b = behaviour(calls.length);
  if (b.hang) {
    signal.addEventListener("abort", () => finish(() => reject(new DOMException("Aborted", "AbortError"))));
    b.started && b.started();
    return;
  }
  setTimeout(() => finish(() => resolve({ ok: b.ok !== false, status: b.status || 200, blob: async () => b.blob || new Blob([]), json: async () => b.json || {} })), b.delay || 5);
});

const api = "http://x";

// 1. single flight: concurrent captures never overlap at the fetch level
await Promise.all([fetchCameraFrame(api), fetchCameraFrame(api), fetchCameraFrame(api)]);
assert.equal(maxActive, 1, "captures overlapped");
assert.equal(calls.length, 3);
assert.ok(calls.every(u => u === "http://x/api/v1/camera/capture"));

// 2. a failing capture does not block later ones, and the error text comes from the backend
behaviour = () => ({ ok: false, status: 504, json: { detail: { message: "Camera timed out" } } });
await assert.rejects(fetchCameraFrame(api), /Camera timed out/);
behaviour = () => ({ ok: true, blob: new Blob([]) });
await assert.rejects(fetchCameraFrame(api), /empty image/);
behaviour = () => ({ ok: true, blob: new Blob([new Uint8Array(5)]) });
assert.equal((await fetchCameraFrame(api)).size, 5);

// 3. exclusive access: preview is refused while held, and a preview request in flight is abandoned
let release; const started = new Promise(r => { release = r; });
behaviour = (n) => ({ hang: true, started: release });
const live = fetchCameraFrame(api);                       // hangs at the camera
await started;
behaviour = () => ({ ok: true, blob: new Blob([new Uint8Array(7)]) });
beginExclusive();
await assert.rejects(live, (e) => e.name === "AbortError");
await assert.rejects(fetchCameraFrame(api), (e) => e.code === "CAMERA_PAUSED");        // preview refused
assert.equal((await fetchCameraFrame(api, { exclusive: true })).size, 7);              // the exclusive capture proceeds
endExclusive();
assert.equal((await fetchCameraFrame(api)).size, 7);                                   // preview works again
assert.equal(active, 0);

// 4. an already-cancelled request never reaches the camera
const before = calls.length;
const ctrl = new AbortController(); ctrl.abort();
await assert.rejects(fetchCameraFrame(api, { signal: ctrl.signal }), (e) => e.name === "AbortError");
assert.equal(calls.length, before);

console.log("camera queue checks passed");
