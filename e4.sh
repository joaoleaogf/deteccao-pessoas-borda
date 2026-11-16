#!/usr/bin/env bash
# Etapa E4 inteira com um comando (Linux, macOS ou WSL). No Windows sem WSL, use e4.ps1.
#
# O que faz, em ordem:
#   1. anota o ambiente do host e constrói as 3 imagens Docker
#   2. prepara os modelos FP32 e INT8                    (contêiner borda-prep, linux/amd64)
#   3. compila os INT8 com o Edge TPU Compiler           (contêiner borda-edgetpu, linux/amd64)
#   4. valida os modelos e roda o teste de fumaça        (contêiner borda-arm64, emulado por QEMU)
#   5. extrai o CSV dos relatórios e escreve docs/ambiente.md
#
# Uso: ./e4.sh [--do-zero] [--perfil rpi4b|rpi5]
#   --do-zero   apaga modelos e resultados da E4 antes de refazer
#   --perfil    limites de CPU e memória do contêiner ARM64 (configs/profiles.yaml); padrão rpi4b
set -euo pipefail
cd "$(dirname "$0")"

DO_ZERO=""; PERFIL="rpi4b"
while (( $# )); do
  case "$1" in
    --do-zero) DO_ZERO="--do-zero" ;;
    --perfil) PERFIL="$2"; shift ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "Opção desconhecida: $1"; exit 2 ;;
  esac
  shift
done
case "$PERFIL" in
  rpi4b) LIMITES=(--cpus=4 --memory=4g) ;;
  rpi5)  LIMITES=(--cpus=4 --memory=8g) ;;
  *) echo "Perfil desconhecido: $PERFIL"; exit 2 ;;
esac

echo "== [1/5] Ambiente do host e imagens Docker"
mkdir -p results/ambiente
{
  echo "data (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "sistema do host: $(uname -srmo)"
  [[ -r /etc/os-release ]] && echo "distribuição: $(. /etc/os-release && echo "$PRETTY_NAME")"
  echo "docker (cliente): $(docker version --format '{{.Client.Version}}')"
  echo "docker (servidor): $(docker version --format '{{.Server.Version}}, {{.Server.Os}}/{{.Server.Arch}}')"
  echo "docker info: $(docker info --format '{{.OperatingSystem}}, kernel {{.KernelVersion}}, {{.NCPU}} CPUs, {{.MemTotal}} bytes de memória')"
  echo "perfil do contêiner ARM64: $PERFIL (${LIMITES[*]})"
  echo "-- emuladores QEMU registrados (tonistiigi/binfmt --version):"
  docker run --rm --privileged tonistiigi/binfmt --version 2>&1 || echo "(não foi possível consultar)"
} > results/ambiente/host.txt
docker build --platform linux/amd64 -t borda-prep    -f docker/Dockerfile.host    docker
docker build --platform linux/amd64 -t borda-edgetpu -f docker/Dockerfile.edgetpu docker
docker build --platform linux/arm64 -t borda-arm64   -f docker/Dockerfile.arm64   docker

MONTAGEM=(-v "$PWD":/repo -w /repo)
echo "== [2/5] Preparação dos modelos"
docker run --rm --platform linux/amd64 "${MONTAGEM[@]}" borda-prep bash src/prepare/preparar.sh $DO_ZERO
echo "== [3/5] Edge TPU Compiler"
docker run --rm --platform linux/amd64 "${MONTAGEM[@]}" borda-edgetpu bash src/prepare/compilar_edgetpu.sh
echo "== [4/5] Validação e teste de fumaça em ARM64 (perfil $PERFIL)"
docker run --rm --platform linux/arm64 "${LIMITES[@]}" "${MONTAGEM[@]}" borda-arm64 \
  sh -c "python src/bench/validar_modelo.py && python src/bench/fumaca_benchmark.py"
echo "== [5/5] CSV do compilador e docs/ambiente.md"
docker run --rm --platform linux/amd64 "${MONTAGEM[@]}" borda-prep \
  sh -c "python3 src/prepare/extrair_logs_edgetpu.py && python3 src/prepare/registrar_ambiente.py"
echo "E4 concluída. Veja results/ e docs/ambiente.md."
