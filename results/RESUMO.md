# Resumo dos resultados (E5 e E6)

Gerado por `src/analysis/estatistica.py` a partir de `results/summary.csv` e `results/e5/`. Não edite à mão.

Combinações medidas: borda 2 de 18; nuvem 9 de 9. Cenários em `results/summary.csv`: 33.

## Como ler estes números

- Tempos de borda medidos em ambiente EMULADO (QEMU, perfil rpi4b); não representam um Raspberry Pi.
- **Amostragem reduzida (decisão D8, altera o desenho da ATV 04):** cada combinação modelo × precisão × resolução foi medida uma vez, com 350 quadros (50 de aquecimento + 300 válidos). Os cenários de 5, 15 e 30 FPS são **derivados** dessas medições (quadro i disponível em i/fps), não medidos em execução própria.
- A comparação absoluta de latência borda (emulada) × nuvem (nativa) **não vale como resultado**. O resultado sólido da QP2 é a **banda de subida**: a nuvem precisa enviar o vídeo; a borda não envia nenhum quadro.
- Nuvem: rede emulada com `tc netem` (RTT 40 ms, subida 10 Mbit/s): valores assumidos que a equipe precisa justificar com fonte. Executada em paralelo com a coleta da borda.
- Energia: não calculada (sem potência de referência com fonte verificável em `configs/energia.yaml`).

## Qualidade (mAP@50 da classe pessoa, 350 imagens)

| parte | modelo | precisão | resolução da fonte | mAP@50 | precisão@0,5 | revocação@0,5 | F1@0,5 |
|---|---|---|---|---|---|---|---|
| borda | yolov8n | int8 | 320 | 0.676 | 0.9718 | 0.4329 | 0.5989 |
| borda | yolov8n | int8 | 480 | 0.7438 | 0.9493 | 0.4889 | 0.6454 |
| nuvem | efficientdet_lite0 | fp32 | 320 | 0.5057 | 0.8494 | 0.3652 | 0.5108 |
| nuvem | efficientdet_lite0 | fp32 | 480 | 0.5118 | 0.8527 | 0.3749 | 0.5208 |
| nuvem | efficientdet_lite0 | fp32 | 640 | 0.4981 | 0.8257 | 0.3662 | 0.5074 |
| nuvem | ssd_mobilenet_v1 | fp32 | 320 | 0.5924 | 0.9508 | 0.3923 | 0.5554 |
| nuvem | ssd_mobilenet_v1 | fp32 | 480 | 0.5954 | 0.9359 | 0.4232 | 0.5828 |
| nuvem | ssd_mobilenet_v1 | fp32 | 640 | 0.6001 | 0.9226 | 0.4261 | 0.5829 |
| nuvem | yolov8n | fp32 | 320 | 0.668 | 0.9609 | 0.4271 | 0.5913 |
| nuvem | yolov8n | fp32 | 480 | 0.745 | 0.9589 | 0.4957 | 0.6535 |
| nuvem | yolov8n | fp32 | 640 | 0.7611 | 0.9497 | 0.5295 | 0.6799 |

## Latência por combinação (quadros válidos; média, IC 95% e p95, em ms)

| parte | modelo | precisão | res. | e2e média | IC inf | IC sup | e2e p95 | inferência média | FPS sustentável |
|---|---|---|---|---|---|---|---|---|---|
| borda | yolov8n | int8 | 320 | 4003.097 | 3954.853 | 4051.342 | 4704.787 | 3968.512 | 0.2498 |
| borda | yolov8n | int8 | 480 | 8135.094 | 8036.909 | 8233.278 | 9685.667 | 8063.383 | 0.1229 |
| nuvem | efficientdet_lite0 | fp32 | 320 | 91.252 | 89.849 | 92.654 | 109.853 | 24.759 | 10.9587 |
| nuvem | efficientdet_lite0 | fp32 | 480 | 105.862 | 104.193 | 107.531 | 133.008 | 17.361 | 9.4463 |
| nuvem | efficientdet_lite0 | fp32 | 640 | 136.69 | 133.933 | 139.448 | 183.807 | 19.345 | 7.3158 |
| nuvem | ssd_mobilenet_v1 | fp32 | 320 | 86.584 | 85.237 | 87.93 | 106.126 | 18.842 | 11.5495 |
| nuvem | ssd_mobilenet_v1 | fp32 | 480 | 101.696 | 100.383 | 103.008 | 123.34 | 13.121 | 9.8333 |
| nuvem | ssd_mobilenet_v1 | fp32 | 640 | 135.553 | 132.825 | 138.282 | 181.282 | 16.619 | 7.3772 |
| nuvem | yolov8n | fp32 | 320 | 77.118 | 75.909 | 78.327 | 97.582 | 15.758 | 12.9672 |
| nuvem | yolov8n | fp32 | 480 | 110.857 | 108.903 | 112.812 | 148.443 | 26.909 | 9.0206 |
| nuvem | yolov8n | fp32 | 640 | 164.535 | 161.502 | 167.568 | 208.551 | 51.533 | 6.0777 |

## Banda de subida e fila por taxa da fonte (cenários derivados)

