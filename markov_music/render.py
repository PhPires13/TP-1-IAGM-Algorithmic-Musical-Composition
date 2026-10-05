"""Converte os tokens gerados em partitura e grava em MIDI / MusicXML

O arquivo simbólico (.mid) é a saída principal
"""

from __future__ import annotations

from pathlib import Path

from music21 import expressions, instrument, metadata, meter, note, stream, tempo

from .corpus import TONIC_MIDI


# ---------- PARTITURA ----------

def to_score(tokens, bpm: int = 76, title: str = "Coral gerado") -> stream.Score:
    """Monta a partitura do music21 com o soprano

    :param tokens: melodia gerada
    :param bpm: andamento
    :param title: título da partitura
    :return: partitura do music21
    """
    tonic = TONIC_MIDI
    score = stream.Score()
    score.metadata = metadata.Metadata(title=title, composer="Cadeia de Markov (estilo J. S. Bach)")

    pickup = tokens[0][2]  # posição métrica da primeira nota (anacruse)

    # ----- Soprano
    sop = stream.Part(id="Soprano")
    sop.partName = "Soprano"
    sop.insert(0, instrument.Soprano())
    sop.append(tempo.MetronomeMark(number=bpm))
    sop.append(meter.TimeSignature("4/4"))
    if pickup:
        sop.append(note.Rest(quarterLength=pickup))
    for rel, dur, _beat, ferm in tokens:
        n = note.Note(tonic + rel, quarterLength=dur)
        if ferm:
            n.expressions.append(expressions.Fermata())
        sop.append(n)
    score.insert(0, sop)
    return score


def write_symbolic(score: stream.Score, out_base: Path) -> dict:
    """Grava a partitura em .mid e .musicxml

    :param score: partitura do music21
    :param out_base: caminho sem extensão
    :return: dicionário {"midi": caminho, "musicxml": caminho}
    """
    out_base.parent.mkdir(parents=True, exist_ok=True)
    mid = out_base.with_suffix(".mid")
    xml = out_base.with_suffix(".musicxml")
    score.write("midi", fp=str(mid))
    score.write("musicxml", fp=str(xml))
    return {"midi": mid, "musicxml": xml}
