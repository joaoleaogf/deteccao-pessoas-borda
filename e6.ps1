# Etapa E6 (análise) no Windows (PowerShell + Docker Desktop). Faz o mesmo que e6.sh.
#
# Uso: .\e6.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Rodar {
    # Executa um comando externo e interrompe o script se ele falhar.
    & $args[0] $args[1..($args.Count - 1)]
    if ($LASTEXITCODE -ne 0) { throw "Falhou: $($args -join ' ')" }
}

$montagem = @("-v", "${PWD}:/repo", "-w", "/repo")
$py = "/opt/venv-export/bin/python"
Write-Host "== [1/3] Cenários derivados, qualidade e results/summary.csv"
Rodar docker run --rm --platform linux/amd64 @montagem borda-prep $py src/analysis/derivar_cenarios.py
Write-Host "== [2/3] Testes, figuras e results/RESUMO.md"
Rodar docker run --rm --platform linux/amd64 @montagem borda-prep $py src/analysis/estatistica.py
Write-Host "== [3/3] Tabelas e macros LaTeX para o artigo (docs/artigo/)"
Rodar docker run --rm --platform linux/amd64 @montagem borda-prep $py src/analysis/artigo_tex.py
Write-Host "E6 concluída. Veja results/RESUMO.md, results/stats/ e figures/."
