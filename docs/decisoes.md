# Decisões em aberto e escolhas provisórias

Este arquivo lista o que a equipe ainda precisa decidir e o que foi adotado provisoriamente
para a E4 poder rodar. Cada escolha provisória está em um arquivo de configuração e pode ser
trocada sem mexer no código. O documento de contexto cita uma seção "Riscos e decisões em
aberto" que não veio no PDF; confira se há itens dela que faltam aqui.

## D1. Resolução dos modelos de entrada fixa (afeta os 54 cenários)

**Fato verificado em 16/11/2026.** Só o YOLOv8n aceita 320, 480 e 640 (a resolução é escolhida
na exportação). O SSD-MobileNet V1 só converte em 300×300: o grafo tem os formatos das âncoras
gravados, e a conversão em 480×480 falha com erro de `Reshape`. O EfficientDet-Lite0 é
publicado só em 320×320.

**Consequência.** A matriz 3 modelos × 2 precisões × 3 resoluções não existe como "resolução de
entrada do modelo" para dois dos três modelos.

**Opções.**
1. Tratar "resolução" como a resolução do quadro da fonte. Cada modelo redimensiona o quadro
   para a sua entrada. Mantém os 54 cenários; o custo do redimensionamento entra na latência
   fim a fim. Para o YOLOv8n, é preciso decidir se a entrada acompanha a fonte (320/480/640)
   ou fica fixa.
2. Variar a resolução só no YOLOv8n e reduzir a matriz (18 + 6 + 6 = 30 cenários).
3. Trocar os modelos de entrada fixa por famílias com várias resoluções (por exemplo,
   EfficientDet-Lite0/1/2), o que muda o fator "modelo".

**Provisório na E4.** YOLOv8n em 320, 480 e 640; SSD em 300; EfficientDet em 320
(`configs/models.yaml`, campo `resolucoes`). Isso serve a qualquer das três opções.

**Adotado em 16/11/2026 (a equipe pode rever): opção 1.** "Resolução" é a do quadro da fonte (320, 480,
640). O YOLOv8n usa o modelo exportado na mesma resolução; SSD (300) e EfficientDet (320) redimensionam o
quadro para a entrada fixa, e esse custo entra no pré-processamento. Mantém os 54 cenários. O quadro da
fonte é a imagem redimensionada para res × res (bilinear, sem manter a proporção).

## D2. O que conta como "INT8" no YOLOv8n

**Fato verificado.** O export oficial da Ultralytics (`format="litert"`, `quantize=8`) deixa a
entrada, a saída e a cabeça de detecção em float32 de propósito; só o corpo da rede vira int8.
Por isso o `yolov8n_int8_*` não atende ao critério "entrada, saída e pesos em inteiros".
SSD e EfficientDet saem inteiros totais.

**Opções.**
1. Manter o export oficial e ajustar o critério de aceite no artigo (INT8 "híbrido").
2. Usar `int8_modo: inteiro_total` em `configs/models.yaml`: quantiza tudo com
   ai-edge-quantizer. Atende ao critério, mas a qualidade (mAP) só será conhecida na E5.

**Provisório na E4.** Opção 1, porque é o caminho documentado pela ferramenta.

**Adotado em 16/11/2026 (a equipe pode rever): opção 1**, o INT8 oficial (híbrido) da Ultralytics.
`configs/models.yaml` não muda. Consequência registrada na E4: o Edge TPU Compiler recusa esse modelo.

## D3. Conjunto de calibração

**Provisório na E4.** COCO128: 128 imagens do COCO train2017, na ordem do nome do arquivo, as
mesmas para os três modelos. Não se sobrepõe ao COCO val2017, que pode ser o conjunto de teste.
Falta confirmar se 128 imagens bastam ou se a equipe quer um conjunto maior.

## D4. Variante de memória de cada placa

`configs/profiles.yaml` usa 4 GB para o Pi 4B e 8 GB para o Pi 5, como no documento de contexto.
Falta confirmar com a equipe.

## D5. Baseline de nuvem (E5)

