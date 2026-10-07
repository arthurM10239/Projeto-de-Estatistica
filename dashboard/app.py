import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import streamlit as st

from graficos import (
    grafico_distribuicao_por_fase,
    grafico_distribuicao_por_mes,
    grafico_evolucao_por_ciclo,
    grafico_mapa_municipios,
    grafico_relacao_clima_focos,
    grafico_relacao_desmatamento_focos,
    grafico_serie_temporal,
)
from preparacao import (
    METRICAS_FOCOS,
    NOMES_MESES,
    ORDEM_FASES_ENSO,
    agregar_por_ciclo_prodes,
    agregar_por_mes,
    agregar_por_municipio,
    calcular_desvio_da_media_do_mes,
    carregar_base_anual,
    carregar_base_mensal,
    carregar_malha_municipios,
    filtrar_base_anual,
    filtrar_base_mensal,
    listar_variaveis_climaticas_disponiveis,
)

st.set_page_config(page_title="Focos de calor, clima e desmatamento no Pará", layout="wide")

FONTES = (
    "Fontes: INPE (BDQueimadas, satélite de referência AQUA_M-T; PRODES), "
    "NASA POWER, NOAA CPC (índice ONI), IBGE."
)


def montar_filtros_laterais(base_mensal):
    st.sidebar.header("Filtros")
    ano_minimo, ano_maximo = int(base_mensal["ano"].min()), int(base_mensal["ano"].max())
    intervalo_anos = st.sidebar.slider("Período (anos)", ano_minimo, ano_maximo, (ano_minimo, ano_maximo))
    mes_inicial, mes_final = st.sidebar.select_slider(
        "Meses do ano", options=list(NOMES_MESES), value=(1, 12), format_func=NOMES_MESES.get
    )
    municipios = base_mensal[["codigo_ibge", "nome_municipio"]].drop_duplicates().sort_values("nome_municipio")
    nome_por_codigo = dict(zip(municipios["codigo_ibge"], municipios["nome_municipio"]))
    codigos_municipios = st.sidebar.multiselect(
        "Municípios", options=list(nome_por_codigo), format_func=nome_por_codigo.get, placeholder="Todos"
    )
    fases_disponiveis = [f for f in ORDEM_FASES_ENSO if f in set(base_mensal["fase_enso"])]
    fases_enso = st.sidebar.multiselect("Fase do ENSO", fases_disponiveis, default=fases_disponiveis)
    rotulo_metrica = st.sidebar.radio("Medida de focos", list(METRICAS_FOCOS))
    st.sidebar.caption(
        "Para comparar o ano parcial com os anos fechados, limite os meses ao mesmo intervalo em todos eles."
    )
    return {
        "intervalo_anos": intervalo_anos,
        "intervalo_meses": (mes_inicial, mes_final),
        "codigos_municipios": codigos_municipios,
        "fases_enso": fases_enso or fases_disponiveis,
        "rotulo_metrica": rotulo_metrica,
        "coluna_metrica": METRICAS_FOCOS[rotulo_metrica],
    }


def exibir_indicadores(base_filtrada, agregado_mensal):
    area_total = base_filtrada.drop_duplicates("codigo_ibge")["area_km2"].sum()
    total_focos = int(agregado_mensal["quantidade_focos"].sum())
    colunas = st.columns(5)
    colunas[0].metric("Total de focos", f"{total_focos:,}".replace(",", "."))
    colunas[1].metric("Focos por 1000 km²", f"{total_focos / area_total * 1000:.1f}")
    if "temperatura_maxima_media_c" in agregado_mensal.columns:
        colunas[2].metric("Temp. máxima média", f"{agregado_mensal['temperatura_maxima_media_c'].mean():.1f} °C")
    if "precipitacao_total_mm" in agregado_mensal.columns:
        colunas[3].metric("Chuva média mensal", f"{agregado_mensal['precipitacao_total_mm'].mean():.0f} mm")
    colunas[4].metric("Meses no recorte", len(agregado_mensal))


