# Resumo dos resultados (E5 e E6)

Gerado por `src/analysis/estatistica.py` a partir de `results/summary.csv` e `results/e5/`. Não edite à mão.

Combinações medidas: borda 18 de 18; nuvem 9 de 9. Cenários em `results/summary.csv`: 81.

## Como ler estes números

- Tempos de borda medidos em ARM64 nativo (VM Oracle A1, Neoverse-N1, 2 núcleos); não representam um Raspberry Pi.
- **Amostragem reduzida (decisão D8, altera o desenho da ATV 04):** cada combinação modelo × precisão × resolução foi medida uma vez, com 350 quadros (50 de aquecimento + 300 válidos). Os cenários de 5, 15 e 30 FPS são **derivados** dessas medições (quadro i disponível em i/fps), não medidos em execução própria.
- A latência borda × nuvem compara um servidor ARM de 2 núcleos com um servidor x86 e **não representa um Raspberry Pi**. O resultado sólido da QP2 é a **banda de subida**: a nuvem precisa enviar o vídeo; a borda não envia nenhum quadro.
- Nuvem: rede emulada com `tc netem` (RTT 40 ms, subida 10 Mbit/s): valores assumidos que a equipe precisa justificar com fonte. Executada em paralelo com a coleta da borda.
- Memória: `rss_mb_max` inclui os 350 quadros da fonte pré-carregados; `rss_mb_max_sem_quadros` desconta esse volume (350 × res × res × 3 bytes).
- Energia: não calculada (sem potência de referência com fonte verificável em `configs/energia.yaml`).

## Qualidade (mAP@50 da classe pessoa, 350 imagens)

