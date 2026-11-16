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
