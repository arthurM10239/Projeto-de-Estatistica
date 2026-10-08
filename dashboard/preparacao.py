import json
from pathlib import Path
import pandas as pd
import streamlit as st

# Definição dos caminhos dos arquivos baseando-se no diretório atual do script (PASTA_RAIZ)
PASTA_RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_BASE_MENSAL = PASTA_RAIZ / "dados" / "tratados" / "base_mensal.csv"
ARQUIVO_BASE_ANUAL = PASTA_RAIZ / "dados" / "tratados" / "base_anual_prodes.csv"
ARQUIVO_MALHA = PASTA_RAIZ / "dados" / "brutos" / "malha_municipios_para.geojson"

# Dicionário para converter o número do mês (1 a 12) em sua abreviação em texto
NOMES_MESES = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}

# Lista que define a ordem exata em que as fases do fenômeno ENSO devem aparecer nos gráficos
ORDEM_FASES_ENSO = ["La Niña", "Neutro", "El Niño"]

# Dicionário relacionando o nome da coluna no arquivo CSV com o rótulo amigável para exibição na tela
VARIAVEIS_CLIMATICAS = {
    "temperatura_maxima_media_c": "Temperatura máxima média (°C)",
    "temperatura_media_c": "Temperatura média (°C)",
    "precipitacao_total_mm": "Precipitação total (mm)",
    "umidade_relativa_media_pct": "Umidade relativa média (%)",
    "anomalia_oni": "Anomalia ONI (°C)",
}

# Lista de variáveis climáticas que precisam ter sua média calculada proporcionalmente ao tamanho do município
VARIAVEIS_PONDERADAS_POR_AREA = [
    "temperatura_maxima_media_c",
    "temperatura_media_c",
    "precipitacao_total_mm",
    "umidade_relativa_media_pct",
]

# Dicionário com as opções de métricas de focos de calor disponíveis para o usuário escolher
METRICAS_FOCOS = {
    "Quantidade de focos": "quantidade_focos",
    "Focos por 1000 km²": "focos_por_1000_km2",
}

# guarda o resultado da função na memória para não ler o CSV toda vez que a tela atualizar
@st.cache_data
def carregar_base_mensal():
    # Verifica se o arquivo existe; se não, retorna vazio para não quebrar o código
    if not ARQUIVO_BASE_MENSAL.exists():
        return None
    
    # Lê o arquivo CSV transformando-o em um DataFrame (tabela) do Pandas
    base = pd.read_csv(ARQUIVO_BASE_MENSAL)
    
    # Cria uma nova coluna chamada "data" combinando as colunas "ano" e "mes" e fixando o dia 1, formato DateTime
    base["data"] = pd.to_datetime({"year": base["ano"], "month": base["mes"], "day": 1})
    return base

# carrega os dados anuais (ciclos do PRODES)
@st.cache_data
def carregar_base_anual():
    if not ARQUIVO_BASE_ANUAL.exists():
        return None
    return pd.read_csv(ARQUIVO_BASE_ANUAL)

# Decorador de cache para carregar o arquivo geográfico com os contornos dos municípios do Pará
@st.cache_data
def carregar_malha_municipios():
    if not ARQUIVO_MALHA.exists():
        return None
    # Abre o arquivo JSON, lê como texto codificado em utf-8 e converte para dicionário Python
    return json.loads(ARQUIVO_MALHA.read_text(encoding="utf-8"))

# Verifica quais variáveis climáticas estão efetivamente presentes nos dados carregados
def listar_variaveis_climaticas_disponiveis(base):
    # Retorna um dicionário filtrado apenas com as colunas que constam na tabela base
    return {coluna: rotulo for coluna, rotulo in VARIAVEIS_CLIMATICAS.items() if coluna in base.columns}

# Filtra a tabela mensal com base nas opções escolhidas nos menus laterais
def filtrar_base_mensal(base, intervalo_anos, intervalo_meses, codigos_municipios, fases_enso):
    # Cria uma máscara (True/False) verificando limites de anos, meses e fases ENSO permitidas
    selecao = (
        base["ano"].between(*intervalo_anos)
        & base["mes"].between(*intervalo_meses)
        & base["fase_enso"].isin(fases_enso)
    )
    
    # Se o usuário tiver selecionado municípios específicos, adiciona essa regra à máscara de filtro
    if codigos_municipios:
        selecao &= base["codigo_ibge"].isin(codigos_municipios)
        
    # Retorna apenas as linhas da tabela onde a máscara for verdadeira
    return base[selecao]

# Filtra a tabela anual do PRODES seguindo a mesma lógica de máscara condicional
def filtrar_base_anual(base_anual, intervalo_anos, codigos_municipios):
    selecao = base_anual["ano_prodes"].between(*intervalo_anos)
    if codigos_municipios:
        selecao &= base_anual["codigo_ibge"].isin(codigos_municipios)
    return base_anual[selecao]

# Agrupa os dados de vários municípios para gerar uma visão estadual/regional somada por mês
def agregar_por_mes(base_filtrada):
    base_ponderada = base_filtrada.copy()