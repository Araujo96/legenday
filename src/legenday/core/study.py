"""Recursos de estudo sem interface (fáceis de testar): modo repetir frase e agenda de revisão."""
from datetime import datetime, timedelta

# ---------------------------------------------------------------- modo repetir frase (shadowing)
LEAD = 0.08   # pausa um pouco antes do fim da fala: o relógio da legenda anda de 40 em 40 ms


class Shadowing:
    """Pausa o vídeo no fim de cada fala, para o aluno repetir em voz alta antes de seguir.

    A cada instante recebe a posição do vídeo e responde se é hora de pausar. Cada fala pausa uma vez só;
    depois de um pulo (repetir frase, barra de tempo...), chame reset() para ela poder pausar de novo."""

    def __init__(self):
        self.enabled = False
        self.reset()

    def reset(self) -> None:
        self._watch = None    # fala que está sendo acompanhada
        self._done = None     # última fala em que já pausou

    def should_pause(self, track, t: float) -> bool:
        if not self.enabled or track is None or t is None:
            return False
        hit = False
        w = self._watch
        if w is not None and w != self._done and t >= track.end_of(w) - LEAD:
            self._done, hit = w, True
        current = track.active_at(t)
        if current >= 0:
            self._watch = current
        return hit


# ---------------------------------------------------------------- revisão espaçada (caixas de Leitner)
INTERVALS = (0, 1, 3, 7, 16, 35)        # dias até a próxima revisão, por caixa
RETRY = timedelta(minutes=10)           # errou: volta ainda hoje


def schedule(box: int, correct: bool, now: datetime) -> tuple:
    """(nova caixa, próxima revisão). Acertou: sobe uma caixa e o intervalo cresce. Errou: volta ao começo."""
    if not correct:
        return 0, now + RETRY
    box = min(box + 1, len(INTERVALS) - 1)
    return box, now + timedelta(days=INTERVALS[box])


def is_due(due: str, now: datetime) -> bool:
    """Palavra nunca revisada (due vazio) ou com a data de revisão já passada."""
    if not due:
        return True
    try:
        return datetime.fromisoformat(due) <= now
    except ValueError:
        return True
