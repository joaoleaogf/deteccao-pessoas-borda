# Plano da E5 (coleta) e da E6 (análise)

Escrito em 16/11/2026. As decisões que este plano segue estão em `docs/decisoes.md` (D1, D2, D4 a D8).

## O que é medido

| Parte | Onde roda | Unidade medida | Quantidade |
|---|---|---|---|
| Borda | contêiner `borda-arm64` (QEMU, perfil `rpi4b`) | 18 combinações modelo × precisão × resolução da fonte | 350 quadros cada (50 de aquecimento) |
| Nuvem | 2 contêineres linux/amd64 (cliente e servidor) numa rede Docker com `tc netem` | 9 combinações modelo × resolução (FP32) | 350 quadros cada (50 de aquecimento) |
| Qualidade | x86 (`borda-prep`) a partir das detecções salvas | 18 combinações (borda) e 9 (nuvem) | 350 imagens |

Cada combinação roda em um processo novo, um quadro depois do outro, sem ritmo de câmera. Os 54
cenários de borda e os 27 de nuvem (5, 15 e 30 FPS) são **derivados** dessas medições:
o quadro i fica disponível em i/fps; o início do processamento é o maior entre a disponibilidade e o fim
do quadro anterior; `t_fila_ms` é a espera; nenhum quadro é descartado (pareamento por `frame_idx`), e
uma coluna à parte conta os quadros que uma política de "descartar se ocupado" teria perdido.

## Colunas por quadro

- Borda: `t_pre_ms`, `t_infer_ms`, `t_post_ms`, `t_e2e_ms` = pre + infer + post; CPU do processo e
  memória (RSS) a cada quadro.
- Nuvem: `t_codif_ms`, `bytes_jpeg`, `t_transmissao_ms`, `t_srv_decod_ms`, `t_pre_ms`, `t_infer_ms`,
  `t_post_ms`, `t_retorno_ms`, `t_e2e_ms` (soma de todos). O relógio é o mesmo nos dois contêineres
  (mesmo kernel do Docker Desktop), por isso ida e volta são medidas separadamente.
- Cenários derivados: `t_fila_ms` em coluna própria, fora de `t_e2e_ms`.

## Execução

- `e5.ps1` / `e5.sh`: monta o conjunto de teste, valida os decodificadores no x86, roda a nuvem e depois
  a borda (INT8 primeiro), destacado (`docker run -d`) e retomável: combinação com arquivo completo
  não roda de novo. Cada combinação grava um manifesto (data, versões, perfil, sha256 do modelo,
  parâmetros de rede).
- `e6.ps1` / `e6.sh`: deriva os cenários, calcula mAP e F1, faz a estatística e as figuras e escreve
  `results/RESUMO.md`.

## Análise (E6)

- Descritiva por cenário: média, desvio padrão, mediana, IC 95% da média (t de Student), p95.
- Comparações pareadas por `frame_idx`: FP32 × INT8 (mesmo modelo e resolução) e borda × nuvem (mesmo
  modelo FP32 e resolução). Shapiro-Wilk nas diferenças; t pareado se normal, senão Wilcoxon; p < 0,05.
- Banda: bytes enviados por quadro na nuvem × fps, contra nenhum envio de vídeo na borda. É o resultado
  sólido da QP2; a comparação absoluta de latência borda emulada × nuvem nativa não vale como resultado.

## Limitações a declarar

Tempos de borda vêm de emulação (QEMU) e não representam um Raspberry Pi; cenários de FPS derivados;
amostragem reduzida (D8); rede emulada com valores assumidos; sem gravações residenciais; energia só
com potência de fonte verificável; Edge TPU só pelo relatório do compilador.
