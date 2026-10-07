"""Experimento do trade-off entre ordem baixa e ordem alta

Para cada par (ordem, temperatura) gera N peças com sementes diferentes e mede quanto elas copiam o corpus
Salva a tabela e a figura usada no resumo em results/

    python experiment.py            # ordens 1 a 6, T em {0.5, 1.0, 1.5}, 30 sementes
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # gera a figura sem abrir janela
import matplotlib.pyplot as plt
import numpy as np

from markov_music.composer import compose
from markov_music.corpus import load_corpus
from markov_music.markov import MarkovChain
from markov_music.metrics import describe, ngram_set

ROOT = Path(__file__).resolve().parent


def run(orders, temps, n_seeds, mode):
    """Gera e mede n_seeds peças (só melodia) para cada combinação de ordem e temperatura

    :param orders: ordens a testar
    :param temps: temperaturas a testar
    :param n_seeds: peças por combinação
    :param mode: "major" ou "minor"
    :return: lista de dicionários, um por peça
    """
    seqs, _, _ = load_corpus(mode)
    grams8 = ngram_set(seqs, 8)
    rows = []
    for order in orders:
        model = MarkovChain(order).fit(seqs)
        for T in temps:
            for seed in range(n_seeds):
                comp = compose(model, None, seed, n_phrases=4, temperature=T)
                m = describe(comp, seqs, grams8)
                m.update(order=order, temperature=T, seed=seed, n_contexts=model.n_contexts())
                rows.append(m)

            sel = [r for r in rows if r["order"] == order and r["temperature"] == T]
            copied = np.mean([r["longest_copied_run"] for r in sel])
            novel = np.mean([r["novel_8gram_ratio"] for r in sel])
            mean_order = np.mean([r["mean_order_used"] for r in sel])
            print(f"ordem={order} T={T}: copia={copied:5.1f}  novos8={novel:.2f}  ordem_media={mean_order:.2f}")
    return rows


def summarize(rows, orders, temps, key):
    """Média e desvio-padrão de uma métrica para cada (temperatura, ordem)

    :param rows: resultados de run
    :param orders: ordens testadas
    :param temps: temperaturas testadas
    :param key: nome da métrica
    :return: (médias, desvios), matrizes de formato (temperaturas, ordens)
    """
    def values(o, t):
        return [r[key] for r in rows if r["order"] == o and r["temperature"] == t]

    mean = np.array([
        [np.mean(values(o, t)) for o in orders]
        for t in temps
    ])
    std = np.array([
        [np.std(values(o, t)) for o in orders]
        for t in temps
    ])
    return mean, std


def plot(rows, orders, temps, path: Path):
    """Gera a figura do resumo: maior trecho copiado e fração de 8-gramas inéditos por ordem

    :param rows: resultados de run
    :param orders: ordens testadas
    :param temps: temperaturas testadas
    :param path: caminho do .pdf de saída
    """
    plt.rcParams.update({"font.size": 6.5, "font.family": "serif"})
    fig, axes = plt.subplots(1, 2, figsize=(3.4, 1.6))  # largura de uma coluna do ISMIR
    colors = ["#1f77b4", "#2ca02c", "#d62728"]
    panels = [
        ("longest_copied_run", "Maior trecho copiado\n(notas)"),
        ("novel_8gram_ratio", "Fração de 8-gramas\ninéditos"),
    ]
    for ax, (key, label) in zip(axes, panels):
        mean, std = summarize(rows, orders, temps, key)
        for i, T in enumerate(temps):
            ax.errorbar(
                orders,
                mean[i],
                yerr=std[i],
                marker="o",
                ms=2,
                capsize=1.5,
                color=colors[i % len(colors)],
                label=f"T = {T:g}",
                lw=0.8,
                elinewidth=0.6,
            )
        ax.set_xlabel("Ordem $n$")
        ax.set_ylabel(label)
        ax.set_xticks(orders)
        ax.grid(alpha=0.3)
    axes[0].legend(frameon=False, handlelength=1.2, borderaxespad=0.2)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    print(f"figura salva em {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orders", type=int, nargs="+", default=[1, 2, 3, 4, 5, 6])
    ap.add_argument("--temps", type=float, nargs="+", default=[0.5, 1.0, 1.5])
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--mode", default="major")
    args = ap.parse_args()

    rows = run(args.orders, args.temps, args.seeds, args.mode)

    # ----- Tabela
    out = ROOT / "results" / f"tradeoff_{args.mode}.csv"
    out.parent.mkdir(exist_ok=True)
    cols = [
        "order",
        "temperature",
        "seed",
        "n_contexts",
        "n_notes",
        "duration_quarters",
        "longest_copied_run",
        "novel_8gram_ratio",
        "mean_order_used",
        "pitch_range",
        "pc_kl",
        "attempts",
    ]
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")  # ignora campos que não estão em cols
        w.writeheader()
        w.writerows(rows)
    print(f"tabela salva em {out}")

    # ----- Figura
    plot(rows, args.orders, args.temps, ROOT / "results" / "tradeoff.pdf")


if __name__ == "__main__":
    main()