def exibir_relacao_clima(agregado_mensal, filtros):
    variaveis = listar_variaveis_climaticas_disponiveis(agregado_mensal)
    if not variaveis:
        st.info("Nenhuma variável climática na base. Rode a coleta com BAIXAR_CLIMA = True.")
        return
    coluna_controles, coluna_grafico = st.columns([1, 3])
    coluna_clima = coluna_controles.selectbox("Variável climática", list(variaveis), format_func=variaveis.get)
    forma_valores = coluna_controles.radio("Valores", ["Originais", "Desvio da média do mês do ano"])
    coluna_metrica = filtros["coluna_metrica"]
    tabela = agregado_mensal
    rotulo_clima, rotulo_focos = variaveis[coluna_clima], filtros["rotulo_metrica"]
    if forma_valores != "Originais":
        tabela = calcular_desvio_da_media_do_mes(agregado_mensal, [coluna_clima, coluna_metrica])
        rotulo_clima, rotulo_focos = f"Desvio: {rotulo_clima}", f"Desvio: {rotulo_focos}"
    pares = tabela[[coluna_clima, coluna_metrica]].dropna()
    correlacao = pares.corr(method="spearman").iloc[0, 1] if len(pares) > 2 else float("nan")
    coluna_controles.metric("Correlação de Spearman", "—" if pd.isna(correlacao) else f"{correlacao:.2f}")
    coluna_controles.metric("Pares de valores", len(pares))
    coluna_grafico.plotly_chart(
        grafico_relacao_clima_focos(tabela, coluna_clima, rotulo_clima, coluna_metrica, rotulo_focos),
        width="stretch",
    )


def exibir_aba_mensal(base_filtrada, filtros):
    agregado_mensal = agregar_por_mes(base_filtrada)
    coluna_metrica, rotulo_metrica = filtros["coluna_metrica"], filtros["rotulo_metrica"]
    exibir_indicadores(base_filtrada, agregado_mensal)
    st.plotly_chart(grafico_serie_temporal(agregado_mensal, coluna_metrica, rotulo_metrica), width="stretch")
    esquerda, direita = st.columns(2)
    esquerda.plotly_chart(
        grafico_distribuicao_por_mes(agregado_mensal, coluna_metrica, rotulo_metrica), width="stretch"
    )
    direita.plotly_chart(
        grafico_distribuicao_por_fase(agregado_mensal, coluna_metrica, rotulo_metrica), width="stretch"
    )
    exibir_relacao_clima(agregado_mensal, filtros)
    malha = carregar_malha_municipios()
    if malha is None:
        st.info("Mapa indisponível: falta o arquivo malha_municipios_para.geojson em dados/brutos.")
    else:
        st.plotly_chart(
            grafico_mapa_municipios(agregar_por_municipio(base_filtrada), malha, coluna_metrica, rotulo_metrica),
            width="stretch",
        )
    with st.expander("Ver tabela mensal agregada"):
        st.dataframe(agregado_mensal, width="stretch", hide_index=True)


def exibir_aba_anual(base_anual, filtros):
    st.caption("Esta aba usa apenas os filtros de período e de municípios.")
    base_anual_filtrada = filtrar_base_anual(base_anual, filtros["intervalo_anos"], filtros["codigos_municipios"])
    if base_anual_filtrada.empty:
        st.warning("Nenhum dado para os filtros selecionados.")
        return
    agregado_ciclos = agregar_por_ciclo_prodes(base_anual_filtrada)
    st.plotly_chart(grafico_evolucao_por_ciclo(agregado_ciclos), width="stretch")
    usar_escala_logaritmica = st.toggle("Escala logarítmica nos dois eixos")
    st.plotly_chart(
        grafico_relacao_desmatamento_focos(base_anual_filtrada, usar_escala_logaritmica), width="stretch"
    )
    with st.expander("Ver tabela por ciclo PRODES"):
        st.dataframe(agregado_ciclos, width="stretch", hide_index=True)


def executar_dashboard():
    st.title("Focos de calor, clima e desmatamento no Pará")
    base_mensal = carregar_base_mensal()
    if base_mensal is None:
        st.error("base_mensal.csv não encontrado. Rode antes: python coleta/executar_coleta.py")
        st.caption(FONTES)
        return
    filtros = montar_filtros_laterais(base_mensal)
    base_filtrada = filtrar_base_mensal(
        base_mensal, filtros["intervalo_anos"], filtros["intervalo_meses"],
        filtros["codigos_municipios"], filtros["fases_enso"],
    )
    aba_mensal, aba_anual = st.tabs(["Mensal", "Anual (ciclo PRODES)"])
    with aba_mensal:
        if base_filtrada.empty:
            st.warning("Nenhum dado para os filtros selecionados.")
        else:
            exibir_aba_mensal(base_filtrada, filtros)
    with aba_anual:
        base_anual = carregar_base_anual()
        if base_anual is None:
            st.warning("base_anual_prodes.csv não encontrado. Falta o shapefile do PRODES.")
        else:
            exibir_aba_anual(base_anual, filtros)
    st.caption(FONTES)


executar_dashboard()
