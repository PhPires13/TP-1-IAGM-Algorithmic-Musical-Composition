"""Cadeia de Markov de ordem n com backoff e amostragem com temperatura

P(x_t | x_t-n ... x_t-1) é estimada por máxima verossimilhança (contagens) no corpus
Se o contexto de ordem n nunca foi visto ou todas as continuações são proibidas, o modelo recua para a ordem n-1
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Callable, Hashable, Sequence

import numpy as np

START = "<s>"  # preenche o contexto antes da primeira nota
END = "</s>"  # marca o fim de uma peça


class MarkovChain:
    def __init__(self, order: int):
        if order < 1:
            raise ValueError("a ordem deve ser >= 1")
        self.order = order
        self.counts: list[dict[tuple, Counter]] = [  # counts[k][contexto de tamanho k] -> Counter(próximo estado)
            defaultdict(Counter)
            for _ in range(order + 1)
        ]

    # ---------- TREINO ----------

    def fit(self, sequences: Sequence[Sequence[Hashable]]) -> "MarkovChain":
        """Conta as transições do corpus para todas as ordens de 0 a n (as menores são usadas no backoff)

        :param sequences: sequências de estados do corpus
        :return: o próprio modelo treinado
        """
        for seq in sequences:
            padded = [START] * self.order + list(seq) + [END]
            for t in range(self.order, len(padded)):
                nxt = padded[t]
                for k in range(self.order + 1):
                    ctx = tuple(padded[t - k:t])
                    self.counts[k][ctx][nxt] += 1
        return self

    def n_contexts(self, k: int | None = None) -> int:
        """Número de contextos distintos vistos no treino

        :param k: ordem do contexto (padrão: a ordem do modelo)
        :return: quantidade de contextos
        """
        return len(self.counts[self.order if k is None else k])

    def transition_matrix(self, k: int | None = None) -> dict[tuple, dict]:
        """Probabilidades de transição normalizadas (apenas para inspeção)

        :param k: ordem do contexto (padrão: a ordem do modelo)
        :return: dicionário contexto -> {próximo estado: probabilidade}
        """
        k = self.order if k is None else k
        return {
            ctx: {s: c / sum(cnt.values()) for s, c in cnt.items()}
            for ctx, cnt in self.counts[k].items()
        }

    # ---------- GERAÇÃO ----------

    def next_distribution(self, history: Sequence[Hashable], allowed: Callable[[Hashable], bool] | None = None):
        """Distribuição do próximo estado, recuando de ordem até achar um contexto com continuação permitida

        :param history: estados gerados até agora
        :param allowed: filtro das restrições (None permite tudo)
        :return: (estados, probabilidades, ordem usada)
        """
        padded = [START] * self.order + list(history)
        for k in range(self.order, -1, -1):
            ctx = tuple(padded[len(padded) - k:]) if k > 0 else ()
            cnt = self.counts[k].get(ctx)
            if not cnt:  # contexto nunca visto: recua
                continue
            items = [(s, c) for s, c in cnt.items() if allowed is None or allowed(s)]
            if not items:  # todas as continuações proibidas: recua
                continue
            symbols = [s for s, _ in items]
            probs = np.array([c for _, c in items], dtype=float)
            return symbols, probs / probs.sum(), k
        raise RuntimeError("nenhuma continuação válida, nem na ordem 0")

    @staticmethod
    def apply_temperature(probs: np.ndarray, temperature: float) -> np.ndarray:
        """Reescala as probabilidades: T < 1 favorece as transições comuns, T > 1 deixa a escolha mais uniforme

        :param probs: probabilidades originais
        :param temperature: temperatura (0 escolhe sempre a mais provável)
        :return: probabilidades reescaladas
        """
        if temperature <= 0:
            out = np.zeros_like(probs)
            out[np.argmax(probs)] = 1.0
            return out
        logp = np.log(probs) / temperature  # equivale a p^(1/T)
        logp -= logp.max()  # estabilidade numérica
        p = np.exp(logp)
        return p / p.sum()

    def sample_next(self, history, rng: np.random.Generator, temperature: float = 1.0,
                    allowed: Callable[[Hashable], bool] | None = None):
        """Sorteia o próximo estado

        :param history: estados gerados até agora
        :param rng: gerador de números aleatórios
        :param temperature: temperatura da amostragem
        :param allowed: filtro das restrições (None permite tudo)
        :return: (estado sorteado, ordem usada)
        """
        symbols, probs, k = self.next_distribution(history, allowed)
        probs = self.apply_temperature(probs, temperature)
        idx = rng.choice(len(symbols), p=probs)
        return symbols[idx], k