| parte | modelo | precisão | res. | FPS | subida (kbit/s) | fila média (ms) | descarte se ocupado |
|---|---|---|---|---|---|---|---|
| borda | yolov8n | int8 | 320 | 5 | 0.0 | 572506.101 | 0.9467 |
| borda | yolov8n | int8 | 320 | 15 | 0.0 | 592439.434 | 0.9767 |
| borda | yolov8n | int8 | 320 | 30 | 0.0 | 597422.767 | 0.9867 |
| borda | yolov8n | int8 | 480 | 5 | 0.0 | 1185561.581 | 0.97 |
| borda | yolov8n | int8 | 480 | 15 | 0.0 | 1205494.914 | 0.9867 |
| borda | yolov8n | int8 | 480 | 30 | 0.0 | 1210478.247 | 0.99 |
| nuvem | efficientdet_lite0 | fp32 | 320 | 5 | 829.4 | 0.0 | 0.0 |
| nuvem | efficientdet_lite0 | fp32 | 320 | 15 | 2488.3 | 3306.554 | 0.26 |
| nuvem | efficientdet_lite0 | fp32 | 320 | 30 | 4976.6 | 8289.887 | 0.6233 |
| nuvem | efficientdet_lite0 | fp32 | 480 | 5 | 1743.5 | 0.0 | 0.0 |
| nuvem | efficientdet_lite0 | fp32 | 480 | 15 | 5230.4 | 6002.751 | 0.3633 |
| nuvem | efficientdet_lite0 | fp32 | 480 | 30 | 10460.8 | 10986.084 | 0.6767 |
| nuvem | efficientdet_lite0 | fp32 | 640 | 5 | 2954.6 | 0.065 | 0.0 |
| nuvem | efficientdet_lite0 | fp32 | 640 | 15 | 8863.8 | 10328.792 | 0.5133 |
| nuvem | efficientdet_lite0 | fp32 | 640 | 30 | 17727.6 | 15312.126 | 0.7567 |
| nuvem | ssd_mobilenet_v1 | fp32 | 320 | 5 | 829.4 | 0.0 | 0.0 |
| nuvem | ssd_mobilenet_v1 | fp32 | 320 | 15 | 2488.3 | 3247.664 | 0.22 |
| nuvem | ssd_mobilenet_v1 | fp32 | 320 | 30 | 4976.6 | 8230.997 | 0.6067 |
| nuvem | ssd_mobilenet_v1 | fp32 | 480 | 5 | 1743.5 | 0.0 | 0.0 |
| nuvem | ssd_mobilenet_v1 | fp32 | 480 | 15 | 5230.4 | 5192.421 | 0.3467 |
| nuvem | ssd_mobilenet_v1 | fp32 | 480 | 30 | 10460.8 | 10175.754 | 0.6633 |
| nuvem | ssd_mobilenet_v1 | fp32 | 640 | 5 | 2954.6 | 0.069 | 0.0 |
| nuvem | ssd_mobilenet_v1 | fp32 | 640 | 15 | 8863.8 | 10171.411 | 0.5033 |
| nuvem | ssd_mobilenet_v1 | fp32 | 640 | 30 | 17727.6 | 15154.745 | 0.7433 |
| nuvem | yolov8n | fp32 | 320 | 5 | 829.4 | 0.0 | 0.0 |
| nuvem | yolov8n | fp32 | 320 | 15 | 2488.3 | 1401.256 | 0.13 |
| nuvem | yolov8n | fp32 | 320 | 30 | 4976.6 | 6384.589 | 0.56 |
| nuvem | yolov8n | fp32 | 480 | 5 | 1743.5 | 0.0 | 0.0 |
| nuvem | yolov8n | fp32 | 480 | 15 | 5230.4 | 6776.65 | 0.3933 |
| nuvem | yolov8n | fp32 | 480 | 30 | 10460.8 | 11759.983 | 0.69 |
| nuvem | yolov8n | fp32 | 640 | 5 | 2954.6 | 1.567 | 0.0 |
| nuvem | yolov8n | fp32 | 640 | 15 | 8863.8 | 14820.18 | 0.5933 |
| nuvem | yolov8n | fp32 | 640 | 30 | 17727.6 | 19803.513 | 0.8 |

## Testes pareados FP32 × INT8 na borda

_Sem pares completos ainda (faltam combinações FP32 da borda)._

## Testes pareados borda × nuvem (registro; não vale como resultado absoluto)

_Sem pares completos ainda (faltam combinações FP32 da borda)._

## Figuras

- `figures/e6_borda_latencia.pdf` e `.png`
- `figures/e6_banda_subida.pdf` e `.png`
- `figures/e6_map50.pdf` e `.png`
- `figures/e6_borda_descarte.pdf` e `.png`

## Limitações

- Emulação QEMU: os tempos de borda servem para comparação relativa (FP32 × INT8, entre modelos e resoluções), não como tempo de um Raspberry Pi. A biblioteca Python do LiteRT é cerca de 10× mais lenta que o `benchmark_model` sob o QEMU (D9).
- Cenários de FPS derivados e amostragem reduzida (D8).
- Conjunto de teste do COCO val2017; não há gravações residenciais (D6).
- INT8 do YOLOv8n é híbrido (D2); Edge TPU avaliado só pelo relatório do compilador (E4).
- Rede da nuvem emulada com valores assumidos (D5); protocolo JPEG/HTTP no lugar de RTSP/WebRTC.