Protocolo (RTSP ou WebRTC), codec, RTT, banda de subida e hardware do servidor não estão
definidos. `configs/network.yaml` está com todos os campos nulos.

## D6. Vídeos e conjunto de teste (E5)

Falta escolher as sequências (COCO ou PASCAL VOC) e saber se as gravações residenciais
(diurna, baixa luz; 1, 2, 3+ pessoas) existem e quem as anota.

## D7. Potência de referência para a energia estimada (E5)

Falta escolher a fonte da literatura e o valor de potência de cada placa.

## Decisões adotadas para a E5 (16/11/2026; a equipe pode rever)

- **D4.** A coleta roda só no perfil `rpi4b` (`--cpus=4 --memory=4g`). Sob QEMU os perfis `rpi4b` e
  `rpi5` não diferem em velocidade (o emulador não reproduz o processador), então duplicar a execução
  não traria informação. As variantes de memória continuam como em `configs/profiles.yaml`.
- **D5.** Baseline de nuvem com dois contêineres numa rede Docker. O cliente só codifica e envia: JPEG
  qualidade 80 por quadro, sobre TCP/HTTP, quadro a quadro (simplificação declarada em relação a
  RTSP/WebRTC, para manter o pareamento por quadro). Enlace com `tc netem`: RTT 40 ms (20 ms em cada
  sentido) e subida de 10 Mbps. Servidor linux/amd64 nativo, mesmos modelos FP32 e resoluções.
  **Atualizada em 17/11/2026:** os dois valores são parâmetros de cenário declarados, não valores
  típicos. O RTT de 40 ms fica dentro da faixa medida por Corneo et al. (WWW '21, doi
  10.1145/3442381.3449854), favorável à nuvem para a América do Sul. A subida de 10 Mbit/s não tem fonte
  específica e fica como limite declarado; como referência, as medianas da Ookla para o Brasil (set/2026)
  são 137,96 Mbit/s na banda larga fixa e 17,66 Mbit/s na rede móvel. O resultado da QP2 é a banda
  demandada (bytes × fps), que independe desse limite (`configs/network.yaml`).
- **D6.** Conjunto de teste: imagens do COCO val2017 que contêm pessoa, sem anotação de multidão,
  balanceadas entre 1, 2 e 3+ pessoas, ordenadas por id, com as anotações da classe pessoa
  (`configs/teste.yaml`, lista e sha256 em `configs/conjunto_teste.csv`; imagens fora do git). Não há
  gravações residenciais: limitação a declarar no artigo.
- **D7.** Potência de referência por placa em `configs/energia.yaml`, com campo de fonte. Enquanto não
  houver valor com fonte verificável, o campo fica nulo e a energia não é calculada.
- **D8. Amostragem reduzida (altera o desenho da ATV 04).** No lugar de 54 cenários × 1.050 inferências,
  cada uma das 18 combinações modelo × precisão × resolução é medida uma única vez, em processo novo, com
  350 quadros (50 de aquecimento descartados + 300 válidos). Os cenários de 5, 15 e 30 FPS são derivados
  dessas medições (quadro i disponível em i/fps, fila e quadros que seriam descartados) e ficam marcados
  como derivados. Motivo: o teste de fumaça indica cerca de 50 h de emulação no desenho original contra
  cerca de 5 h no reduzido, e a taxa da fonte não muda o tempo de inferência de cada quadro. O baseline
  de nuvem usa as mesmas 350 imagens por combinação. Decisão da equipe em 16/11/2026.
