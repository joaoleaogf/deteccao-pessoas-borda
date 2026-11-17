# Material de apoio para o artigo

Rascunhos e tabelas gerados a partir dos dados da E5/E6. O texto final do artigo e a apresentação
continuam com a equipe.

| Arquivo | O que é | Como é feito |
|---|---|---|
| `metodologia.tex` | rascunho da seção de metodologia (ARM64 nativo, amostragem reduzida, limitações) | escrito à mão, sem números digitados |
| `resultados.tex` | rascunho da seção de resultados | escrito à mão; todo valor vem de uma macro |
| `numeros.tex` | macros com os números citados (`\mapYoloFpSeis`, `\etoeSsdIntTres`, `\bandaSeisTrinta`...) | gerado por `src/analysis/artigo_tex.py` |
| `tabelas/*.tex` | tabelas de qualidade, latência na borda, testes FP32 × INT8, nuvem e Edge TPU | geradas por `src/analysis/artigo_tex.py` |

Uso no LaTeX do artigo: `\input{numeros.tex}` no preâmbulo e `\input{metodologia}` /
`\input{resultados}` no corpo (as figuras são lidas de `../../figures/`; ajuste o caminho se copiar os
arquivos para outro lugar). Para atualizar depois de refazer a coleta, rode `e6.ps1` ou `e6.sh`.

Nome das macros: `\<métrica><Modelo><Precisão><Resolução>[<FPS>][Nuvem]`, com Modelo = Yolo, Ssd ou
Effdet; Precisão = Fp ou Int; Resolução = Tres (320), Quatro (480) ou Seis (640); FPS = Cinco, Quinze ou
Trinta. Métricas: `map` (mAP@50), `etoe` (latência fim a fim, ms), `fps` (taxa sustentável), `razao`
(FP32/INT8), `cpu` (%), `rss` (MB sem os quadros pré-carregados), `desc` (% de quadros descartados),
`banda` (Mbit/s de subida na nuvem).

Pontos que a equipe ainda precisa resolver antes de submeter: fonte para o RTT e a banda de subida da
nuvem (D5), potência de referência para a energia (D7) e a justificativa da amostragem reduzida (D8).
