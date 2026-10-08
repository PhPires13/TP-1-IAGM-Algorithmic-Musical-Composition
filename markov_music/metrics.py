"""Métricas que quantificam o trade-off entre novidade e memorização do corpus"""

from __future__ import annotations

import numpy as np


def longest_copied_run(gen, corpus_seqs) -> tuple[int, int]:
    """Maior trecho contíguo da peça que aparece idêntico em alguma peça do corpus (maior substring comum)

    :param gen: tokens da peça gerada
    :param corpus_seqs: sequências do corpus
    :return: (tamanho do trecho em notas, índice da peça do corpus de onde ele veio)
    """
    best, best_idx = 0, -1
    g = list(gen)
    for idx, seq in enumerate(corpus_seqs):
        s = list(seq)
        prev = [0] * (len(s) + 1)  # programação dinâmica: prev[j] = trecho comum que termina em g[i-1] e s[j-1]
        for i in range(1, len(g) + 1):
            cur = [0] * (len(s) + 1)
            gi = g[i - 1]
            for j in range(1, len(s) + 1):
                if gi == s[j - 1]:
                    cur[j] = prev[j - 1] + 1
                    if cur[j] > best:
                        best, best_idx = cur[j], idx
            prev = cur
    return best, best_idx


def ngram_set(seqs, n):
    """Conjunto de todos os n-gramas (trechos de n notas) das sequências

    :param seqs: sequências de tokens
    :param n: tamanho do trecho
    :return: conjunto de tuplas
    """
    out = set()
    for s in seqs:
        out.update(tuple(s[i:i + n]) for i in range(len(s) - n + 1))
    return out


def novelty(gen, corpus_ngrams: set, n: int) -> float:
    """Fração dos n-gramas da peça que não existem no corpus

    :param gen: tokens da peça gerada
    :param corpus_ngrams: n-gramas do corpus (ver ngram_set)
    :param n: tamanho do trecho
    :return: fração entre 0 e 1
    """
    grams = [tuple(gen[i:i + n]) for i in range(len(gen) - n + 1)]
    if not grams:
        return 0.0
    return sum(g not in corpus_ngrams for g in grams) / len(grams)


def describe(comp, corpus_seqs, corpus_8grams=None) -> dict:
    """Calcula todas as métricas de uma peça

    :param comp: peça gerada (Composition)
    :param corpus_seqs: sequências do corpus
    :param corpus_8grams: 8-gramas do corpus pré-calculados (opcional, acelera o experimento)
    :return: dicionário com as métricas
    """
    toks = comp.tokens
    run, idx = longest_copied_run(toks, corpus_seqs)
    if corpus_8grams is None:
        corpus_8grams = ngram_set(corpus_seqs, 8)
    rels = [t[0] for t in toks]
    return {
        "n_notes": len(toks),
        "duration_quarters": float(sum(t[1] for t in toks)),
        "longest_copied_run": run,
        "copied_from": idx,
        "novel_8gram_ratio": novelty(toks, corpus_8grams, 8),
        "mean_order_used": float(np.mean(comp.orders_used)),
        "pitch_range": max(rels) - min(rels),
        "attempts": comp.attempts,
    }
