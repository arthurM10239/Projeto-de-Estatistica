# Focos de calor, clima e desmatamento no Pará

Dashboard interativo que relaciona focos de queimada no estado do Pará com
variáveis climáticas, fase do El Niño/La Niña e incremento de desmatamento,
entre 2015 e 2026.

Trabalho da disciplina de Estatística — Engenharia de Computação, CESUPA.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Pandas](https://img.shields.io/badge/pandas-2.x-150458)
![Streamlit](https://img.shields.io/badge/Streamlit-1.50%2B-FF4B4B)
![GeoPandas](https://img.shields.io/badge/GeoPandas-1.x-139C5A)

---

## Sobre o projeto

A Amazônia concentra a maior parte dos focos de queimada do Brasil, e o Pará
lidera o incremento de desmatamento entre os estados da Amazônia Legal. O fogo
na região é quase sempre iniciado por ação humana, mas a sua propagação depende
de condições climáticas — temperatura, chuva e umidade — que variam com o ciclo
El Niño/La Niña (ENSO).

Este projeto reúne quatro fontes públicas independentes numa base única por
município e mês, e expõe essas variáveis num dashboard com filtros, para que o
usuário explore as relações por conta própria.

O recorte cobre **2015 a 2025 completos** e **2026 parcial** (janeiro a
setembro), período que inclui dois eventos fortes de El Niño já encerrados
(2015–16 e 2023–24) e o evento em curso.

### Perguntas que o dashboard permite explorar

- Como os focos de calor se distribuem ao longo do ano e entre os anos?
- Os meses classificados como El Niño apresentam distribuição de focos
  diferente dos meses neutros ou de La Niña?
- Qual a relação entre focos e cada variável climática, com e sem o efeito da
  sazonalidade?
- Onde os focos se concentram geograficamente?
- Como desmatamento e focos se comportam ao longo dos ciclos do PRODES?

O dashboard não apresenta conclusões. Os títulos e rótulos são descritivos e a
leitura dos padrões fica a cargo de quem usa.

---

## Capturas de tela

> Substituir pelos prints do dashboard depois da primeira execução.

| Aba Mensal | Aba Anual |
|---|---|
| `docs/mensal.png` | `docs/anual.png` |

---

## Fontes de dados

| Fonte | O que fornece | Granularidade | Obtenção |
|---|---|---|---|
| [INPE / BDQueimadas](https://terrabrasilis.dpi.inpe.br/queimadas/bdqueimadas/) | focos de calor, satélite de referência AQUA_M-T | ponto / diária | manual |
| [INPE / PRODES](https://terrabrasilis.dpi.inpe.br/downloads/) | incremento anual de desmatamento (shapefile) | polígono / anual | manual |
| [NASA POWER](https://power.larc.nasa.gov/) | temperatura, precipitação e umidade | ponto / diária | automática |
| [NOAA CPC](https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt) | índice ONI (fase do ENSO) | trimestre móvel | automática |
| [IBGE](https://servicodados.ibge.gov.br/api/docs/localidades) | municípios, centroides, áreas e malha territorial | município | automática |

Nenhum dado é versionado neste repositório. Veja [Obtendo os dados](#obtendo-os-dados).

---

## Stack

- **pandas** — tratamento, junção e agregação das bases
- **GeoPandas / pyogrio** — cruzamento dos polígonos do PRODES com a malha municipal
- **Streamlit** — interface do dashboard
- **Plotly** — gráficos interativos
- **requests** — consumo das APIs

---

## Instalação

Requer Python 3.10 ou superior.

```bash
git clone <url-do-repositorio>
cd projeto_queimadas

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

python -m pip install -r requirements.txt
```

No VS Code: `Ctrl+Shift+P` → `Python: Select Interpreter` → selecionar o `.venv`.

> O ambiente virtual não é substituído pelo Git. O repositório versiona o
> código; o `.venv` guarda as bibliotecas instaladas. Cada máquina cria o seu,
> e o `requirements.txt` é o que garante versões iguais entre os integrantes.

---

## Obtendo os dados

A pasta `dados/` está no `.gitignore`: os arquivos brutos somam mais de 1 GB e
o GitHub recusa arquivos acima de 100 MB. Cada integrante baixa a sua cópia.

### 1. Focos de calor (manual)

No [BDQueimadas](https://terrabrasilis.dpi.inpe.br/queimadas/bdqueimadas/),
exportar **um arquivo por ano** com os filtros:

- Estado: **Pará**
- Satélite: **satélite de referência (AQUA_M-T)**
- Período: 01/01 a 31/12, de 2015 a 2025
- Para 2026: 01/01/2026 a 30/09/2026
- **Sem** filtro de bioma

Salvar os `.csv` ou `.zip` em `dados/brutos/focos/`.

Conferir a contagem de cada ano no
[painel de estatísticas do INPE](https://data.inpe.br/queimadas/estatisticas/?tipo=estados).

### 2. Desmatamento (manual)

Na [área de downloads do TerraBrasilis](https://terrabrasilis.dpi.inpe.br/downloads/),
baixar **Incremento anual no desmatamento — Shapefile (desde 2008)** e colocar
o `.zip` em `dados/brutos/prodes_shapefile/`, **sem descompactar**.

Conferir os totais anuais no
[dashboard de incrementos](https://terrabrasilis.dpi.inpe.br/app/dashboard/deforestation/biomes/legal_amazon/increments).

### 3. Demais fontes (automático)

Clima, índice ONI e dados do IBGE são baixados pelo próprio script e ficam em
cache em `dados/brutos/`.

---

## Execução

```bash
python coleta/executar_coleta.py
python -m streamlit run dashboard/app.py
```

A coleta faz 144 requisições à API da NASA POWER com intervalo entre elas, e
cruza os polígonos do PRODES com a malha municipal. Conte com algumas dezenas
de minutos na primeira execução. Tudo fica em cache, então execuções seguintes
retomam de onde pararam.

### Saídas

| Arquivo | Conteúdo |
|---|---|
| `dados/tratados/base_mensal.csv` | município × mês: focos, clima, anomalia ONI, fase do ENSO |
| `dados/tratados/base_anual_prodes.csv` | município × ciclo PRODES: focos, clima agregado, desmatamento |

---

## Estrutura

```
coleta/
  configuracao.py       parâmetros do recorte, caminhos e URLs
  utilidades.py         normalização de nomes e requisições com retentativa
  municipios.py         lista, centroides, áreas e malha do IBGE
  focos.py              leitura e contagem dos focos por município e mês
  clima.py              download e agregação mensal das variáveis climáticas
  enso.py               índice ONI e classificação das fases
  desmatamento.py       cruzamento dos polígonos do PRODES com os municípios
  montagem.py           junção das fontes nas duas bases finais
  executar_coleta.py    orquestra a coleta completa
dashboard/
  preparacao.py         carregamento, filtros e agregações
  graficos.py           construção das figuras
  app.py                interface Streamlit
dados/
  brutos/               fontes originais (não versionado)
  tratados/             bases prontas para análise (não versionado)
```

---

## Visualizações

| # | Visualização | Objetivo analítico |
|---|---|---|
| 1 | Indicadores do recorte | ordem de grandeza antes dos gráficos |
| 2 | Série temporal de focos, colorida por fase do ENSO | tendência |
| 3 | Boxplot de focos por mês do ano | distribuição e sazonalidade |
| 4 | Boxplot de focos por fase do ENSO | comparação entre grupos |
| 5 | Dispersão clima × focos, com Spearman | relação entre variáveis |
| 6 | Mapa coroplético por município | distribuição espacial |
| 7 | Desmatamento e focos por ciclo PRODES, em painéis separados | tendência |
| 8 | Dispersão desmatamento × focos por município-ano | relação entre variáveis |

---

## Decisões de tratamento

| Decisão | Justificativa |
|---|---|
| Apenas o satélite AQUA_M-T | é o satélite de referência do INPE; misturar satélites infla artificialmente a série ao longo do tempo |
| Leitura em UTF-8 | em `latin-1`, nomes como Belém, Óbidos e Bragança são corrompidos e perdidos na junção, sem erro aparente |
| Mês sem foco registrado vira `0` | ausência de detecção é informação, não dado faltante |
| Focos normalizados por 1000 km² | sem normalizar, municípios extensos como Altamira dominam a análise apenas pelo tamanho |
| Ciclo PRODES de agosto a julho | é o ano de referência do PRODES, que não coincide com o ano civil |
| Áreas calculadas em ESRI:102033 | projeção de área equivalente; calcular área em coordenadas geográficas produz valores incorretos |
| Clima ponderado pela área municipal | ao agregar municípios, um município pequeno não pode pesar igual a um grande |
| Correlação de Spearman | a contagem de focos é assimétrica e contém outliers; Spearman não assume relação linear |
| Opção de desvio da média do mês | remove o efeito sazonal, que infla a correlação bruta entre clima e focos |
| Fase do ENSO: ±0,5 °C por 5 trimestres consecutivos | critério da NOAA; o evento em curso em 2026 é aceito sem completar os 5 trimestres |
| Ano parcial marcado em `ano_completo` | comparar 2026 parcial com anos fechados é erro metodológico; é preciso filtrar os mesmos meses |

---

## Limitações

- **Foco de calor não é área queimada.** Um incêndio extenso gera múltiplos
  focos e a cobertura de nuvens impede detecções.
- **O clima vem do centroide do município**, uma aproximação grosseira em
  municípios de grande extensão.
- **O satélite Aqua é antigo** e sua órbita vem derivando, o que pode afetar a
  comparabilidade dos anos mais recentes. Consultar a
  [página de avisos do Programa Queimadas](https://data.inpe.br/queimadas/avisos/)
  antes de concluir sobre tendências recentes.
- **Observações do mesmo município ao longo dos anos não são independentes**
  entre si.
- **Correlação não implica causalidade.** Desmatamento, fiscalização e política
  ambiental variam no mesmo período que o clima, e o desenho observacional deste
  projeto não permite separar esses efeitos.

---

## Autores

- Ian de Azevedo Mendes
- *(completar com o nome da dupla)*

Centro Universitário do Estado do Pará (CESUPA) — Engenharia de Computação.

---

## Licença

Projeto acadêmico. Os dados pertencem às instituições de origem (INPE, NASA,
NOAA e IBGE) e seguem as respectivas políticas de uso.