| parte | modelo | precisão | resolução da fonte | mAP@50 | precisão@0,5 | revocação@0,5 | F1@0,5 |
|---|---|---|---|---|---|---|---|
| borda | efficientdet_lite0 | fp32 | 320 | 0.5142 | 0.8316 | 0.3768 | 0.5186 |
| borda | efficientdet_lite0 | fp32 | 480 | 0.5121 | 0.8377 | 0.3739 | 0.517 |
| borda | efficientdet_lite0 | fp32 | 640 | 0.5074 | 0.8355 | 0.3729 | 0.5157 |
| borda | efficientdet_lite0 | int8 | 320 | 0.4724 | 0.8341 | 0.3594 | 0.5024 |
| borda | efficientdet_lite0 | int8 | 480 | 0.4679 | 0.8277 | 0.3527 | 0.4946 |
| borda | efficientdet_lite0 | int8 | 640 | 0.4695 | 0.8269 | 0.3507 | 0.4925 |
| borda | ssd_mobilenet_v1 | fp32 | 320 | 0.6033 | 0.9228 | 0.4386 | 0.5946 |
| borda | ssd_mobilenet_v1 | fp32 | 480 | 0.6026 | 0.9185 | 0.4464 | 0.6008 |
| borda | ssd_mobilenet_v1 | fp32 | 640 | 0.6022 | 0.9103 | 0.4512 | 0.6034 |
| borda | ssd_mobilenet_v1 | int8 | 320 | 0.6048 | 0.9002 | 0.4531 | 0.6028 |
| borda | ssd_mobilenet_v1 | int8 | 480 | 0.6054 | 0.8987 | 0.4628 | 0.611 |
| borda | ssd_mobilenet_v1 | int8 | 640 | 0.6103 | 0.897 | 0.4628 | 0.6106 |
| borda | yolov8n | fp32 | 320 | 0.6791 | 0.9658 | 0.4367 | 0.6015 |
| borda | yolov8n | fp32 | 480 | 0.7504 | 0.9534 | 0.514 | 0.6679 |
| borda | yolov8n | fp32 | 640 | 0.7701 | 0.9556 | 0.5401 | 0.6901 |
| borda | yolov8n | int8 | 320 | 0.676 | 0.9718 | 0.4329 | 0.5989 |
| borda | yolov8n | int8 | 480 | 0.7438 | 0.9493 | 0.4889 | 0.6454 |
| borda | yolov8n | int8 | 640 | 0.7605 | 0.9621 | 0.515 | 0.6709 |
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
| borda | efficientdet_lite0 | fp32 | 320 | 37.707 | 37.506 | 37.907 | 39.898 | 33.683 | 26.5205 |
| borda | efficientdet_lite0 | fp32 | 480 | 39.942 | 39.768 | 40.117 | 42.298 | 33.616 | 25.036 |
| borda | efficientdet_lite0 | fp32 | 640 | 40.687 | 40.558 | 40.815 | 42.257 | 33.463 | 24.5781 |
| borda | efficientdet_lite0 | int8 | 320 | 22.463 | 22.364 | 22.561 | 23.553 | 14.394 | 44.5186 |
| borda | efficientdet_lite0 | int8 | 480 | 24.944 | 24.839 | 25.05 | 25.99 | 14.342 | 40.0893 |
| borda | efficientdet_lite0 | int8 | 640 | 25.581 | 25.469 | 25.693 | 26.612 | 14.36 | 39.0915 |
| borda | ssd_mobilenet_v1 | fp32 | 320 | 40.357 | 40.3 | 40.415 | 41.052 | 34.786 | 24.7786 |
| borda | ssd_mobilenet_v1 | fp32 | 480 | 41.125 | 41.024 | 41.227 | 42.541 | 34.826 | 24.3158 |
| borda | ssd_mobilenet_v1 | fp32 | 640 | 42.063 | 41.953 | 42.172 | 43.192 | 34.832 | 23.7741 |
| borda | ssd_mobilenet_v1 | int8 | 320 | 17.191 | 17.138 | 17.244 | 17.597 | 10.965 | 58.171 |
| borda | ssd_mobilenet_v1 | int8 | 480 | 17.802 | 17.752 | 17.852 | 18.261 | 10.963 | 56.1734 |
| borda | ssd_mobilenet_v1 | int8 | 640 | 18.98 | 18.912 | 19.048 | 19.724 | 10.966 | 52.6867 |
| borda | yolov8n | fp32 | 320 | 34.724 | 34.637 | 34.811 | 35.467 | 33.692 | 28.7986 |
| borda | yolov8n | fp32 | 480 | 77.01 | 76.864 | 77.155 | 79.058 | 74.14 | 12.9854 |
| borda | yolov8n | fp32 | 640 | 136.506 | 136.323 | 136.688 | 139.599 | 132.068 | 7.3257 |
| borda | yolov8n | int8 | 320 | 11.178 | 11.136 | 11.221 | 11.838 | 10.15 | 89.4599 |
| borda | yolov8n | int8 | 480 | 24.922 | 24.82 | 25.023 | 26.203 | 21.934 | 40.1256 |
| borda | yolov8n | int8 | 640 | 42.834 | 42.727 | 42.941 | 44.299 | 38.475 | 23.346 |
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
| borda | efficientdet_lite0 | fp32 | 320 | 5 | 0.0 | 0.0 | 0.0 |
| borda | efficientdet_lite0 | fp32 | 320 | 15 | 0.0 | 0.0 | 0.0 |
| borda | efficientdet_lite0 | fp32 | 320 | 30 | 0.0 | 631.778 | 0.1133 |
| borda | efficientdet_lite0 | fp32 | 480 | 5 | 0.0 | 0.0 | 0.0 |
| borda | efficientdet_lite0 | fp32 | 480 | 15 | 0.0 | 0.0 | 0.0 |
| borda | efficientdet_lite0 | fp32 | 480 | 30 | 0.0 | 993.034 | 0.1633 |
| borda | efficientdet_lite0 | fp32 | 640 | 5 | 0.0 | 0.0 | 0.0 |
| borda | efficientdet_lite0 | fp32 | 640 | 15 | 0.0 | 0.0 | 0.0 |
| borda | efficientdet_lite0 | fp32 | 640 | 30 | 0.0 | 1093.306 | 0.1767 |
| borda | efficientdet_lite0 | int8 | 320 | 5 | 0.0 | 0.0 | 0.0 |
| borda | efficientdet_lite0 | int8 | 320 | 15 | 0.0 | 0.0 | 0.0 |
| borda | efficientdet_lite0 | int8 | 320 | 30 | 0.0 | 0.0 | 0.0 |
| borda | efficientdet_lite0 | int8 | 480 | 5 | 0.0 | 0.0 | 0.0 |
| borda | efficientdet_lite0 | int8 | 480 | 15 | 0.0 | 0.0 | 0.0 |
| borda | efficientdet_lite0 | int8 | 480 | 30 | 0.0 | 0.0 | 0.0 |
| borda | efficientdet_lite0 | int8 | 640 | 5 | 0.0 | 0.0 | 0.0 |
| borda | efficientdet_lite0 | int8 | 640 | 15 | 0.0 | 0.0 | 0.0 |
| borda | efficientdet_lite0 | int8 | 640 | 30 | 0.0 | 0.0 | 0.0 |
| borda | ssd_mobilenet_v1 | fp32 | 320 | 5 | 0.0 | 0.0 | 0.0 |
| borda | ssd_mobilenet_v1 | fp32 | 320 | 15 | 0.0 | 0.0 | 0.0 |
| borda | ssd_mobilenet_v1 | fp32 | 320 | 30 | 0.0 | 1058.403 | 0.17 |
| borda | ssd_mobilenet_v1 | fp32 | 480 | 5 | 0.0 | 0.0 | 0.0 |
| borda | ssd_mobilenet_v1 | fp32 | 480 | 15 | 0.0 | 0.0 | 0.0 |
| borda | ssd_mobilenet_v1 | fp32 | 480 | 30 | 0.0 | 1150.182 | 0.1867 |
| borda | ssd_mobilenet_v1 | fp32 | 640 | 5 | 0.0 | 0.0 | 0.0 |
| borda | ssd_mobilenet_v1 | fp32 | 640 | 15 | 0.0 | 0.0 | 0.0 |
| borda | ssd_mobilenet_v1 | fp32 | 640 | 30 | 0.0 | 1295.161 | 0.2033 |
| borda | ssd_mobilenet_v1 | int8 | 320 | 5 | 0.0 | 0.0 | 0.0 |
| borda | ssd_mobilenet_v1 | int8 | 320 | 15 | 0.0 | 0.0 | 0.0 |
| borda | ssd_mobilenet_v1 | int8 | 320 | 30 | 0.0 | 0.0 | 0.0 |
| borda | ssd_mobilenet_v1 | int8 | 480 | 5 | 0.0 | 0.0 | 0.0 |
| borda | ssd_mobilenet_v1 | int8 | 480 | 15 | 0.0 | 0.0 | 0.0 |
| borda | ssd_mobilenet_v1 | int8 | 480 | 30 | 0.0 | 0.0 | 0.0 |
| borda | ssd_mobilenet_v1 | int8 | 640 | 5 | 0.0 | 0.0 | 0.0 |
| borda | ssd_mobilenet_v1 | int8 | 640 | 15 | 0.0 | 0.0 | 0.0 |
| borda | ssd_mobilenet_v1 | int8 | 640 | 30 | 0.0 | 0.0 | 0.0 |
| borda | yolov8n | fp32 | 320 | 5 | 0.0 | 0.0 | 0.0 |
| borda | yolov8n | fp32 | 320 | 15 | 0.0 | 0.0 | 0.0 |
| borda | yolov8n | fp32 | 320 | 30 | 0.0 | 206.455 | 0.0367 |
| borda | yolov8n | fp32 | 480 | 5 | 0.0 | 0.0 | 0.0 |
| borda | yolov8n | fp32 | 480 | 15 | 0.0 | 1529.452 | 0.1333 |
| borda | yolov8n | fp32 | 480 | 30 | 0.0 | 6512.785 | 0.5633 |
| borda | yolov8n | fp32 | 640 | 5 | 0.0 | 0.0 | 0.0 |
| borda | yolov8n | fp32 | 640 | 15 | 0.0 | 10438.458 | 0.5067 |
| borda | yolov8n | fp32 | 640 | 30 | 0.0 | 15421.791 | 0.75 |
| borda | yolov8n | int8 | 320 | 5 | 0.0 | 0.0 | 0.0 |
| borda | yolov8n | int8 | 320 | 15 | 0.0 | 0.0 | 0.0 |
| borda | yolov8n | int8 | 320 | 30 | 0.0 | 0.0 | 0.0 |
| borda | yolov8n | int8 | 480 | 5 | 0.0 | 0.0 | 0.0 |
| borda | yolov8n | int8 | 480 | 15 | 0.0 | 0.0 | 0.0 |
| borda | yolov8n | int8 | 480 | 30 | 0.0 | 0.0 | 0.0 |
| borda | yolov8n | int8 | 640 | 5 | 0.0 | 0.0 | 0.0 |
| borda | yolov8n | int8 | 640 | 15 | 0.0 | 0.0 | 0.0 |
| borda | yolov8n | int8 | 640 | 30 | 0.0 | 1420.061 | 0.22 |
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

