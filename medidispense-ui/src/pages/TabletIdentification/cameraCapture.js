/**
 * One-at-a-time access to the ESP32 camera through the backend (GET /api/v1/camera/capture).
 *
 * The ESP32 serves a single request at a time and overlapping requests can hang it, so every capture in the
 * browser goes through this queue. The live preview is "passive": while another part of the page holds
 * exclusive access (the Stage B reverse-side capture) preview requests are refused instead of queued, and any
 * preview request already in flight is abandoned so the exclusive capture is not stuck behind it.
 *
 * This module only reads frames. It never starts a scan and never writes anything.
 */

let queue = Promise.resolve();   // tail of the request chain: the next capture starts when the previous one settles
let exclusiveHolders = 0;
let liveAbort = null;            // AbortController of the preview request currently in flight

export class CameraPausedError extends Error {
  constructor() {
    super("Live preview paused while another capture uses the camera.");
    this.code = "CAMERA_PAUSED";
  }
}

async function errorText(res) {
  try {
    const d = (await res.json()).detail;
    return (d && d.message) || (typeof d === "string" ? d : `Camera request failed (HTTP ${res.status}).`);
  } catch {
    return `Camera request failed (HTTP ${res.status}).`;
  }
}

export function beginExclusive() {
  exclusiveHolders += 1;
  if (liveAbort) liveAbort.abort();
}

export function endExclusive() {
  exclusiveHolders = Math.max(0, exclusiveHolders - 1);
}

/** Resolves with the JPEG Blob of one new capture, or rejects with a readable Error. */
export function fetchCameraFrame(apiUrl, { signal, exclusive = false } = {}) {
  if (!exclusive && exclusiveHolders > 0) return Promise.reject(new CameraPausedError());

  const run = async () => {
    if (!exclusive && exclusiveHolders > 0) throw new CameraPausedError();
    if (signal && signal.aborted) throw new DOMException("Aborted", "AbortError");
    const ctrl = new AbortController();
    const onAbort = () => ctrl.abort();
    if (signal) signal.addEventListener("abort", onAbort);
    if (!exclusive) liveAbort = ctrl;
    try {
      const res = await fetch(`${apiUrl}/api/v1/camera/capture`, { cache: "no-store", signal: ctrl.signal });
      if (!res.ok) throw new Error(await errorText(res));
      const blob = await res.blob();
      if (!blob.size) throw new Error("The camera returned an empty image.");
      return blob;
    } finally {
      if (signal) signal.removeEventListener("abort", onAbort);
      if (liveAbort === ctrl) liveAbort = null;
    }
  };

  const result = queue.then(run, run);
  queue = result.then(() => undefined, () => undefined);
  return result;
}
