# Detecção de Pessoas na Borda

Código do experimento da pesquisa "Detecção de Pessoas na Borda: Viabilidade da Inferência
Local em Câmeras de Smart Home" (Equipe 5, XRSC10, UNIFEI 2026.2).

O contexto completo fica em `docs/CONTEXTO.md` (exporte o documento da equipe para lá).
As decisões que a equipe ainda precisa tomar estão em `docs/decisoes.md`.

**Situação:** etapa E4 implementada. E5 (coleta) e E6 (análise) ainda não começaram.

**Aviso sobre os números.** O contêiner ARM64 é emulado por QEMU. Ele limita núcleos e
memória, mas não reproduz a velocidade de um Raspberry Pi. Nenhum tempo gerado na E4 é
resultado do experimento: são testes de funcionamento.

## Pré-requisitos

- Docker com emulação ARM64. O Docker Desktop (Windows, macOS) já traz o QEMU. Em Linux puro,
  registre os emuladores uma vez: `docker run --privileged --rm tonistiigi/binfmt --install arm64`.
- Cerca de 15 GB livres em disco e acesso à internet na primeira execução.

Não é preciso instalar Python nem nenhuma outra ferramenta no host: tudo roda em contêineres.

## E4: refazer do zero com um comando

Windows (PowerShell):

```powershell
.\e4.ps1 -DoZero
```

Linux, macOS ou WSL:

```bash
./e4.sh --do-zero
```

Sem `-DoZero`/`--do-zero`, o que já existe é reaproveitado. `-Perfil rpi5`/`--perfil rpi5`
troca os limites do contêiner ARM64 (padrão `rpi4b`; veja `configs/profiles.yaml`).

### O que o comando faz

| Passo | Onde roda | Script | O que gera |
|---|---|---|---|
| 1 | host | `e4.sh` / `e4.ps1` | `results/ambiente/host.txt` e as 3 imagens Docker |
| 2 | `borda-prep` (amd64) | `src/prepare/preparar.sh` | `models/*.tflite`, `results/modelos.csv` |
| 3 | `borda-edgetpu` (amd64) | `src/prepare/compilar_edgetpu.sh` | `models/edgetpu/`, `results/edgetpu_logs/` |
| 4 | `borda-arm64` (QEMU) | `src/bench/validar_modelo.py`, `src/bench/fumaca_benchmark.py` | `results/validacao_arm64.csv`, `results/benchmark_fumaca.csv` |
| 5 | `borda-prep` (amd64) | `src/prepare/extrair_logs_edgetpu.py`, `src/prepare/registrar_ambiente.py` | `results/edgetpu_compile.csv`, `docs/ambiente.md` |

O passo 2 chama, em ordem:

| Script | O que faz |
|---|---|
| `src/prepare/baixar.py` | Baixa pesos, conjunto de calibração e imagem de teste, e confere o sha256 de cada um. |
| `src/prepare/exportar_yolo.py` | Exporta o YOLOv8n para `.tflite` em FP32 e INT8, em 320, 480 e 640. |
| `src/prepare/quantizar_efficientdet.py` | Copia o EfficientDet-Lite0 FP32 e gera o INT8 por quantização pós-treinamento. |
| `src/prepare/converter_ssd.py` | Converte o SSD-MobileNet V1 do grafo congelado do TF1 para FP32 e INT8. |
| `src/prepare/conferir_modelos.py` | Confere por script o tipo dos tensores de cada modelo. |

Todo script aceita `--help` e começa com um comentário dizendo o que faz e o que gera.
`src/comum.py` tem as funções compartilhadas e `src/prepare/quantizar.py` a quantização com
ai-edge-quantizer.

### Modelos gerados

Dez arquivos em `models/`, com o nome `<modelo>_<precisão>_<resolução>.tflite`:

| Modelo | Origem | Resoluções | INT8 |
|---|---|---|---|
| `yolov8n` | pesos da Ultralytics (COCO) | 320, 480, 640 | export oficial `quantize=8` (híbrido, veja D2) |
| `ssd_mobilenet_v1` | TF1 Detection Model Zoo (COCO) | 300 | inteiro total, PTQ do TensorFlow |
| `efficientdet_lite0` | MediaPipe (COCO) | 320 | inteiro total, PTQ do ai-edge-quantizer |

Os três INT8 são calibrados com as mesmas 128 imagens (COCO128), na mesma ordem.

### Critérios de aceite da E4 e onde conferir

| Critério | Onde conferir |
|---|---|
| Todos os modelos carregam e executam no contêiner ARM64 | `results/validacao_arm64.csv`, colunas `arquitetura` e `ok` |
| INT8 com entrada, saída e pesos em inteiros, conferido por script | `results/modelos.csv`, coluna `inteiro_total` |
| Um único comando refaz a etapa do zero | `e4.sh --do-zero` ou `e4.ps1 -DoZero` |

## Estrutura

```
configs/    models.yaml (origens e hashes), profiles.yaml, scenarios.yaml, network.yaml
docker/     Dockerfile.host (preparação), Dockerfile.edgetpu (compilador), Dockerfile.arm64 (medição)
docs/       ambiente.md (gerado), decisoes.md
src/        comum.py, prepare/ (E4), bench/ (E4 e E5), eval/ (E5), analysis/ (E6)
models/     arquivos .tflite (fora do git; gerados pelo passo 2)
data/       calibração e imagem de teste (fora do git; baixados pelo passo 2)
results/    CSVs e relatórios
figures/    gráficos do artigo (E6)
```

Modelos e dados ficam fora do git. Para obtê-los, rode a E4: os downloads são conferidos por
sha256 e as conversões usam versões fixadas das ferramentas.