| modelo | res. | métrica | n | média FP32 | média INT8 | FP32/INT8 | Shapiro p | teste | p | p < 0,05 |
|---|---|---|---|---|---|---|---|---|---|---|
| efficientdet_lite0 | 320 | t_e2e_ms | 300 | 37.707 | 22.463 | 1.6786 | 8.719e-30 | Wilcoxon pareado | 6.083e-51 | True |
| efficientdet_lite0 | 320 | t_infer_ms | 300 | 33.683 | 14.394 | 2.3401 | 8.427e-31 | Wilcoxon pareado | 6.083e-51 | True |
| efficientdet_lite0 | 480 | t_e2e_ms | 300 | 39.942 | 24.944 | 1.6013 | 1.82e-26 | Wilcoxon pareado | 6.083e-51 | True |
| efficientdet_lite0 | 480 | t_infer_ms | 300 | 33.616 | 14.342 | 2.344 | 3.163e-27 | Wilcoxon pareado | 6.083e-51 | True |
| efficientdet_lite0 | 640 | t_e2e_ms | 300 | 40.687 | 25.581 | 1.5905 | 2.912e-26 | Wilcoxon pareado | 6.083e-51 | True |
| efficientdet_lite0 | 640 | t_infer_ms | 300 | 33.463 | 14.36 | 2.3302 | 1.081e-28 | Wilcoxon pareado | 6.083e-51 | True |
| ssd_mobilenet_v1 | 320 | t_e2e_ms | 300 | 40.357 | 17.191 | 2.3476 | 1.883e-19 | Wilcoxon pareado | 6.083e-51 | True |
| ssd_mobilenet_v1 | 320 | t_infer_ms | 300 | 34.786 | 10.965 | 3.1725 | 1.456e-20 | Wilcoxon pareado | 6.083e-51 | True |
| ssd_mobilenet_v1 | 480 | t_e2e_ms | 300 | 41.125 | 17.802 | 2.3102 | 1.514e-20 | Wilcoxon pareado | 6.083e-51 | True |
| ssd_mobilenet_v1 | 480 | t_infer_ms | 300 | 34.826 | 10.963 | 3.1768 | 6.877e-25 | Wilcoxon pareado | 6.082e-51 | True |
| ssd_mobilenet_v1 | 640 | t_e2e_ms | 300 | 42.063 | 18.98 | 2.2161 | 6.917e-21 | Wilcoxon pareado | 6.083e-51 | True |
| ssd_mobilenet_v1 | 640 | t_infer_ms | 300 | 34.832 | 10.966 | 3.1765 | 1.331e-28 | Wilcoxon pareado | 6.083e-51 | True |
| yolov8n | 320 | t_e2e_ms | 300 | 34.724 | 11.178 | 3.1064 | 3.023e-30 | Wilcoxon pareado | 6.083e-51 | True |
| yolov8n | 320 | t_infer_ms | 300 | 33.692 | 10.15 | 3.3194 | 1.437e-30 | Wilcoxon pareado | 6.082e-51 | True |
| yolov8n | 480 | t_e2e_ms | 300 | 77.01 | 24.922 | 3.0901 | 3.076e-20 | Wilcoxon pareado | 6.083e-51 | True |
| yolov8n | 480 | t_infer_ms | 300 | 74.14 | 21.934 | 3.3801 | 7.646e-21 | Wilcoxon pareado | 6.083e-51 | True |
| yolov8n | 640 | t_e2e_ms | 300 | 136.506 | 42.834 | 3.1869 | 8.664e-07 | Wilcoxon pareado | 6.083e-51 | True |
| yolov8n | 640 | t_infer_ms | 300 | 132.068 | 38.475 | 3.4326 | 3.51e-15 | Wilcoxon pareado | 6.083e-51 | True |

