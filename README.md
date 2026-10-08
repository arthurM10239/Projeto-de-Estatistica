# Focos de calor, clima e desmatamento no Pará (2015–2026)

Projeto da disciplina de Estatística. Relaciona focos de queimada no Pará com
variáveis climáticas, fase do El Niño/La Niña e desmatamento.

Recorte: 2015 a 2025 completos, mais 2026 parcial (janeiro a setembro).

## 1. Instalar

Precisa de Python 3.10 ou mais novo.

```
python -m venv .venv
.venv\Scripts\activate          (Windows)
source .venv/bin/activate       (macOS / Linux)
python -m pip install -r requirements.txt
```

No VS Code: `Ctrl+Shift+P` -> `Python: Select Interpreter` -> escolher o `.venv`.

## 2. Baixar os dados brutos

Nada é versionado: a pasta `dados/` começa vazia e cada um baixa a sua cópia.

### 2.1 Focos de calor (manual)

Portal: https://terrabrasilis.dpi.inpe.br/queimadas/bdqueimadas/

Exportar **um arquivo por ano**, com estes filtros:

- Estado: Pará
- Satélite: satélite de referência (AQUA_M-T)
- Período: 01/01 a 31/12 de cada ano, de 2015 a 2025
- Para 2026: de 01/01/2026 a 30/09/2026
- Não marcar filtro de bioma

Salvar os `.csv` ou `.zip` em `dados/brutos/focos/`. O script lê todos os
arquivos dessa pasta de uma vez, em qualquer um dos dois formatos de coluna
que o INPE usa.

Conferir a contagem de cada ano em
https://data.inpe.br/queimadas/estatisticas/?tipo=estados

### 2.2 Desmatamento (manual)

Portal: https://terrabrasilis.dpi.inpe.br/downloads/

Baixar **Incremento anual no desmatamento - Shapefile (desde 2008)** e colocar
o `.zip` em `dados/brutos/prodes_shapefile/`, **sem descompactar**.

Conferir os totais por ano em
https://terrabrasilis.dpi.inpe.br/app/dashboard/deforestation/biomes/legal_amazon/increments

### 2.3 Automáticos

O script baixa sozinho, e guarda em `dados/brutos/`:

- municípios, centroides, áreas e malha do Pará (API do IBGE)
- clima diário por município (NASA POWER)
- índice ONI (NOAA CPC)

## 3. Trabalhando em dupla pelo GitHub

O `.gitignore` deixa `dados/` de fora do repositório de propósito: os CSV de
focos, o shapefile do PRODES e o cache da NASA POWER passam de 1 GB juntos, e o
GitHub recusa arquivo acima de 100 MB. Só o código vai para o repositório, uns
90 KB. Cada um baixa a sua cópia dos dados brutos e roda a coleta na própria
máquina. As pastas vazias continuam no repositório por causa dos `.gitkeep`.

Se algum arquivo grande for commitado por engano, ele fica no histórico mesmo
depois de apagado, e limpar isso dá trabalho. Antes do primeiro `push`, confira
com `git status` que nada de `dados/` aparece.

O ambiente virtual (`.venv/`) também fica fora do repositório. Ele não é
substituído pelo Git: o repositório guarda o código, o `.venv` guarda as
bibliotecas instaladas. Cada máquina cria o seu, e o `requirements.txt` é o que
garante que os dois tenham as mesmas versões.

## 4. Rodar

```
python coleta/executar_coleta.py
python -m streamlit run dashboard/app.py
```

A coleta demora: são 144 requisições à NASA POWER, com pausa entre elas, mais
o cruzamento dos polígonos do PRODES. Tudo que ela baixa fica em cache, então
rodar de novo é rápido e continua de onde parou.

Saída em `dados/tratados/`:

- `base_mensal.csv` — município x mês, com focos, clima e fase do ENSO
- `base_anual_prodes.csv` — município x ciclo PRODES, com focos e desmatamento

## 5. Estrutura

```
coleta/
  configuracao.py   parâmetros do recorte, caminhos e URLs
  utilidades.py     normalização de nomes e requisições com retentativa
  municipios.py     lista, centroides, áreas e malha do IBGE
  focos.py          leitura e contagem dos focos por município e mês
  clima.py          download e agregação mensal do clima
  enso.py           índice ONI e classificação das fases
  desmatamento.py   cruzamento dos polígonos do PRODES com os municípios
  montagem.py       junção das fontes nas duas bases finais
  executar_coleta.py  roda tudo na ordem
dashboard/
  preparacao.py     carregamento, filtros e agregações
  graficos.py       as sete figuras
  app.py            a interface Streamlit
```

## 6. Decisões de tratamento

| Decisão | Motivo |
|---|---|
| Só o satélite AQUA_M-T | é o satélite de referência do INPE; misturar satélites infla a série ao longo do tempo |
| Leitura em UTF-8 | em latin-1, Belém, Óbidos e Bragança são corrompidos e somem na junção |
| Mês sem foco vira 0 | não detectar foco é informação, não é dado faltando |
| Focos por 1000 km² | sem normalizar, Altamira e São Félix do Xingu dominam só pelo tamanho |
| Ciclo PRODES de agosto a julho | é o ano de referência do PRODES, não o ano civil |
| Área em ESRI:102033 | projeção de área equivalente; calcular área em latitude/longitude dá valor errado |
| Clima ponderado pela área | ao somar municípios, um município pequeno não pode pesar igual a um grande |
| Correlação de Spearman | a contagem de focos é assimétrica e tem outliers; Spearman não assume relação linear |
| Fase do ENSO: ±0,5 °C por 5 trimestres | critério da NOAA; o evento em curso em 2026 entra mesmo sem fechar os 5 |
| 2026 separado por `ano_completo` | comparar ano parcial com anos fechados é erro; filtrar os mesmos meses |

## 7. Limitações a assumir na defesa

- Foco de calor não é área queimada: um incêndio grande gera vários focos e nuvem esconde foco.
- O clima vem do centroide do município, o que é uma aproximação grosseira em municípios enormes.
- O Aqua é um satélite antigo e sua órbita vem derivando; conferir a página de
  avisos do INPE antes de concluir qualquer coisa sobre os anos mais recentes.
- Os pontos de um mesmo município ao longo dos anos não são independentes entre si.
- Correlação não é causa: desmatamento, fiscalização e política ambiental mudam junto com o clima.

## 8. Fontes

- INPE / BDQueimadas — focos de calor
- INPE / PRODES — incremento de desmatamento
- NASA POWER — temperatura, precipitação e umidade
- NOAA CPC — índice ONI
- IBGE — municípios, áreas e malha territorial
