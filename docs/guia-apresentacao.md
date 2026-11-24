# Guia da apresentação em aula

Notas para apresentar o projeto ao vivo num Mac: o objetivo da pesquisa, o que cada etapa da
demonstração mostra, como rodá-la e o que responder às perguntas mais prováveis. A instalação e os
detalhes técnicos da demonstração estão em `docs/demo-macos.md`.

## Objetivo do projeto

"Detecção de Pessoas na Borda: Viabilidade da Inferência Local em Câmeras de Smart Home" (Equipe 5,
XRSC10, UNIFEI 2026.2).

Uma câmera de casa inteligente pode detectar pessoas de dois jeitos:

- **na nuvem**: a câmera envia o vídeo para um servidor, que roda o detector;
- **na borda**: o próprio dispositivo (uma placa ARM, como um Raspberry Pi) roda o detector e não
  precisa enviar o vídeo.

A pesquisa avalia se a inferência local é viável. Para isso compara três detectores leves
(**YOLOv8n**, **SSD-MobileNet V1** e **EfficientDet-Lite0**) em duas precisões (**FP32** e **INT8**) e
três resoluções da fonte (**320, 480 e 640 px**), medindo:

- **latência por quadro** (pré-processamento + inferência + pós-processamento) em ARM64;
- **qualidade**: mAP@50 da classe pessoa em 350 imagens do COCO val2017;
- **banda de subida** que a nuvem exige e a borda não (a borda não envia nenhum quadro).

A quantização para INT8 é o ponto central: reduz o tamanho do modelo e acelera a inferência em CPU
ARM. A pergunta é quanto ela acelera e quanto custa em qualidade.

### Como o artigo mediu

- Borda: VM ARM64 nativa (Oracle A1, Neoverse-N1, 2 núcleos), 350 quadros por combinação (50 de
  aquecimento), 18 combinações (decisão D10). Não é um Raspberry Pi: serve para comparar modelos,
  precisões e resoluções em ARM64 real.
- Nuvem: servidor x86 com rede emulada (RTT 40 ms, subida 10 Mbit/s), só FP32.
- Os cenários de 5, 15 e 30 FPS são derivados das medições (decisão D8).
- Resultados em `results/RESUMO.md`.

## Checklist antes da aula

- [ ] No app **Terminal**: `cd ~/Developer/deteccao-pessoas-borda && bash demo/roteiro.sh 5`.
  Clique em **Permitir** quando o macOS pedir a câmera e aperte `q` para sair.
- [ ] Rode a etapa 4 uma vez (`bash demo/roteiro.sh 4`) para confirmar que tudo carrega.
- [ ] Deixe o Mac na tomada (bateria fraca reduz o desempenho e muda os tempos).
- [ ] Feche apps pesados durante as medições.
- [ ] Aumente a fonte do Terminal (Cmd+) para a turma ler as tabelas.

## Roteiro (cerca de 10 minutos)

Abra o menu com `bash demo/roteiro.sh`, ou chame cada etapa pelo número.

| # | Comando | Tempo | O que mostrar e o que falar |
|---|---|---|---|
| 1 | `bash demo/roteiro.sh 1` | ~10 s | De onde vem cada modelo, com o sha256 conferido. **Não treinamos nada**: os três vêm pré-treinados no COCO. Nosso trabalho é converter, quantizar, medir e avaliar. |
| 2 | `bash demo/roteiro.sh 2` (ou `2 --rapido`) | ~1 min (~15 s) | A quantização FP32 → INT8 roda na hora, calibrada nas 128 imagens do COCO128. Mostre a tabela antes e depois: os modelos ficam de ~2,9 a ~3,7× menores. Os INT8 do SSD e do EfficientDet não têm nenhum tensor float32 ("inteiro total"); o do YOLOv8n é híbrido (D2). |
| 3 | `bash demo/roteiro.sh 3` | ~5 s | mAP@50 da classe pessoa em 100 imagens, ao lado do valor do artigo. No artigo, o INT8 quase não muda o mAP do YOLOv8n e do SSD, mas tira ~0,04 do EfficientDet (0,514 → 0,472 em 320). |
| 4 | `bash demo/roteiro.sh 4` | ~10 s | Latência FP32 × INT8 das 18 combinações neste Mac, ao lado da do artigo, e o ganho da quantização. |
| 5 | `bash demo/roteiro.sh 5` | livre | Webcam ao vivo. Troque o modelo (`m`), alterne FP32/INT8 (`i`) e mude a resolução (`r`), mostrando a latência mudar na tela. |
| 6 | `bash demo/roteiro.sh 6` | livre | Reserva, se a câmera falhar: as mesmas telas com as imagens COCO do projeto. |

Para mostrar o mAP completo (350 imagens, 3 resoluções, ~1 min): `bash demo/roteiro.sh 3 --completo`.

### Teclas da demonstração ao vivo

