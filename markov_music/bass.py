"""Cadeia de Markov condicional que gera a linha do baixo para uma melodia já pronta

A nota do baixo depende do baixo anterior e da nota do soprano no mesmo instante: P(b_t | b_t-1, s_t, posicao_t)
Como esse contexto é esparso, há backoff para contextos cada vez mais simples
"""

from __future__ import annotations

from collections import Counter, defaultdict

import numpy as np

from .markov import MarkovChain


def _contexts(prev_bass, sop_rel, beat):
    """Lista os contextos do mais específico ao mais genérico (ordem do backoff)

    :param prev_bass: nota anterior do baixo (None no início)
    :param sop_rel: altura do soprano relativa à tônica
    :param beat: posição métrica da nota no compasso
    :return: lista de tuplas de contexto
    """
    return [
        ("b-s-beat", prev_bass, sop_rel, beat),
        ("b-s", prev_bass, sop_rel),
        ("s", sop_rel),
        ("s-pc", sop_rel % 12),
        ("uni",),
    ]


class BassChain:
    def __init__(self):
        self.counts: dict[tuple, Counter] = defaultdict(Counter)  # contexto -> Counter(nota do baixo)

    def fit(self, soprano_seqs, bass_seqs) -> "BassChain":
        """Conta as notas do baixo observadas em cada contexto do corpus

        :param soprano_seqs: sequências de tokens do soprano
        :param bass_seqs: alturas do baixo alinhadas a cada nota do soprano
        :return: o próprio modelo treinado
        """
        for sop, bass in zip(soprano_seqs, bass_seqs):
            prev = None
            for tok, b in zip(sop, bass):
                for ctx in _contexts(prev, tok[0], tok[2]):
                    self.counts[ctx][b] += 1
                prev = b
        return self

    def generate(self, soprano_tokens, rng: np.random.Generator, temperature: float = 1.0):
        """Sorteia uma nota de baixo para cada nota da melodia

        :param soprano_tokens: melodia gerada
        :param rng: gerador de números aleatórios
        :param temperature: temperatura da amostragem
        :return: lista de alturas do baixo relativas à tônica
        """
        bass = []
        prev = None
        for i, tok in enumerate(soprano_tokens):
            sop_rel = tok[0]
            last = i == len(soprano_tokens) - 1

            def allowed(b):
                if b > sop_rel - 3:  # baixo sempre abaixo do soprano
                    return False
                if b < -24 or b > 7:  # tessitura do baixo (Dó2 a Sol4 em Dó maior)
                    return False
                if last and b % 12 != 0:  # cadência final na tônica
                    return False
                return True

            # usa o contexto mais específico que tenha alguma nota permitida
            for ctx in _contexts(prev, sop_rel, tok[2]):
                cnt = self.counts.get(ctx)
                if not cnt:
                    continue
                items = [(b, c) for b, c in cnt.items() if allowed(b)]
                if items:
                    break
            else:  # nunca deveria acontecer, mantém a tônica como fallback
                items = [(-12, 1)]

            symbols = [b for b, _ in items]
            probs = np.array([c for _, c in items], dtype=float)
            probs = MarkovChain.apply_temperature(probs / probs.sum(), temperature)
            prev = symbols[rng.choice(len(symbols), p=probs)]
            bass.append(prev)
        return bass
