# Etapa E4 inteira com um comando no Windows (PowerShell + Docker Desktop).
# Faz o mesmo que e4.sh; veja lá a descrição de cada passo.
#
# Uso: .\e4.ps1 [-DoZero] [-Perfil rpi4b|rpi5]
param(
    [switch]$DoZero,
    [ValidateSet("rpi4b", "rpi5")][string]$Perfil = "rpi4b"
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Rodar {
    # Executa um comando externo e interrompe o script se ele falhar.
    & $args[0] $args[1..($args.Count - 1)]
    if ($LASTEXITCODE -ne 0) { throw "Falhou: $($args -join ' ')" }
}

$limites = if ($Perfil -eq "rpi5") { @("--cpus=4", "--memory=8g") } else { @("--cpus=4", "--memory=4g") }
$zero = if ($DoZero) { "--do-zero" } else { "" }
$montagem = @("-v", "${PWD}:/repo", "-w", "/repo")

Write-Host "== [1/5] Ambiente do host e imagens Docker"
New-Item -ItemType Directory -Force results/ambiente | Out-Null
$so = Get-CimInstance Win32_OperatingSystem
$linhas = @(
    "data (UTC): $((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'))",
    "sistema do host: $($so.Caption) $($so.Version) ($($so.OSArchitecture))",
    "docker (cliente): $(docker version --format '{{.Client.Version}}')",
    "docker (servidor): $(docker version --format '{{.Server.Version}}, {{.Server.Os}}/{{.Server.Arch}}')",
    "docker info: $(docker info --format '{{.OperatingSystem}}, kernel {{.KernelVersion}}, {{.NCPU}} CPUs, {{.MemTotal}} bytes de memória')",
    "perfil do contêiner ARM64: $Perfil ($($limites -join ' '))",
    "-- emuladores QEMU registrados (tonistiigi/binfmt --version):"
)
# No Windows PowerShell 5.1, "2>&1" em comando nativo vira erro com "Stop" (o docker escreve o
# progresso do download no stderr); por isso este trecho roda com "Continue", como o "|| echo" do e4.sh.
$linhas += & {
    $ErrorActionPreference = "Continue"
    $saida = (docker run --rm --privileged tonistiigi/binfmt --version 2>&1 | ForEach-Object { "$_" } | Out-String).Trim()
    if ($LASTEXITCODE -eq 0) { $saida } else { "(não foi possível consultar)" }
}
[IO.File]::WriteAllLines("$PWD/results/ambiente/host.txt", $linhas)

Rodar docker build --platform linux/amd64 -t borda-prep -f docker/Dockerfile.host docker
Rodar docker build --platform linux/amd64 -t borda-edgetpu -f docker/Dockerfile.edgetpu docker
Rodar docker build --platform linux/arm64 -t borda-arm64 -f docker/Dockerfile.arm64 docker

Write-Host "== [2/5] Preparação dos modelos"
Rodar docker run --rm --platform linux/amd64 @montagem borda-prep bash src/prepare/preparar.sh $zero
Write-Host "== [3/5] Edge TPU Compiler"
Rodar docker run --rm --platform linux/amd64 @montagem borda-edgetpu bash src/prepare/compilar_edgetpu.sh
Write-Host "== [4/5] Validação e teste de fumaça em ARM64 (perfil $Perfil)"
Rodar docker run --rm --platform linux/arm64 @limites @montagem borda-arm64 sh -c "python src/bench/validar_modelo.py && python src/bench/fumaca_benchmark.py"
Write-Host "== [5/5] CSV do compilador e docs/ambiente.md"
Rodar docker run --rm --platform linux/amd64 @montagem borda-prep sh -c "python3 src/prepare/extrair_logs_edgetpu.py && python3 src/prepare/registrar_ambiente.py"
Write-Host "E4 concluída. Veja results/ e docs/ambiente.md."
