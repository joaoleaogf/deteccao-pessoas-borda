# Artigo da disciplina (projeto Overleaf da equipe)

O artigo usa o projeto Overleaf da equipe, com a classe da disciplina (`PioliEdgeComp.cls`). O texto do
artigo (`docs/artigo/equipe/`), a classe, o estilo `.bst` e o logotipo **não estão neste repositório**:
ficam no PC da equipe e no Overleaf. Aqui ficam o que sai dos dados (macros, tabelas e figuras em
pgfplots) e o script que monta o projeto.

| Caminho | O que é |
|---|---|
| `equipe/main.tex`, `equipe/configuracao.tex` | estrutura e dados do artigo (acrescenta `\input{numeros}`, o marcador `\pendente{}` e as conclusões) |
| `equipe/elemtextuais/` | resumo e seções 1 a 7 (1 e 2 da equipe, revisadas; 3 a 7 com o experimento) |
| `equipe/referencias.bib` | referências da equipe (DOI do Reducto corrigido) e três de ferramentas |
| `equipe/figs/` | figuras da equipe (com as fontes TikZ em `figs/src/`) |
| `numeros.tex`, `tabelas/*.tex` | números e tabelas gerados dos dados por `src/analysis/artigo_tex.py` |

## Montar e compilar

1. Descompacte o projeto Overleaf da equipe em `data/projeto_equipe/` (precisa de `PioliEdgeComp.cls`,
   `apalike2_ptBR.bst`, `config/` e `figs/`).
2. Rode `e6.ps1` ou `e6.sh` se os dados mudaram.
3. `python src/analysis/montar_overleaf.py` gera `build/artigo_equipe/` e `build/artigo_equipe.zip`, com
   a mesma estrutura do projeto da equipe (para substituir os arquivos no Overleaf).
4. Sem TeX instalado: `docker run --rm -v "$PWD/build/artigo_equipe:/doc" -w /doc texlive/texlive:latest
   latexmk -pdf main.tex`.

## Pendências marcadas em vermelho no PDF

- Confirmar a lista de bases do mapeamento (os slides registram "Scopus sem acesso").
- Conferir as hipóteses H1 e H2 com a proposta.
- Fonte para o RTT de 40 ms e a subida de 10 Mbit/s da nuvem.