- **D9. Biblioteca Python ~10× mais lenta que o benchmark_model sob QEMU (descoberta de 17/11/2026).**
  Medido no contêiner ARM64 (4 CPUs), SSD-MobileNet V1, por inferência, ambiente emulado:
  `benchmark_model` FP32 4,13 s com XNNPACK e 4,63 s sem; Python (`ai-edge-litert` 2.3.0, 4 threads)
  58,1–58,3 s com XNNPACK, 42,9–49,8 s sem delegado e 93,6–94,9 s com 1 thread; versões 1.4.0
  (40,4–44,8 s) e 2.0.2 (58,3–66,3 s) dão o mesmo. INT8: 4,6–6,4 s no Python contra 0,36 s no
  `benchmark_model` (teste de fumaça). Com `QEMU_CPU=cortex-a72` (o processador do Pi 4) o Python cai
  para 35,1–41,2 s no FP32 e 2,2–2,6 s no INT8. A coleta precisa do Python (pré e pós-processamento e
  detecções por quadro), então a estimativa de ~5 h (feita com o `benchmark_model`) vira ~55 h.
  **Adotado:** coleta com `QEMU_CPU=cortex-a72`, registrado no manifesto de cada combinação; os 9 INT8
  rodam com 350 quadros. **Pendente (decisão da equipe):** como medir os 9 FP32 (350 quadros em ~2,5
  dias, 100 quadros em ~16 h, ou inferência pelo `benchmark_model`).
- **D10. Borda medida em ARM64 nativo, não mais emulada (decisão do usuário em 17/11/2026).**
  A coleta da borda passou para uma VM ARM da Oracle Cloud (VM.Standard.A1.Flex, Ampere com núcleos
  Neoverse-N1, 2 OCPU, 12 GB, Ubuntu 24.04, região São Paulo, cota gratuita), criada só para isso e
  apagada no fim. O contêiner `borda-arm64` roda lá sem QEMU, com 2 threads (perfil `oracle-a1-2ocpu`
  em `configs/profiles.yaml`). Motivo: sob o QEMU a coleta levaria ~2 dias (D9); em ARM nativo, a primeira
  combinação (YOLOv8n INT8, fonte 320) levou 11,2 ms por quadro e a coleta inteira cabe em minutos.
  Validação: o mAP@50 dessa combinação na VM (0,676) é igual ao da validação no x86 (0,676).
  As 18 combinações foram refeitas na VM, inclusive as 2 INT8 já medidas no emulador; o que a coleta
  emulada mediu fica em `results/e5/anexo_emulado/` como anexo de comparação (marcado como emulado).
  **Limitação:** um núcleo Neoverse-N1 de servidor não é um Raspberry Pi (Cortex-A72 no Pi 4,
  Cortex-A76 no Pi 5) e são 2 núcleos, não 4; os tempos servem para comparar modelos, precisões e
  resoluções em ARM64 real, não como tempo absoluto de um Pi.
- **Execução paralela.** O baseline de nuvem rodou ao mesmo tempo que a coleta da borda (host com 12
  CPUs; borda limitada a 4). Fica registrado no manifesto de cada combinação de nuvem.
- **Métricas de qualidade.** mAP@50 da classe pessoa (pycocotools) e precisão, revocação e F1 com
  limiar de pontuação 0,5 e IoU 0,5, calculados das detecções salvas na própria coleta. NMS igual para
  os três modelos: IoU 0,5, pontuação mínima 0,01, até 100 detecções por quadro.

## Escolhas técnicas feitas na E4 (para a equipe saber defender)

- **SSD-MobileNet V1 FP32 e INT8 saem do mesmo grafo** (TF1 Model Zoo,
  `ssd_mobilenet_v1_coco_2018_01_28`). O modelo quantizado pronto da Coral não foi usado porque
  foi treinado com quantização (QAT): compará-lo com um FP32 de outros pesos misturaria dois
  efeitos. Aqui a única diferença entre FP32 e INT8 é a quantização pós-treinamento.
- **EfficientDet-Lite0 INT8 é quantizado por nós** a partir do FP32 do MediaPipe, com a mesma
  calibração dos outros modelos, em vez de usar o INT8 pronto do MediaPipe.
- **SSD e EfficientDet não têm NMS dentro do modelo.** Devolvem caixas e pontuações brutas por
  âncora. A decodificação e a NMS serão feitas em Python na E5, e esse tempo conta na latência
  fim a fim. O YOLOv8n também devolve saída bruta (84 × N).
- **A entrada do YOLOv8n é NCHW** (1×3×H×W, valores de 0 a 1); a dos outros é NHWC.
