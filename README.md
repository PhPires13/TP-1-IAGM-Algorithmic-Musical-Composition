# TP1 - Composição Musical Algorítmica com Cadeias de Markov

**DCC831 - IA Generativa para Música (UFMG, 2026/2)** - Pedro Pires

Sistema que gera **corais no estilo de J. S. Bach** com **cadeias de Markov de ordem *n*** aprendidas do corpus de corais de Bach do `music21`.

## Onde está cada item pedido no enunciado

| Item do enunciado | Onde está |
|---|---|
| Método escolhido (usado exclusivamente) | Cadeias de Markov: [`markov_music/markov.py`](markov_music/markov.py) (melodia) e [`markov_music/bass.py`](markov_music/bass.py) (baixo, também uma cadeia de Markov) |
| Saída simbólica reproduzível | `.mid` e `.musicxml` de cada peça. A mesma semente gera sempre a mesma peça |
| Restrição estilística | Coral no estilo de Bach: 4/4, *F* frases terminadas em fermata (padrão 4) e final na tônica, imposta durante a geração em [`markov_music/composer.py`](markov_music/composer.py) |
| Ordem do modelo e justificativa | Ordem *n* configurável (`--order`, padrão 3). A justificativa está no resumo (seções 4 e 5) |
| Origem das probabilidades de transição | Aprendidas de um corpus real (117 corais em modo maior e 125 em menor), por contagem com backoff |
| Trade-off ordem baixa x ordem alta | [`experiment.py`](experiment.py) gera a tabela e a figura em [`results/`](results/), discutidas no resumo |
| Várias músicas com a mesma configuração | Sementes diferentes (`--seed`, `--n`) |
| Variar pelo menos um hiperparâmetro | Ordem, temperatura, número de frases e modo maior/menor |
| Código-fonte, README e dependências | Este repositório, este arquivo e [`requirements.txt`](requirements.txt) |
| Resumo no formato ISMIR (template oficial 2026, 2 páginas + referências) | [`abstract.pdf`](abstract.pdf), compilado a partir de [`latex/`](latex/) |
| Pelo menos 3 músicas geradas, em áudio, com variação entre si | 6 peças em [`music/`](music/), cada uma com `.wav` (tabela abaixo e Tabela 1 do resumo) |

## Instalação

Requer Python 3.12 ou superior (testado com Python 3.14).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

O corpus de Bach já vem com o `music21`, então não é preciso baixar nenhum dataset.
O corpus processado fica salvo em [`corpus/`](corpus/). Sem essa pasta, ele é recriado na primeira execução (cerca de 1 minuto).

## Uso

```bash
python generate.py                                    # 3 peças: ordem 3, T = 1.0, 4 frases
python generate.py --order 1 --n 5 --seed 10          # ordem baixa (mais aleatória)
python generate.py --order 5 --temperature 1.5        # ordem alta, temperatura maior
python generate.py --mode minor --phrases 6           # corais em modo menor, 6 frases
```

| Parâmetro | Padrão | Descrição |
|---|---|---|
| `--order` | 3 | ordem *n* da cadeia (quantas notas anteriores formam o contexto) |
| `--temperature` | 1.0 | T < 1 favorece as transições mais comuns, T > 1 deixa a escolha mais uniforme |
| `--phrases` | 4 | número de frases (fermatas) da peça |
| `--mode` | major | treina com os corais em modo `major` ou `minor` |
| `--n`, `--seed` | 3, 0 | quantas peças gerar, a peça *i* usa a semente `seed + i` |
| `--no-bass` | - | gera só a melodia |
| `--no-audio` | - | não gera o `.wav` |

Cada peça fica em `outputs/<nome>/` com `.mid`, `.musicxml`, `.wav` (só para audição) e `.json` (tokens gerados e métricas).

## Reproduzir os resultados

```bash
./reproduce.sh
```

Gera as 6 peças de `music/` e roda `experiment.py`, que testa as ordens 1 a 6 e as temperaturas 0.5, 1.0 e 1.5, com 30 sementes cada.
O resumo pode ser recompilado com qualquer distribuição LaTeX, por exemplo `cd latex && tectonic ISMIR2026_template.tex`.

## Músicas geradas (`music/`)

O nome de cada pasta segue o padrão `modo_o<ordem>_t<temperatura>_p<frases>_s<semente>`.

| Pasta | Ordem | T | O que varia |
|---|---|---|---|
| `major_o3_t1_p4_s0` | 3 | 1.0 | configuração padrão |
| `major_o3_t1_p4_s1` | 3 | 1.0 | mesma configuração, outra semente |
| `major_o1_t1_p4_s0` | 1 | 1.0 | ordem baixa: genérica, sem direção melódica |
| `major_o5_t1_p4_s0` | 5 | 1.0 | ordem alta: copia 18 notas seguidas de um coral real |
| `major_o3_t1.5_p4_s0` | 3 | 1.5 | temperatura maior |
| `minor_o3_t1_p6_s0` | 3 | 1.0 | modo menor, 6 frases |

## Estrutura

```
abstract.pdf        resumo no formato ISMIR
latex/              fonte LaTeX do resumo (template oficial ISMIR 2026)
music/              as 6 peças geradas (.mid, .musicxml, .wav, .json)
results/            tabela e figura do experimento de ordem x temperatura
corpus/             corpus de Bach já processado (cache)
generate.py         gera peças pela linha de comando
experiment.py       experimento do trade-off entre ordem baixa e ordem alta
reproduce.sh        reproduz as peças e o experimento
markov_music/
  corpus.py         extrai e tokeniza as linhas de soprano e baixo dos corais
  markov.py         cadeia de Markov de ordem n: treino, backoff e temperatura
  composer.py       geração com as restrições de forma (frases, compasso, cadência)
  bass.py           cadeia de Markov condicional para a linha do baixo
  render.py         exporta MIDI/MusicXML e sintetiza o .wav a partir do MIDI
  metrics.py        métricas de memorização e novidade
```

Cada nota do soprano é um estado `(altura, duração, posição no compasso, fermata)`, com a altura em semitons a partir de Dó4 depois de transpor a peça para Dó maior (ou Lá menor).

## Uso de IA

O trabalho contou com o auxílio de IA durante o seu desenvolvimento.
Os módelos usados foram:
- Claude Code
  - Planejamento do projeto, ajuda teórica, suporte de código (ensinar, melhorias, bugs), melhoria da escrita, melhoria da formatação
  - (Infelizmente as sessões do Claude Code são puramente locais e não tem opção de compartilhamento de link, com isso pedi para o mesmo gerar um arquivo markdown com a transcrição da conversa em [`transcricao_sessao_IAGM_TP1.md`](transcricao_sessao_IAGM_TP1.md))
- Copilot
  - Completamento de código, completamento de comentários
  - (Não possui sessão apenas sugestões locais)
