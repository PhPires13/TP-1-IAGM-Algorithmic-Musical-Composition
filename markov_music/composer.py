"""Gera uma melodia de coral respeitando a forma escolhida como restrição estilística

Restrições: n_phrases frases terminadas em fermata, frases não muito curtas, 4/4 consistente e final na tônica
Elas são impostas durante a amostragem, removendo os estados proibidos da distribuição
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .markov import END, MarkovChain


@dataclass
class Composition:
    tokens: list[tuple]  # melodia: (altura, duração, posição no compasso, fermata)
    orders_used: list[int] = field(default_factory=list)  # ordem efetiva de cada passo após o backoff
    attempts: int = 1  # tentativas até satisfazer a forma


def compose_melody(model: MarkovChain, rng: np.random.Generator, n_phrases: int = 4, min_phrase_notes: int = 5,
                   max_phrase_notes: int = 16, max_attempts: int = 500) -> Composition:
    """Gera nota por nota até completar n_phrases frases, descartando tentativas que ficam longas demais

    :param model: cadeia de Markov treinada
    :param rng: gerador de números aleatórios
    :param n_phrases: número de frases (fermatas) da peça
    :param min_phrase_notes: tamanho mínimo de cada frase
    :param max_phrase_notes: tamanho médio máximo das frases (limita o total de notas)
    :param max_attempts: tentativas antes de desistir
    :return: a melodia gerada
    """
    max_notes = n_phrases * max_phrase_notes
    for attempt in range(1, max_attempts + 1):
        tokens, orders, phrases, phrase_len = [], [], 0, 0
        while len(tokens) < max_notes:
            last_phrase = phrases == n_phrases - 1
            too_short = phrase_len < min_phrase_notes - 1
            expected_beat = (tokens[-1][2] + tokens[-1][1]) % 4 if tokens else None  # posição + duração

            def allowed(sym):
                if sym == END:  # a peça só termina após n_phrases fermatas
                    return False
                rel, _dur, beat, ferm = sym
                if expected_beat is not None and abs(beat - expected_beat) > 1e-6:  # mantém a grade do 4/4
                    return False
                if ferm and too_short:  # frases muito curtas não soam como coral
                    return False
                if ferm and last_phrase and rel % 12 != 0:  # cadência final na tônica
                    return False
                return True

            sym, k = model.sample_next(tokens, rng, allowed)
            tokens.append(sym)
            orders.append(k)
            phrase_len += 1
            if sym[3]:  # fermata fecha a frase
                phrases, phrase_len = phrases + 1, 0
                if phrases == n_phrases:
                    return Composition(tokens, orders, attempt)
        # passou do tamanho máximo sem fechar a forma: rejeita e tenta de novo
    raise RuntimeError("não foi possível gerar uma peça que satisfaça a forma")


def compose(model: MarkovChain, seed: int, n_phrases: int = 4) -> Composition:
    """Gera uma melodia a partir de uma semente

    :param model: cadeia de Markov da melodia
    :param seed: semente (a mesma semente gera a mesma peça)
    :param n_phrases: número de frases da peça
    :return: a peça gerada
    """
    rng = np.random.default_rng(seed)
    comp = compose_melody(model, rng, n_phrases)
    return comp
