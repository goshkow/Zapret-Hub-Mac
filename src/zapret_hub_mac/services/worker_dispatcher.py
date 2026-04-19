from __future__ import annotations

from concurrent.futures import Future
from queue import Queue
from threading import Event, Thread
from typing import Any, Callable


class SerialWorkerDispatcher:
    def __init__(self, name: str) -> None:
        self._queue: Queue[tuple[Future[Any], Callable[..., Any], tuple[Any, ...], dict[str, Any]] | None] = Queue()
        self._stopped = Event()
        self._thread = Thread(target=self._run, name=name, daemon=True)
        self._thread.start()

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Future[Any]:
        future: Future[Any] = Future()
        self._queue.put((future, fn, args, kwargs))
        return future

    def shutdown(self) -> None:
        if self._stopped.is_set():
            return
        self._stopped.set()
        self._queue.put(None)
        self._thread.join(timeout=1.0)

    def _run(self) -> None:
        while not self._stopped.is_set():
            item = self._queue.get()
            if item is None:
                self._queue.task_done()
                break
            future, fn, args, kwargs = item
            if future.set_running_or_notify_cancel():
                try:
                    result = fn(*args, **kwargs)
                except BaseException as exc:
                    future.set_exception(exc)
                else:
                    future.set_result(result)
            self._queue.task_done()
