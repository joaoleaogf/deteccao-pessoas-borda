# Artigo no template do IMC/UNIFEI

O artigo segue o "Template LaTeX para Artigo" da disciplina (Overleaf, classe `imc.cls`). O template
não tem licença de redistribuição, por isso **não está neste repositório**: aqui fica só o conteúdo do
trabalho, e o script de montagem junta os dois.

| Caminho | O que é |
|---|---|
| `overleaf/configuracao.tex` | autores, título, professor, palavras-chave, textos de capa e o marcador `\pendente{}` |
| `overleaf/elemtextuais/` | resumo e seções 1 a 5 (nomes que o `main.tex` do template já inclui) e agradecimentos |
| `overleaf/referencias.bib` | só referências conferidas (arXiv, CITATION.cff da Ultralytics, páginas oficiais) |
| `numeros.tex` | macros com todos os números citados no texto, geradas dos dados por `src/analysis/artigo_tex.py` |
| `tabelas/*.tex` | tabelas geradas pelo mesmo script |

## Montar e compilar

1. Baixe o template de artigo da disciplina e deixe os arquivos em `data/template_artigo_imc/`
   (`imc.cls`, `apalike2_ptBR.bst`, `main.tex`, `config/`).
2. Rode `e6.ps1` ou `e6.sh` se os dados mudaram (atualiza `numeros.tex`, tabelas e figuras).
3. `python src/analysis/montar_overleaf.py` gera `build/artigo_overleaf/` e `build/artigo_overleaf.zip`
   (no Overleaf: New Project > Upload Project). O script só troca a sigla do curso no `main.tex`
   (`--curso sin`, padrão) e não altera a classe.
4. Para compilar sem instalar TeX: `docker run --rm -v "$PWD/build/artigo_overleaf:/doc" -w /doc
   texlive/texlive:latest latexmk -pdf main.tex`.

## O que a equipe ainda precisa preencher (marcado em vermelho no PDF)

- Seção 2: texto da revisão e trabalhos relacionados (T1 a T7), com as referências completas no `.bib`.
- Introdução: detalhes da busca sistemática e conferência das hipóteses H1 e H2 com a proposta.
- Citações de T1 e T2 na justificativa e na discussão.
- Fonte para o RTT de 40 ms e a subida de 10 Mbit/s da nuvem.
- E-mails dos autores, data da apresentação e agradecimentos.
- Avisos de "Overfull hbox" na linha 27 do `main.tex` vêm da capa gerada pela própria classe.
