# Demonstração no macOS (Apple Silicon)

Roda o projeto num Mac, sem Docker, para mostrar em aula o fluxo inteiro: modelos pré-treinados,
quantização FP32 → INT8, mAP@50, latência e detecção ao vivo na webcam. Testado num MacBook com
Apple M5, macOS 26.6.

Os números que aparecem na demonstração são medidos na hora, neste Mac, ou lidos dos arquivos de
resultados do repositório (`results/e5/`). **Os tempos do Mac não substituem os do artigo**, que
foram medidos num servidor ARM64 Neoverse-N1 de 2 núcleos (decisão D10).

## Instalação (uma vez, ~5 min; ~2 min ao refazer com os downloads em cache)

```bash
git clone https://github.com/joaoleaogf/deteccao-pessoas-borda.git
cd deteccao-pessoas-borda
bash scripts/setup_macos.sh
```

Não pede senha nem instala nada no sistema. Precisa só do `git` e do `python3` das Command Line
Tools (`xcode-select --install`, se faltarem). O script:

- instala o `uv` 0.11.32 em `.venv-uv` e, com ele, o Python 3.12 em `~/.local/share/uv`;
- cria `.venv` (inferência e demonstração), `.venv-export` (Ultralytics, ai-edge-quantizer) e
  `.venv-tf` (TensorFlow) com as versões exatas de `requirements/macos-*.lock.txt`;
- roda os scripts do próprio projeto (`src/prepare/`): baixa as origens conferindo o sha256, gera os
  10 modelos `.tflite` e monta o conjunto de teste (350 imagens do COCO val2017 com pessoa).

`--do-zero` refaz ambientes e modelos; `--so-ambiente` para depois dos ambientes.

## Roteiro da aula

```bash
bash demo/roteiro.sh
```

Abre um menu; cada etapa também roda sozinha (`bash demo/roteiro.sh 2`). Tempos medidos no M5:

| Etapa | O que mostra | Tempo |
|---|---|---|
| 1 | De onde vem cada modelo e conferência do sha256 | ~10 s |
| 2 | Quantização FP32 → INT8 refeita no Mac, com tamanho antes e depois (`--rapido`: só EfficientDet) | ~1 min (~15 s) |
| 3 | mAP@50 da classe pessoa em 100 imagens, ao lado do valor do artigo (`--completo`: 350 imagens, 3 resoluções) | ~5 s (~1 min) |
| 4 | Latência FP32 × INT8 das 18 combinações neste Mac, ao lado da do artigo | ~10 s |
| 5 | Ao vivo na webcam | — |
| 6 | Ao vivo com as imagens COCO (reserva se a câmera falhar) | — |

### O que responder sobre "treinamento"

O projeto **não treina modelos**. Os três detectores vêm pré-treinados no COCO (80 classes, inclusive
pessoa): YOLOv8n da Ultralytics, SSD-MobileNet V1 do TF1 Detection Model Zoo e EfficientDet-Lite0 do
MediaPipe. O trabalho do projeto é converter, **quantizar** (quantização pós-treinamento, calibrada nas
128 imagens do COCO128), medir e avaliar. Nenhum INT8 é baixado pronto:

- **SSD-MobileNet V1**: TFLiteConverter com conjunto representativo, inteiro total (entrada e saída uint8);
- **EfficientDet-Lite0**: ai-edge-quantizer, inteiro total (int8);
- **YOLOv8n**: exportador oficial da Ultralytics com `quantize=8`, que deixa entrada, saída e cabeça em
  float32 de propósito (INT8 "híbrido", decisão D2).

Os INT8 gerados no Mac não são idênticos byte a byte aos do artigo, e o export INT8 do YOLOv8n muda um
pouco a cada execução; por isso o mAP@50 dos INT8 pode diferir alguns milésimos do publicado. Os FP32 do
SSD e do EfficientDet saem idênticos (mesmo sha256 de `results/modelos.csv`), e com as 350 imagens o mAP
dos FP32 no Mac é igual ao do artigo.

## Demonstração ao vivo

```bash
.venv/bin/python demo/demo_ao_vivo.py                 # webcam
.venv/bin/python demo/demo_ao_vivo.py --imagens       # reserva: imagens COCO do projeto
.venv/bin/python demo/demo_ao_vivo.py --video aula.mp4
```

| Tecla | Ação |
|---|---|
| `m` ou `1` `2` `3` | troca o modelo |
| `i` | alterna FP32 / INT8 |
| `r` | troca a resolução da fonte (320 → 480 → 640) |
| espaço | pausa |
| `q` ou Esc | sai |

Na tela: modelo, precisão, resolução da fonte e da entrada do modelo, latência por quadro (pré +
inferência + pós, média dos últimos 30 quadros), FPS sustentável (1000 / latência), FPS da tela (inclui
câmera e desenho, limitado pela câmera) e, para comparação, a latência e o mAP@50 da mesma combinação
no artigo. O quadro passa pelo mesmo caminho da coleta: redimensionado para res × res (D1) e processado
por `src/bench/deteccao.py`. O LiteRT usa 2 threads, como na coleta do artigo (`--threads` muda).

Medição curta, sem janela:

```bash
.venv/bin/python demo/demo_ao_vivo.py --benchmark            # 60 imagens por combinação
.venv/bin/python demo/demo_ao_vivo.py --benchmark --salvar   # grava CSV em results/mac/ (fora do git)
```

## Se a câmera falhar

O macOS só libera a câmera para o app de onde o comando foi rodado (Terminal, iTerm, VS Code).

1. Rode uma vez `bash demo/roteiro.sh 5` **antes da aula**, no Terminal, e clique em **Permitir**.
2. Se não aparecer o pedido ou a mensagem "não consegui abrir a webcam" continuar: Ajustes do Sistema →
   Privacidade e Segurança → Câmera → ligue o Terminal, feche o Terminal (Cmd+Q) e abra de novo.
3. Outra câmera (por exemplo um iPhone via Continuidade): `--camera 1`.
4. Reserva sem câmera: `bash demo/roteiro.sh 6` (imagens COCO) ou `--video arquivo.mp4`.
