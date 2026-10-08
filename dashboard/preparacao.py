# Importação de bibliotecas nativas do Python para manipulação de arquivos e dados em formato JSON
import json
from pathlib import Path

# Importação da biblioteca Pandas para manipulação de tabelas de dados e Streamlit para o uso de cache
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

# Decorador do Streamlit que guarda o resultado da função na memória (cache) para não ler o CSV toda vez que a tela atualizar
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

# Decorador de cache para carregar os dados anuais (ciclos do PRODES)
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
    
    # Define como as colunas padrões serão agregadas (somando a quantidade e a área)
    colunas_soma = {"quantidade_focos": "sum", "area_km2": "sum"}
    
    # Identifica as colunas de clima presentes na base
    variaveis_presentes = [v for v in VARIAVEIS_PONDERADAS_POR_AREA if v in base_ponderada.columns]
    
    # Estratégia matemática para fazer "Média Ponderada" do clima com base no tamanho (área) da cidade
    for variavel in variaveis_presentes:
        # Pega a área do município apenas se ele tiver dados de clima (se não, zera)
        area_valida = base_ponderada["area_km2"].where(base_ponderada[variavel].notna(), 0)
        
        # Multiplica o dado climático pela área da cidade
        base_ponderada[f"{variavel}_x_area"] = base_ponderada[variavel].fillna(0) * area_valida
        base_ponderada[f"{variavel}_area_valida"] = area_valida
        
        # Diz para o Pandas somar essas multiplicações depois no 'groupby'
        colunas_soma[f"{variavel}_x_area"] = "sum"
        colunas_soma[f"{variavel}_area_valida"] = "sum"
        
    # Agrupa a tabela inteira por Mês, Ano e índices climáticos globais
    agregado = (
        base_ponderada.groupby(["data", "ano", "mes", "anomalia_oni", "fase_enso"], dropna=False)
        .agg(colunas_soma)
        .reset_index()
    )
    
    # Finaliza a média ponderada dividindo a soma dos (valores * áreas) pela soma total das áreas
    for variavel in variaveis_presentes:
        agregado[variavel] = agregado[f"{variavel}_x_area"] / agregado[f"{variavel}_area_valida"].replace(0, pd.NA)
        
    # Calcula a métrica de focos proporcional ao tamanho da área (densidade)
    agregado["focos_por_1000_km2"] = agregado["quantidade_focos"] / agregado["area_km2"] * 1000
    
    # Converte o número do mês para o nome abreviado (ex: 1 virar "Jan")
    agregado["nome_mes"] = agregado["mes"].map(NOMES_MESES)
    
    # Limpa a tabela, removendo colunas temporárias matemáticas e deixando só o que importa
    colunas_finais = [
        "data", "ano", "mes", "nome_mes", "anomalia_oni", "fase_enso",
        "quantidade_focos", "focos_por_1000_km2", *variaveis_presentes,
    ]
    return agregado[colunas_finais].sort_values("data").reset_index(drop=True)

# Calcula se os valores climáticos estão acima ou abaixo da média histórica do respectivo mês
def calcular_desvio_da_media_do_mes(agregado_mensal, colunas):
    desvios = agregado_mensal.copy()
    for coluna in colunas:
        # Pega o valor absoluto e subtrai pela média de todos os outros valores do mesmo mês ("mes")
        desvios[coluna] = desvios[coluna] - desvios.groupby("mes")[coluna].transform("mean")
    return desvios

# Prepara a base agregando os focos totais de cada município no período inteiro para plotar no mapa
def agregar_por_municipio(base_filtrada):
    agregado = (
        base_filtrada.groupby(["codigo_ibge", "nome_municipio"])
        # Soma a quantidade de focos e pega apenas a primeira (first) informação da área
        .agg(quantidade_focos=("quantidade_focos", "sum"), area_km2=("area_km2", "first"))
        .reset_index()
    )
    # Calcula a densidade de focos baseando-se no novo total somado e no tamanho do município
    agregado["focos_por_1000_km2"] = agregado["quantidade_focos"] / agregado["area_km2"] * 1000
    
    # O mapa coroplético exige que a chave de ligação (IBGE) seja um texto (String), não um número
    agregado["codigo_ibge_texto"] = agregado["codigo_ibge"].astype(str)
    return agregado

# Soma os indicadores anuais agrupando pelo ciclo PRODES (que vai de Agosto de um ano a Julho do outro)
def agregar_por_ciclo_prodes(base_anual_filtrada):
    agregado = (
        base_anual_filtrada.groupby("ano_prodes")
        .agg(
            quantidade_focos=("quantidade_focos", "sum"),
            desmatamento_km2=("desmatamento_km2", "sum"),
            area_km2=("area_km2", "sum"),
        )
        .reset_index()
    )
    # Recalcula a densidade por 1000km² após a soma dos valores do ciclo
    agregado["focos_por_1000_km2"] = agregado["quantidade_focos"] / agregado["area_km2"] * 1000
    return agregado