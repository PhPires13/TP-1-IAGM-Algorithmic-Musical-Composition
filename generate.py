"""Gera corais no estilo de J. S. Bach com uma cadeia de Markov de ordem n

Exemplos:
    python generate.py                                  # 3 peças, ordem 3, T = 1.0
    python generate.py --order 1 --n 5 --seed 10
    python generate.py --order 5 --temperature 1.5 --phrases 6
"""

from __future__ import annotations

import argparse
from pathlib import Path

from markov_music.composer import compose
from markov_music.corpus import load_corpus
from markov_music.markov import MarkovChain
from markov_music.render import to_score, write_symbolic


def build_models(order: int):
    """Carrega o corpus e treina a cadeia da melodia

    :param order: ordem n da cadeia da melodia
    :return: (cadeia da melodia, sequências do corpus)
    """
    seqs, _ = load_corpus()
    model = MarkovChain(order).fit(seqs)
    return model, seqs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--order", type=int, default=3, help="ordem n da cadeia de Markov (memória)")
    ap.add_argument("--temperature", type=float, default=1.0, help="temperatura da amostragem")
    ap.add_argument("--phrases", type=int, default=4, help="número de frases (fermatas) da peça")
    ap.add_argument("--n", type=int, default=3, help="quantidade de peças a gerar")
    ap.add_argument("--seed", type=int, default=0, help="semente inicial (peça i usa seed+i)")
    ap.add_argument("--outdir", type=Path, default=Path("outputs"))
    args = ap.parse_args()

    model, seqs = build_models(args.order)
    print(f"Modelo de ordem {args.order}: {model.n_contexts()} contextos de {len(seqs)} corais.")

    for i in range(args.n):
        seed = args.seed + i
        comp = compose(model, seed, n_phrases=args.phrases, temperature=args.temperature)

        # ----- Arquivos simbólicos
        name = f"o{args.order}_t{args.temperature:g}_p{args.phrases}_s{seed}"
        base = args.outdir / name / name
        score = to_score(
            comp.tokens,
            title=f"Coral Markov (ordem {args.order}, T={args.temperature:g}, semente {seed})",
        )
        write_symbolic(score, base)

        print(f"[{i + 1}/{args.n}] {base.parent}  notas={len(comp.tokens)}")


if __name__ == "__main__":
    main()
