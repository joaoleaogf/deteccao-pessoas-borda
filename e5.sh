#!/usr/bin/env bash
# Etapa E5 (coleta) com um comando (Linux, macOS ou WSL). No Windows sem WSL, use e5.ps1.
#
# O que faz, em ordem:
#   1. constrói as imagens borda-prep (amd64) e borda-arm64
#   2. monta o conjunto de teste (350 imagens COCO) e valida os decodificadores no x86 nativo
#   3. inicia o baseline de nuvem em segundo plano: servidor e cliente numa rede Docker com tc netem
#   4. inicia a coleta da borda em segundo plano no contêiner ARM64 (QEMU_CPU=cortex-a72, perfil rpi4b)
# As duas coletas são retomáveis: rodar de novo pula as combinações concluídas.
#
# Uso: ./e5.sh [--precisao int8|fp32|todas] [--so-preparar]
set -euo pipefail
cd "$(dirname "$0")"

PRECISAO="todas"; SO_PREPARAR=""
while (( $# )); do
  case "$1" in
    --precisao) PRECISAO="$2"; shift ;;
    --so-preparar) SO_PREPARAR=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "Opção desconhecida: $1"; exit 2 ;;
  esac
  shift
done

M=(-v "$PWD":/repo -w /repo)
PY=/opt/venv-export/bin/python

echo "== [1/4] Imagens Docker"
docker build --platform linux/amd64 -t borda-prep  -f docker/Dockerfile.host  docker
docker build --platform linux/arm64 -t borda-arm64 -f docker/Dockerfile.arm64 docker

echo "== [2/4] Conjunto de teste e validação dos decodificadores (x86 nativo)"
docker run --rm --platform linux/amd64 "${M[@]}" borda-prep $PY src/prepare/montar_teste.py
docker run --rm --platform linux/amd64 "${M[@]}" borda-prep $PY src/eval/validar_decodificadores.py --int8
[[ -n "$SO_PREPARAR" ]] && { echo "Preparação concluída."; exit 0; }

echo "== [3/4] Baseline de nuvem (destacado; retomável)"
docker network create e5-rede >/dev/null 2>&1 || true
docker rm -f e5-servidor e5-nuvem >/dev/null 2>&1 || true
docker run -d --name e5-servidor --network e5-rede --network-alias servidor --cap-add NET_ADMIN "${M[@]}" borda-prep \
  sh -c "tc qdisc add dev eth0 root netem delay 20ms && exec $PY src/nuvem/servidor.py"
docker run -d --name e5-nuvem --network e5-rede --cap-add NET_ADMIN "${M[@]}" borda-prep \
  sh -c "tc qdisc add dev eth0 root netem delay 20ms rate 10mbit && $PY src/nuvem/cliente.py"

echo "== [4/4] Borda no contêiner ARM64 (destacado; retomável; INT8 primeiro)"
FILTRO=(); [[ "$PRECISAO" != "todas" ]] && FILTRO=(--precisao "$PRECISAO")
docker rm -f e5-borda >/dev/null 2>&1 || true
docker run -d --name e5-borda --platform linux/arm64 --cpus=4 --memory=4g -e QEMU_CPU=cortex-a72 "${M[@]}" borda-arm64 \
  python src/bench/coletar_borda.py --perfil rpi4b "${FILTRO[@]}"

echo "Coleta iniciada em segundo plano. Acompanhe com 'docker logs -f e5-borda' e 'docker logs -f e5-nuvem'."
echo "Se o computador desligar, rode ./e5.sh de novo: combinações concluídas não rodam outra vez."
