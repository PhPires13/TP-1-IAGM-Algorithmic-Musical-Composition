"""Converte os tokens gerados em MIDI / MusicXML e sintetiza um .wav simples para audição

O arquivo simbólico (.mid) é a saída principal
O .wav é gerado a partir dele por um sintetizador aditivo próprio
"""

from __future__ import annotations

from pathlib import Path

import mido
import numpy as np
from music21 import expressions, instrument, metadata, meter, note, stream, tempo
from scipy.io import wavfile

from .corpus import TONIC_MIDI

KEY_TONIC = {"major": TONIC_MIDI, "minor": TONIC_MIDI - 3}  # Dó4 ou Lá3


# ---------- PARTITURA ----------

def to_score(tokens, bass=None, mode: str = "major", bpm: int = 76, title: str = "Coral gerado") -> stream.Score:
    """Monta a partitura do music21 com o soprano e, se houver, o baixo

    :param tokens: melodia gerada
    :param bass: alturas do baixo (None para só a melodia)
    :param mode: "major" ou "minor"
    :param bpm: andamento
    :param title: título da partitura
    :return: partitura do music21
    """
    tonic = KEY_TONIC[mode]
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

    # ----- Baixo (mesmo ritmo do soprano)
    if bass is not None:
        bp = stream.Part(id="Baixo")
        bp.partName = "Baixo"
        bp.insert(0, instrument.Bass())
        bp.append(meter.TimeSignature("4/4"))
        if pickup:
            bp.append(note.Rest(quarterLength=pickup))
        for (rel, dur, _b, ferm), b in zip(tokens, bass):
            n = note.Note(tonic + b, quarterLength=dur)
            if ferm:
                n.expressions.append(expressions.Fermata())
            bp.append(n)
        score.insert(0, bp)
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


# ---------- SÍNTESE DE ÁUDIO ----------

def _midi_notes(path: Path):
    """Lê todas as notas de um arquivo MIDI

    :param path: caminho do .mid
    :return: lista de (início em s, fim em s, altura MIDI, velocidade)
    """
    mf = mido.MidiFile(str(path))
    notes, active = [], {}
    t = 0.0
    for msg in mf:  # iterar o MidiFile já converte ticks em segundos
        t += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            active[(msg.channel, msg.note)] = (t, msg.velocity)
        elif msg.type in ("note_off", "note_on"):  # note_on com velocidade 0 também desliga a nota
            start = active.pop((msg.channel, msg.note), None)
            if start is not None:
                notes.append((start[0], t, msg.note, start[1]))
    return notes


def synthesize(midi_path: Path, wav_path: Path, sr: int = 44100) -> Path:
    """Sintetiza um .wav a partir do .mid com timbre de órgão (soma de harmônicos) e uma reverberação simples

    :param midi_path: caminho do .mid
    :param wav_path: caminho do .wav de saída
    :param sr: taxa de amostragem
    :return: caminho do .wav
    """
    notes = _midi_notes(midi_path)
    total = max(end for _, end, _, _ in notes) + 1.5
    out = np.zeros(int(total * sr))
    harmonics = [(1, 1.0), (2, 0.45), (3, 0.25), (4, 0.12), (6, 0.05)]  # (harmônico, amplitude)
    for start, end, pitch_, vel in notes:
        dur = end - start
        n = int((dur + 0.25) * sr)  # 0.25 s de release
        t = np.arange(n) / sr
        f0 = 440.0 * 2 ** ((pitch_ - 69) / 12)
        tone = sum(a * np.sin(2 * np.pi * f0 * h * t) for h, a in harmonics if f0 * h < sr / 2)

        # ----- Envelope: ataque de 20 ms e decaimento exponencial após o fim da nota
        env = np.ones(n)
        att = int(0.02 * sr)
        env[:att] = np.linspace(0, 1, att)
        rel_start = int(dur * sr)
        env[rel_start:] = np.exp(-np.arange(n - rel_start) / (0.06 * sr))

        gain = (vel / 127) * (0.6 if pitch_ >= 55 else 0.45)  # baixo um pouco mais suave
        i0 = int(start * sr)
        out[i0:i0 + n] += gain * tone * env

    # reverberação simples: alguns ecos amortecidos para soar menos seco
    wet = out.copy()
    for delay, g in [(0.031, 0.35), (0.047, 0.28), (0.071, 0.2), (0.113, 0.12)]:
        d = int(delay * sr)
        wet[d:] += g * out[:-d]
    wet /= np.max(np.abs(wet)) + 1e-9
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(str(wav_path), sr, (wet * 0.9 * 32767).astype(np.int16))
    return wav_path
