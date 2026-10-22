"""Sample device-wide GPU telemetry; never label it as process allocation."""
import subprocess
import threading
import time


def sample():
    result = subprocess.run(["nvidia-smi", "--query-gpu=uuid,memory.used,utilization.gpu",
                             "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=3,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        raise RuntimeError("nvidia-smi unavailable")
    return [{"uuid": parts[0].strip(), "memory_used_gib": float(parts[1]) / 1024,
             "utilization_percent": float(parts[2]), "monotonic_s": time.monotonic()}
            for line in result.stdout.splitlines() if line.strip() for parts in [line.split(",")]]


class GPUSampler:
    def __init__(self, interval=0.25):
        self.interval, self.samples, self.error = interval, [], None
        self.stop = threading.Event()

    def collect(self):
        try:
            self.samples.extend(sample())
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
            self.error = type(exc).__name__

    def loop(self):
        while not self.stop.wait(self.interval):
            self.collect()

    def __enter__(self):
        self.collect()
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.stop.set()
        self.thread.join(timeout=4)
        self.collect()

    def report(self):
        return {"status": "measured" if self.samples else "unavailable", "reason": self.error,
                "scope": "all visible GPUs, device-wide including other processes", "interval_seconds": self.interval,
                "samples": self.samples,
                "peak_device_memory_used_gib": max((s["memory_used_gib"] for s in self.samples), default=None),
                "mean_device_utilization_percent": sum(s["utilization_percent"] for s in self.samples) / len(self.samples) if self.samples else None}
