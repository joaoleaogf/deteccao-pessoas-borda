# Detecção de Pessoas na Borda

Código do experimento da pesquisa "Detecção de Pessoas na Borda: Viabilidade da Inferência
Local em Câmeras de Smart Home" (Equipe 5, XRSC10, UNIFEI 2026.2).

O contexto completo fica em `docs/CONTEXTO.md` (exporte o documento da equipe para lá).
As decisões que a equipe ainda precisa tomar estão em `docs/decisoes.md`.

**Situação:** E4 concluída. E5 (coleta) e E6 (análise) implementadas; o andamento da coleta e os
resultados estão em `results/RESUMO.md`. O plano da E5 está em `docs/plano_e5.md`.

**Aviso sobre os números.** O contêiner ARM64 é emulado por QEMU. Ele limita núcleos e
memória, mas não reproduz a velocidade de um Raspberry Pi. Nenhum tempo gerado na E4 é
resultado do experimento: são testes de funcionamento.

**Demonstração no macOS.** Para rodar sem Docker num Mac com Apple Silicon (quantização, mAP,
latência e detecção ao vivo na webcam): `bash scripts/setup_macos.sh` e depois `bash demo/roteiro.sh`.
Passo a passo em `docs/demo-macos.md`; notas para a apresentação em `docs/guia-apresentacao.md`.

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

## E5: coleta

```powershell
.\e5.ps1 [-Precisao int8|fp32|todas] [-SoPreparar]
```

```bash
./e5.sh [--precisao int8|fp32|todas] [--so-preparar]
```

| Passo | Onde roda | Script | O que gera |
|---|---|---|---|
| 1 | host | `e5.ps1` / `e5.sh` | imagens `borda-prep` e `borda-arm64` |
| 2 | `borda-prep` | `src/prepare/montar_teste.py` | `configs/conjunto_teste.csv`, `data/teste_coco/` (350 imagens COCO val2017 com pessoa) |
| 2 | `borda-prep` | `src/eval/validar_decodificadores.py` | `results/e5/validacao_decodificadores.csv` (mAP@50 no x86 nativo) |
| 3 | 2 contêineres `borda-prep` + `tc netem` | `src/nuvem/servidor.py`, `src/nuvem/cliente.py` | `results/e5/nuvem/<combinação>/` |
| 4 | `borda-arm64` (QEMU, `cortex-a72`) | `src/bench/coletar_borda.py` → `medir_borda.py` | `results/e5/borda/<combinação>/` |

Os passos 3 e 4 rodam em segundo plano (`docker logs -f e5-borda`, `docker logs -f e5-nuvem`) e são
retomáveis: combinação com o arquivo `COMPLETO` não roda de novo. Cada combinação tem `quadros.csv`
(tempos por quadro), `deteccoes.json` e `manifesto.json` (data, versões, perfil, sha256 do modelo, rede).
A amostragem é a reduzida (decisão D8): 18 combinações na borda e 9 na nuvem, 350 quadros cada, com os
cenários de 5, 15 e 30 FPS derivados na E6. O computador precisa ficar ligado durante a coleta.

### Borda em ARM64 nativo (como a coleta foi feita; decisão D10)

O passo 4 acima roda a borda emulada pelo QEMU, que é lenta demais para a coleta completa (D9). Os
resultados em `results/e5/borda/` foram medidos numa máquina ARM64 nativa (VM Oracle A1, 2 núcleos
Neoverse-N1, Ubuntu 24.04), assim:

```bash
sudo apt-get install -y docker.io docker-buildx git
git clone https://github.com/joaoleaogf/deteccao-pessoas-borda.git && cd deteccao-pessoas-borda
# copie para a máquina models/*.tflite, data/teste_coco/ e data/teste/bus.jpg (gerados pela E4 e pelo passo 2)
sudo DOCKER_BUILDKIT=1 docker build -t borda-arm64 -f docker/Dockerfile.arm64 docker
sudo docker run --rm -v "$PWD":/repo -w /repo borda-arm64 python src/bench/coletar_borda.py \
  --perfil oracle-a1-2ocpu --threads 2 --ambiente "ARM64 nativo (Oracle A1, Neoverse-N1, 2 núcleos)"
```

Apague antes as pastas de `results/e5/borda/` que vierem do git, ou elas serão puladas como concluídas.
A coleta parcial emulada ficou em `results/e5/anexo_emulado/`, só para comparação.

## E6: análise

```powershell
.\e6.ps1
```

```bash
./e6.sh
```

| Script | O que gera |
|---|---|
| `src/analysis/derivar_cenarios.py` | `results/e5/cenarios/`, `results/summary.csv`, `results/e5/qualidade.csv` |
| `src/analysis/estatistica.py` | `results/stats/`, `figures/*.pdf` e `*.png`, `results/RESUMO.md` |
| `src/analysis/artigo_tex.py` | `docs/artigo/tabelas/*.tex`, `docs/artigo/numeros.tex` |

A análise é determinística e pode rodar com a coleta incompleta (usa as combinações concluídas).
O rascunho das seções do artigo está em `docs/artigo/`; os números do texto vêm de `numeros.tex`.

## Estrutura

```
configs/    models.yaml (origens e hashes), profiles.yaml, scenarios.yaml, network.yaml
docker/     Dockerfile.host (preparação), Dockerfile.edgetpu (compilador), Dockerfile.arm64 (medição)
docs/       ambiente.md (gerado), decisoes.md, demo-macos.md, guia-apresentacao.md
demo/       demonstração em aula no macOS (roteiro.sh, demo_ao_vivo.py, etapas.py)
scripts/    setup_macos.sh (instalação sem Docker no macOS)
requirements/  versões exatas dos ambientes do macOS
src/        comum.py, prepare/ (E4 e E5), bench/ (E4 e E5), nuvem/ (E5), eval/ (E5), analysis/ (E6)
models/     arquivos .tflite (fora do git; gerados pelo passo 2)
data/       calibração e imagem de teste (fora do git; baixados pelo passo 2)
results/    CSVs e relatórios
figures/    gráficos do artigo (E6)
```

Modelos e dados ficam fora do git. Para obtê-los, rode a E4: os downloads são conferidos por
sha256 e as conversões usam versões fixadas das ferramentas.
