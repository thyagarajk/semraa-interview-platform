"""Background sampler for whole-device GPU memory (covers Ollama, which runs in its own process)."""

from __future__ import annotations

import threading
from types import TracebackType
from typing import Any


class GpuMemorySampler:
    def __init__(self, interval_s: float = 0.05, device: int = 0) -> None:
        self.interval_s = interval_s
        self.device = device
        self.peak_mb = 0.0
        self.start_mb = 0.0
        self.total_mb = 0.0
        self.name = ""
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._nvml: Any = None
        self._handle: Any = None

    def _used_mb(self) -> float:
        info = self._nvml.nvmlDeviceGetMemoryInfo(self._handle)
        return float(info.used) / (1024 * 1024)

    def __enter__(self) -> GpuMemorySampler:
        import pynvml

        pynvml.nvmlInit()
        self._nvml = pynvml
        self._handle = pynvml.nvmlDeviceGetHandleByIndex(self.device)
        name = pynvml.nvmlDeviceGetName(self._handle)
        self.name = name.decode() if isinstance(name, bytes) else str(name)
        self.total_mb = float(pynvml.nvmlDeviceGetMemoryInfo(self._handle).total) / (1024 * 1024)
        self.start_mb = self.peak_mb = self._used_mb()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def _run(self) -> None:
        while not self._stop.wait(self.interval_s):
            self.peak_mb = max(self.peak_mb, self._used_mb())

    def sample_now(self) -> float:
        used = self._used_mb()
        self.peak_mb = max(self.peak_mb, used)
        return used

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
        self.sample_now()
        self._nvml.nvmlShutdown()