| Tecla | Ação |
|---|---|
| `m` ou `1` `2` `3` | troca o modelo (YOLOv8n, SSD-MobileNet V1, EfficientDet-Lite0) |
| `i` | alterna FP32 / INT8 |
| `r` | troca a resolução da fonte (320 → 480 → 640) |
| espaço | pausa |
| `q` ou Esc | sai |

### Como ler a tela ao vivo

- **Latência por quadro**: média dos últimos 30 quadros, dividida em pré + inferência + pós. É a
  mesma conta da coleta do artigo.
- **FPS sustentável** = 1000 / latência: quantos quadros por segundo o detector aguentaria.
- **FPS na tela**: inclui a câmera e o desenho; fica limitado pela câmera (em geral 30).
- **Linha "Artigo"**: latência e mAP@50 da mesma combinação no servidor ARM, lidos de `results/e5/`.
- **Entrada do modelo**: o SSD (300) e o EfficientDet (320) têm entrada fixa. Para eles, mudar a
  resolução da fonte muda só o redimensionamento (decisão D1); a inferência quase não muda.

## Perguntas prováveis e respostas

**Vocês treinaram os modelos?**
Não. Os três detectores são pré-treinados no COCO (YOLOv8n da Ultralytics, SSD-MobileNet V1 do TF1
Detection Model Zoo, EfficientDet-Lite0 do MediaPipe). A pesquisa é sobre implantação: quantização,
latência na borda e qualidade na classe pessoa.

**Como foi feita a quantização?**
Quantização pós-treinamento (PTQ), calibrada nas mesmas 128 imagens do COCO128, na mesma ordem, para
os três modelos:
- SSD-MobileNet V1: conversor do TensorFlow Lite com conjunto representativo, inteiro total.
- EfficientDet-Lite0: ai-edge-quantizer, inteiro total.
- YOLOv8n: exportador oficial da Ultralytics (`quantize=8`), que mantém entrada, saída e cabeça em
  float32 de propósito (decisão D2).

Nenhum INT8 foi baixado pronto. O SSD quantizado da Coral, por exemplo, não foi usado porque foi
treinado com quantização (QAT) e misturaria dois efeitos.

**Por que o INT8 acelera menos no Mac do que no artigo?**
É o que a etapa 4 mede: no Mac (Apple M5) o INT8 ficou de 1,1× a 1,5× mais rápido; no servidor ARM do
artigo, de 1,6× a 3,2× (`results/RESUMO.md`). O ganho da quantização depende do processador. Por isso
o artigo mede em ARM64 e os números do Mac não substituem os dele.

**Os tempos do artigo valem para um Raspberry Pi?**
Não como tempo absoluto. Foram medidos num servidor Neoverse-N1 de 2 núcleos; um Pi 4 usa
Cortex-A72 e um Pi 5 usa Cortex-A76. Servem para comparar modelos, precisões e resoluções em ARM64
real (limitação declarada na decisão D10).

**Por que o SSD e o EfficientDet não mudam de resolução?**
Os dois têm entrada fixa (300×300 e 320×320). Só o YOLOv8n é exportado em 320, 480 e 640. Para manter
as combinações, "resolução" é a do quadro da fonte, e cada modelo redimensiona para a sua entrada
(decisão D1).

**E a nuvem?**
Na nuvem, a câmera precisa enviar o vídeo: a banda de subida cresce com a resolução e a taxa de
quadros. Na borda, nenhum quadro sai da casa. Esse é o resultado mais sólido da comparação borda ×
nuvem (`results/RESUMO.md`, seção de banda de subida).

**Os números da demonstração são confiáveis?**
Tudo o que aparece é medido na hora no Mac ou lido dos arquivos de resultados do repositório.
Com as 350 imagens, o mAP dos FP32 no Mac é igual ao do artigo. Os INT8 refeitos no Mac ficam a
alguns milésimos, porque não saem idênticos byte a byte (o export INT8 do YOLOv8n varia a cada
execução).

## Se algo der errado

| Problema | O que fazer |
|---|---|
| "Não consegui abrir a webcam" | Ajustes do Sistema → Privacidade e Segurança → Câmera → ligue o Terminal; feche o Terminal (Cmd+Q) e abra de novo. Na hora da aula, use a etapa 6. |
| A câmera abre outra (iPhone via Continuidade) | `.venv/bin/python demo/demo_ao_vivo.py --camera 1` |
| "Ambiente não encontrado" | `bash scripts/setup_macos.sh` (~2 min com os downloads em cache) |
| "Modelo não encontrado" | `bash scripts/setup_macos.sh`, ou `bash demo/roteiro.sh 2` para refazer os INT8 |
| A etapa 2 falhou no meio | O roteiro devolve os INT8 anteriores automaticamente; a demonstração continua funcionando. |
| Sem internet na sala | Tudo funciona offline depois da instalação; a etapa 1 só confere os arquivos já baixados. |
| Vídeo próprio | `.venv/bin/python demo/demo_ao_vivo.py --video arquivo.mp4` |
