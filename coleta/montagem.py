import pandas as pd

from configuracao import (
    ANO_FINAL_COMPLETO,
    ANO_INICIAL_ANALISE,
    ANO_INICIAL_COLETA,
    ANO_PARCIAL,
    MES_INICIO_ANO_PRODES,
    ULTIMO_MES_PARCIAL,
)


def criar_grade_municipio_mes(tabela_municipios):
    meses = pd.date_range(
        f"{ANO_INICIAL_COLETA}-01-01", f"{ANO_PARCIAL}-{ULTIMO_MES_PARCIAL:02d}-01", freq="MS"
    )
    calendario = pd.DataFrame({"ano": meses.year, "mes": meses.month})
    return tabela_municipios[["codigo_ibge", "nome_municipio", "area_km2"]].merge(calendario, how="cross")


def montar_base_mensal_completa(tabela_municipios, focos_mensais, clima_mensal, enso_mensal):
    base = criar_grade_municipio_mes(tabela_municipios)
    base = base.merge(focos_mensais, on=["codigo_ibge", "ano", "mes"], how="left")
    base["quantidade_focos"] = base["quantidade_focos"].fillna(0).astype(int)
    base["focos_por_1000_km2"] = base["quantidade_focos"] / base["area_km2"] * 1000
    if clima_mensal is not None:
        base = base.merge(clima_mensal, on=["codigo_ibge", "ano", "mes"], how="left")
    base = base.merge(enso_mensal, on=["ano", "mes"], how="left")
    base["ano_prodes"] = base["ano"] + (base["mes"] >= MES_INICIO_ANO_PRODES).astype(int)
    base["ano_completo"] = base["ano"] <= ANO_FINAL_COMPLETO
    return base


def recortar_base_mensal_analise(base_mensal_completa):
    recorte = base_mensal_completa[base_mensal_completa["ano"] >= ANO_INICIAL_ANALISE]
    return recorte.sort_values(["codigo_ibge", "ano", "mes"]).reset_index(drop=True)


def montar_base_anual_prodes(base_mensal_completa, desmatamento_anual):
    ciclos_completos = base_mensal_completa[
        base_mensal_completa["ano_prodes"].between(ANO_INICIAL_ANALISE, ANO_FINAL_COMPLETO)
    ]
    agregacoes = {
        "quantidade_focos": ("quantidade_focos", "sum"),
        "anomalia_oni_media": ("anomalia_oni", "mean"),
        "meses_no_ciclo": ("mes", "size"),
    }
    for coluna in ["temperatura_media_c", "temperatura_maxima_media_c", "umidade_relativa_media_pct"]:
        if coluna in ciclos_completos.columns:
            agregacoes[coluna] = (coluna, "mean")
    if "precipitacao_total_mm" in ciclos_completos.columns:
        agregacoes["precipitacao_total_mm"] = ("precipitacao_total_mm", "sum")
    base_anual = (
        ciclos_completos.groupby(["codigo_ibge", "nome_municipio", "area_km2", "ano_prodes"])
        .agg(**agregacoes)
        .reset_index()
    )
    base_anual = base_anual[base_anual["meses_no_ciclo"] == 12]
    base_anual["focos_por_1000_km2"] = base_anual["quantidade_focos"] / base_anual["area_km2"] * 1000
    base_anual = base_anual.merge(desmatamento_anual, on=["codigo_ibge", "ano_prodes"], how="left")
    base_anual["desmatamento_pct_area"] = base_anual["desmatamento_km2"] / base_anual["area_km2"] * 100
    return base_anual.reset_index(drop=True)
