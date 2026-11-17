# Etapa E5 (coleta) no Windows (PowerShell + Docker Desktop). Faz o mesmo que e5.sh; veja lá cada passo.
#
# Uso: .\e5.ps1 [-Precisao int8|fp32|todas] [-SoPreparar]
param(
    [ValidateSet("int8", "fp32", "todas")][string]$Precisao = "todas",
    [switch]$SoPreparar
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Rodar {
    # Executa um comando externo e interrompe o script se ele falhar.
    & $args[0] $args[1..($args.Count - 1)]
    if ($LASTEXITCODE -ne 0) { throw "Falhou: $($args -join ' ')" }
}

function Docker-Silencioso {
    # Comando docker cujo erro é esperado (por exemplo, remover contêiner que não existe).
    $ErrorActionPreference = "Continue"
    & docker @args 2>&1 | Out-Null
}

$montagem = @("-v", "${PWD}:/repo", "-w", "/repo")
$py = "/opt/venv-export/bin/python"

Write-Host "== [1/4] Imagens Docker"
Rodar docker build --platform linux/amd64 -t borda-prep -f docker/Dockerfile.host docker
Rodar docker build --platform linux/arm64 -t borda-arm64 -f docker/Dockerfile.arm64 docker

Write-Host "== [2/4] Conjunto de teste e validação dos decodificadores (x86 nativo)"
Rodar docker run --rm --platform linux/amd64 @montagem borda-prep $py src/prepare/montar_teste.py
Rodar docker run --rm --platform linux/amd64 @montagem borda-prep $py src/eval/validar_decodificadores.py --int8
if ($SoPreparar) { Write-Host "Preparação concluída."; exit 0 }

Write-Host "== [3/4] Baseline de nuvem (destacado; retomável)"
Docker-Silencioso network create e5-rede
Docker-Silencioso rm -f e5-servidor e5-nuvem
Rodar docker run -d --name e5-servidor --network e5-rede --network-alias servidor --cap-add NET_ADMIN @montagem borda-prep `
    sh -c "tc qdisc add dev eth0 root netem delay 20ms && exec $py src/nuvem/servidor.py"
Rodar docker run -d --name e5-nuvem --network e5-rede --cap-add NET_ADMIN @montagem borda-prep `
    sh -c "tc qdisc add dev eth0 root netem delay 20ms rate 10mbit && $py src/nuvem/cliente.py"

Write-Host "== [4/4] Borda no contêiner ARM64 (destacado; retomável; INT8 primeiro)"
$filtro = if ($Precisao -eq "todas") { @() } else { @("--precisao", $Precisao) }
Docker-Silencioso rm -f e5-borda
Rodar docker run -d --name e5-borda --platform linux/arm64 --cpus=4 --memory=4g -e QEMU_CPU=cortex-a72 @montagem borda-arm64 `
    python src/bench/coletar_borda.py --perfil rpi4b @filtro

Write-Host "Coleta iniciada em segundo plano. Acompanhe com:"
Write-Host "  docker logs -f e5-borda     (borda; andamento em results/e5/borda/andamento.log)"
Write-Host "  docker logs -f e5-nuvem     (nuvem)"
Write-Host "Se o computador desligar, rode .\e5.ps1 de novo: combinações concluídas não rodam outra vez."
