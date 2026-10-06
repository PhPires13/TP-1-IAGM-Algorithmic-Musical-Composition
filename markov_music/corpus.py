"""Extrai o corpus de treino: linhas de soprano (e o baixo correspondente) dos corais de J. S. Bach do music21

Cada nota do soprano vira um token (altura relativa à tônica, duração, posição no compasso, fermata)
Todas as peças são transpostas para Dó maior, então o modelo aprende graus da escala
"""

from __future__ import annotations

import json
from pathlib import Path

from music21 import corpus, interval, note as m21note

TONIC_MIDI = 60  # Dó central: referência das alturas relativas
ALLOWED_DURATIONS = {0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0}  # sem quiálteras

CACHE_DIR = Path(__file__).resolve().parent.parent / "corpus"


# ---------- CONVERSÃO DE TOKENS ----------

def token_to_str(tok: tuple) -> str:
    """Converte um token em texto para salvar no cache JSON

    :param tok: token (altura, duração, posição, fermata)
    :return: texto no formato "altura|duração|posição|fermata"
    """
    rel, dur, beat, ferm = tok
    return f"{rel}|{dur}|{beat}|{int(ferm)}"


def str_to_token(s: str) -> tuple:
    """Converte o texto do cache JSON de volta em token

    :param s: texto no formato "altura|duração|posição|fermata"
    :return: token (altura, duração, posição, fermata)
    """
    rel, dur, beat, ferm = s.split("|")
    return (int(rel), float(dur), float(beat), bool(int(ferm)))


# ---------- EXTRAÇÃO ----------

def _soprano_part(score):
    """Encontra a voz do soprano (ou a primeira voz, se nenhuma tiver esse nome)

    :param score: partitura do music21
    :return: a voz do soprano
    """
    for p in score.parts:
        name = (p.partName or p.id or "").lower()
        if "soprano" in name:
            return p
    return score.parts[0]


def chorale_to_tokens(score):
    """Converte um coral em tokens do soprano e alturas do baixo, se ele seguir a restrição de estilo

    :param score: partitura do coral
    :return: (tokens do soprano, baixo que soa em cada nota do soprano), ou None se a peça for descartada
    """
    part = _soprano_part(score)
    bass = score.parts[-1]

    # ----- Filtros da restrição de estilo
    sigs = part.recurse().getElementsByClass("TimeSignature")
    if not sigs or any(ts.ratioString != "4/4" for ts in sigs):  # só compasso 4/4
        return None

    k = score.analyze("key")
    if k.mode != "major":
        return None

    # ----- Transposição para Dó maior pelo menor intervalo (+-6 semitons), preservando a tessitura
    semis = -k.tonic.pitchClass % 12
    if semis > 6:
        semis -= 12
    iv = interval.Interval(semis)
    part = part.transpose(iv).stripTies()
    bass_notes = bass.transpose(iv).stripTies().flatten().notes.stream()

    # ----- Tokenização
    tokens, bass_rel = [], []
    for n in part.flatten().notesAndRests:
        if not isinstance(n, m21note.Note):  # pausas no soprano são raras, descarta a peça
            return None
        dur = float(n.quarterLength)
        if dur not in ALLOWED_DURATIONS:
            return None
        beat = round(float(n.beat) - 1.0, 2)  # 0.0 a 3.75
        rel = n.pitch.midi - TONIC_MIDI
        ferm = any(e.classes[0] == "Fermata" for e in n.expressions)
        tokens.append((rel, dur, beat, ferm))

        b = bass_notes.getElementAtOrBefore(n.offset)  # baixo que soa no início desta nota
        if b is None or not isinstance(b, m21note.Note):
            return None
        bass_rel.append(b.pitch.midi - TONIC_MIDI)

    if len(tokens) < 16:
        return None
    rel, dur, beat, _ = tokens[-1]
    tokens[-1] = (rel, dur, beat, True)  # a última nota sempre fecha uma frase

    return tokens, bass_rel


# ---------- CARREGAMENTO ----------

def load_corpus(use_cache: bool = True, verbose: bool = True):
    """Carrega o corpus, processando os corais na primeira vez e salvando o resultado em corpus/

    :param use_cache: usa o cache em corpus/ se ele existir
    :param verbose: mostra o progresso
    :return: (sequências do soprano, sequências do baixo, nomes das peças)
    """
    CACHE_DIR.mkdir(exist_ok=True)
    cache = CACHE_DIR / "bach_chorales_major.json"
    if use_cache and cache.exists():
        data = json.loads(cache.read_text())
        seqs = [[str_to_token(s) for s in seq] for seq in data["sequences"]]
        return seqs, data["bass"], data["pieces"]

    sequences, basses, names = [], [], []
    paths = corpus.getComposer("bach")
    seen_melodies = set()
    for i, path in enumerate(paths):
        try:
            score = corpus.parse(path)
            if len(score.parts) != 4:
                continue
            res = chorale_to_tokens(score)
        except Exception:  # alguns arquivos do corpus têm problemas de parsing
            continue
        if res is None:
            continue
        toks, bass_rel = res
        key_ = tuple(toks)
        if key_ in seen_melodies:  # vários corais harmonizam a mesma melodia
            continue
        seen_melodies.add(key_)
        sequences.append(toks)
        basses.append(bass_rel)
        names.append(Path(str(path)).stem)
        if verbose and len(sequences) % 25 == 0:
            print(f"  {len(sequences)} corais aceitos ({i + 1}/{len(paths)} arquivos lidos)")

    data = {
        "pieces": names,
        "sequences": [[token_to_str(t) for t in seq] for seq in sequences],
        "bass": basses,
    }
    cache.write_text(json.dumps(data))
    if verbose:
        print(f"Corpus: {len(sequences)} melodias de corais em modo maior.")
    return sequences, basses, names