## Testes pareados borda × nuvem (servidor ARM × servidor x86; não representa um Raspberry Pi)

| modelo | res. | métrica | n | média borda | média nuvem | teste | p |
|---|---|---|---|---|---|---|---|
| efficientdet_lite0 | 320 | t_e2e_ms | 300 | 37.707 | 91.252 | Wilcoxon pareado | 6.084e-51 |
| efficientdet_lite0 | 320 | t_infer_ms | 300 | 33.683 | 24.759 | Wilcoxon pareado | 1.459e-30 |
| efficientdet_lite0 | 480 | t_e2e_ms | 300 | 39.942 | 105.862 | Wilcoxon pareado | 6.084e-51 |
| efficientdet_lite0 | 480 | t_infer_ms | 300 | 33.616 | 17.361 | Wilcoxon pareado | 1.414e-48 |
| efficientdet_lite0 | 640 | t_e2e_ms | 300 | 40.687 | 136.69 | Wilcoxon pareado | 6.084e-51 |
| efficientdet_lite0 | 640 | t_infer_ms | 300 | 33.463 | 19.345 | Wilcoxon pareado | 4.974e-46 |
| ssd_mobilenet_v1 | 320 | t_e2e_ms | 300 | 40.357 | 86.584 | Wilcoxon pareado | 6.084e-51 |
| ssd_mobilenet_v1 | 320 | t_infer_ms | 300 | 34.786 | 18.842 | Wilcoxon pareado | 9.358e-48 |
| ssd_mobilenet_v1 | 480 | t_e2e_ms | 300 | 41.125 | 101.696 | Wilcoxon pareado | 6.084e-51 |
| ssd_mobilenet_v1 | 480 | t_infer_ms | 300 | 34.826 | 13.121 | Wilcoxon pareado | 9.453e-51 |
| ssd_mobilenet_v1 | 640 | t_e2e_ms | 300 | 42.063 | 135.553 | Wilcoxon pareado | 6.084e-51 |
| ssd_mobilenet_v1 | 640 | t_infer_ms | 300 | 34.832 | 16.619 | Wilcoxon pareado | 9.009e-49 |
| yolov8n | 320 | t_e2e_ms | 300 | 34.724 | 77.118 | Wilcoxon pareado | 6.084e-51 |
| yolov8n | 320 | t_infer_ms | 300 | 33.692 | 15.758 | Wilcoxon pareado | 2.937e-49 |
| yolov8n | 480 | t_e2e_ms | 300 | 77.01 | 110.857 | Wilcoxon pareado | 6.084e-51 |
| yolov8n | 480 | t_infer_ms | 300 | 74.14 | 26.909 | Wilcoxon pareado | 6.269e-51 |
| yolov8n | 640 | t_e2e_ms | 300 | 136.506 | 164.535 | Wilcoxon pareado | 2.184e-38 |
| yolov8n | 640 | t_infer_ms | 300 | 132.068 | 51.533 | Wilcoxon pareado | 6.145e-51 |

## Figuras

- `figures/e6_borda_latencia.pdf` e `.png`
- `figures/e6_banda_subida.pdf` e `.png`
- `figures/e6_map50.pdf` e `.png`
- `figures/e6_borda_descarte.pdf` e `.png`

## Limitações

- Borda em ARM64 nativo num servidor Neoverse-N1 com 2 núcleos (D10): os tempos servem para comparação relativa (FP32 × INT8, entre modelos e resoluções), não como tempo de um Raspberry Pi (Cortex-A72/A76, 4 núcleos). Uma coleta parcial anterior sob emulação QEMU fica em `results/e5/anexo_emulado/` só como comparação (D9).
- Cenários de FPS derivados e amostragem reduzida (D8).
- Conjunto de teste do COCO val2017; não há gravações residenciais (D6).
- INT8 do YOLOv8n é híbrido (D2); Edge TPU avaliado só pelo relatório do compilador (E4).
- Rede da nuvem emulada com valores assumidos (D5); protocolo JPEG/HTTP no lugar de RTSP/WebRTC.
