"""Tarefas em segundo plano (tradução, dicionário, ffmpeg...) para não travar a interface.

    tasks.run(lambda: lookup.quick(text), on_done)

`on_done(resultado)` roda de volta na thread da interface; se a tarefa falhar, recebe a exceção.
"""
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class TaskRunner(QObject):
    _finished = Signal(int, object)

    def __init__(self, parent=None, pool=None):
        super().__init__(parent)
        self.pool = pool or QThreadPool.globalInstance()
        self._callbacks = {}
        self._next = 0
        self._finished.connect(self._dispatch)

    def run(self, fn, on_done=None) -> None:
        self._next += 1
        self._callbacks[self._next] = on_done
        self.pool.start(_Task(self._next, fn, self))

    def _dispatch(self, task_id: int, payload) -> None:
        callback = self._callbacks.pop(task_id, None)
        if callback is not None:
            callback(payload)

    def wait(self, ms: int = 1000) -> bool:
        return self.pool.waitForDone(ms)


class _Task(QRunnable):
    def __init__(self, task_id: int, fn, runner: TaskRunner):
        super().__init__()
        self.task_id, self.fn, self.runner = task_id, fn, runner

    def run(self):
        try:
            result = self.fn()
        except Exception as exc:
            result = exc
        try:
            self.runner._finished.emit(self.task_id, result)
        except RuntimeError:   # janela já foi fechada
            pass
