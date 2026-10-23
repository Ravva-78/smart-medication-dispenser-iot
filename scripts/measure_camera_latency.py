"""
Measure real ESP32 capture latency and failure rate (read-only; writes nothing).

Usage:
    python scripts/measure_camera_latency.py [--url http://<ip>/capture] [--n 10] [--gap 1.0]

Uses the same capture client as the app (app/camera.py), so the numbers include the same timeouts.
Use the result to decide whether a "capture -> flip -> capture" workflow can realistically have a time budget.
"""
import argparse
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.dont_write_bytecode = True
from app import camera  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="capture URL (default: ESP32_CAM_URL / ESP32_CAM_IP)")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--gap", type=float, default=1.0, help="seconds between captures")
    args = ap.parse_args()

    ok, failed, sizes = [], {}, []
    for i in range(1, args.n + 1):
        t = time.perf_counter()
        try:
            jpeg = camera.capture_jpeg(args.url)
            dt = time.perf_counter() - t
            ok.append(dt)
            sizes.append(len(jpeg))
            print(f"{i:2}: OK   {dt:5.1f}s  {len(jpeg) / 1024:5.1f} KB", flush=True)
        except camera.CameraError as err:
            dt = time.perf_counter() - t
            failed[err.kind] = failed.get(err.kind, 0) + 1
            print(f"{i:2}: FAIL {dt:5.1f}s  {err.kind}", flush=True)
        time.sleep(args.gap)

    print(f"\n{len(ok)}/{args.n} succeeded; failures by kind: {failed or 'none'}")
    if ok:
        ok.sort()
        p90 = ok[min(len(ok) - 1, int(round(0.9 * (len(ok) - 1))))]
        print(f"successful capture time: min {ok[0]:.1f}s | median {statistics.median(ok):.1f}s | p90 {p90:.1f}s | max {ok[-1]:.1f}s")
        print(f"average frame {statistics.mean(sizes) / 1024:.1f} KB -> about {statistics.mean(sizes) / 1024 / statistics.mean(ok):.1f} KB/s effective")
        within = sum(1 for x in ok if x <= 4.0)
        print(f"captures within 4 s: {within}/{args.n} ({100 * within / args.n:.0f}% of all attempts)")


if __name__ == "__main__":
    main()
