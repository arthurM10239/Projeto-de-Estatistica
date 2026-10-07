import calendar
import time

import numpy as np
import pandas as pd

from configuracao import (
    ANO_INICIAL_COLETA,
    ANO_PARCIAL,
    PARAMETROS_CLIMATICOS,
    PASTA_CLIMA,
    ULTIMO_MES_PARCIAL,
    URL_NASA_POWER_DIARIO,
)
from utilidades import requisitar_com_tentativas

VALOR_AUSENTE_NASA_POWER = -999

AGREGACAO_MENSAL_CLIMA = {
    "T2M": ("temperatura_media_c", "media"),
    "T2M_MAX": ("temperatura_maxima_media_c", "media"),
    "PRECTOTCORR": ("precipitacao_total_mm", "soma"),
    "RH2M": ("umidade_relativa_media_pct", "media"),
}


def baixar_clima_diario_municipio(codigo_ibge, latitude, longitude):
    destino = PASTA_CLIMA / f"{codigo_ibge}.csv"
    if destino.exists():
        return pd.read_csv(destino, index_col="data", parse_dates=["data"])
    ultimo_dia = calendar.monthrange(ANO_PARCIAL, ULTIMO_MES_PARCIAL)[1]
    parametros = {
        "parameters": ",".join(PARAMETROS_CLIMATICOS),
        "community": "AG",
        "latitude": round(latitude, 4),
        "longitude": round(longitude, 4),
        "start": f"{ANO_INICIAL_COLETA}0101",
        "end": f"{ANO_PARCIAL}{ULTIMO_MES_PARCIAL:02d}{ultimo_dia}",
        "format": "JSON",
    }
    conteudo = requisitar_com_tentativas(URL_NASA_POWER_DIARIO, parametros).json()
    clima_diario = pd.DataFrame(conteudo["properties"]["parameter"]).replace(VALOR_AUSENTE_NASA_POWER, np.nan)
    clima_diario.index = pd.to_datetime(clima_diario.index, format="%Y%m%d")
    clima_diario.index.name = "data"
    destino.parent.mkdir(parents=True, exist_ok=True)
    clima_diario.to_csv(destino)
    time.sleep(1)
    return clima_diario


def agregar_clima_mensal(clima_diario):
    agrupado = clima_diario.resample("MS")
    colunas_mensais = {}
    for parametro, (nome_coluna, operacao) in AGREGACAO_MENSAL_CLIMA.items():
        if operacao == "soma":
            colunas_mensais[nome_coluna] = agrupado[parametro].sum(min_count=1)
        else:
            colunas_mensais[nome_coluna] = agrupado[parametro].mean()
    clima_mensal = pd.DataFrame(colunas_mensais)
    clima_mensal["dias_com_dado"] = agrupado["T2M"].count()
    return clima_mensal


def montar_clima_mensal_para(tabela_municipios):
    tabelas_municipais = []
    total = len(tabela_municipios)
    for posicao, municipio in enumerate(tabela_municipios.itertuples(index=False), start=1):
        print(f"  NASA POWER {posicao}/{total}: {municipio.nome_municipio}")
        clima_mensal = agregar_clima_mensal(
            baixar_clima_diario_municipio(municipio.codigo_ibge, municipio.latitude, municipio.longitude)
        )
        clima_mensal = clima_mensal.assign(
            codigo_ibge=municipio.codigo_ibge, ano=clima_mensal.index.year, mes=clima_mensal.index.month
        )
        tabelas_municipais.append(clima_mensal.reset_index(drop=True))
    return pd.concat(tabelas_municipais, ignore_index=True)
