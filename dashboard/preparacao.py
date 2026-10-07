import json
from pathlib import Path

import pandas as pd
import streamlit as st

PASTA_RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_BASE_MENSAL = PASTA_RAIZ / "dados" / "tratados" / "base_mensal.csv"
ARQUIVO_BASE_ANUAL = PASTA_RAIZ / "dados" / "tratados" / "base_anual_prodes.csv"
ARQUIVO_MALHA = PASTA_RAIZ / "dados" / "brutos" / "malha_municipios_para.geojson"

NOMES_MESES = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}

ORDEM_FASES_ENSO = ["La Niña", "Neutro", "El Niño"]

VARIAVEIS_CLIMATICAS = {
    "temperatura_maxima_media_c": "Temperatura máxima média (°C)",
    "temperatura_media_c": "Temperatura média (°C)",
    "precipitacao_total_mm": "Precipitação total (mm)",
    "umidade_relativa_media_pct": "Umidade relativa média (%)",
    "anomalia_oni": "Anomalia ONI (°C)",
}

VARIAVEIS_PONDERADAS_POR_AREA = [
    "temperatura_maxima_media_c",
    "temperatura_media_c",
    "precipitacao_total_mm",
    "umidade_relativa_media_pct",
]

METRICAS_FOCOS = {
    "Quantidade de focos": "quantidade_focos",
    "Focos por 1000 km²": "focos_por_1000_km2",
}


@st.cache_data
def carregar_base_mensal():
    if not ARQUIVO_BASE_MENSAL.exists():
        return None
    base = pd.read_csv(ARQUIVO_BASE_MENSAL)
    base["data"] = pd.to_datetime({"year": base["ano"], "month": base["mes"], "day": 1})
    return base


@st.cache_data
def carregar_base_anual():
    if not ARQUIVO_BASE_ANUAL.exists():
        return None
    return pd.read_csv(ARQUIVO_BASE_ANUAL)


@st.cache_data
def carregar_malha_municipios():
    if not ARQUIVO_MALHA.exists():
        return None
    return json.loads(ARQUIVO_MALHA.read_text(encoding="utf-8"))


def listar_variaveis_climaticas_disponiveis(base):
    return {coluna: rotulo for coluna, rotulo in VARIAVEIS_CLIMATICAS.items() if coluna in base.columns}


def filtrar_base_mensal(base, intervalo_anos, intervalo_meses, codigos_municipios, fases_enso):
    selecao = (
        base["ano"].between(*intervalo_anos)
        & base["mes"].between(*intervalo_meses)
        & base["fase_enso"].isin(fases_enso)
    )
    if codigos_municipios:
        selecao &= base["codigo_ibge"].isin(codigos_municipios)
    return base[selecao]


def filtrar_base_anual(base_anual, intervalo_anos, codigos_municipios):
    selecao = base_anual["ano_prodes"].between(*intervalo_anos)
    if codigos_municipios:
        selecao &= base_anual["codigo_ibge"].isin(codigos_municipios)
    return base_anual[selecao]


def agregar_por_mes(base_filtrada):
    base_ponderada = base_filtrada.copy()
    colunas_soma = {"quantidade_focos": "sum", "area_km2": "sum"}
    variaveis_presentes = [v for v in VARIAVEIS_PONDERADAS_POR_AREA if v in base_ponderada.columns]
    for variavel in variaveis_presentes:
        area_valida = base_ponderada["area_km2"].where(base_ponderada[variavel].notna(), 0)
        base_ponderada[f"{variavel}_x_area"] = base_ponderada[variavel].fillna(0) * area_valida
        base_ponderada[f"{variavel}_area_valida"] = area_valida
        colunas_soma[f"{variavel}_x_area"] = "sum"
        colunas_soma[f"{variavel}_area_valida"] = "sum"
    agregado = (
        base_ponderada.groupby(["data", "ano", "mes", "anomalia_oni", "fase_enso"], dropna=False)
        .agg(colunas_soma)
        .reset_index()
    )
    for variavel in variaveis_presentes:
        agregado[variavel] = agregado[f"{variavel}_x_area"] / agregado[f"{variavel}_area_valida"].replace(0, pd.NA)
    agregado["focos_por_1000_km2"] = agregado["quantidade_focos"] / agregado["area_km2"] * 1000
    agregado["nome_mes"] = agregado["mes"].map(NOMES_MESES)
    colunas_finais = [
        "data", "ano", "mes", "nome_mes", "anomalia_oni", "fase_enso",
        "quantidade_focos", "focos_por_1000_km2", *variaveis_presentes,
    ]
    return agregado[colunas_finais].sort_values("data").reset_index(drop=True)


def calcular_desvio_da_media_do_mes(agregado_mensal, colunas):
    desvios = agregado_mensal.copy()
    for coluna in colunas:
        desvios[coluna] = desvios[coluna] - desvios.groupby("mes")[coluna].transform("mean")
    return desvios


def agregar_por_municipio(base_filtrada):
    agregado = (
        base_filtrada.groupby(["codigo_ibge", "nome_municipio"])
        .agg(quantidade_focos=("quantidade_focos", "sum"), area_km2=("area_km2", "first"))
        .reset_index()
    )
    agregado["focos_por_1000_km2"] = agregado["quantidade_focos"] / agregado["area_km2"] * 1000
    agregado["codigo_ibge_texto"] = agregado["codigo_ibge"].astype(str)
    return agregado


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
    agregado["focos_por_1000_km2"] = agregado["quantidade_focos"] / agregado["area_km2"] * 1000
    return agregado
