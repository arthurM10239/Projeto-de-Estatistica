import io

import pandas as pd

from configuracao import (
    ARQUIVO_ONI,
    LIMIAR_ANOMALIA_ENSO,
    MINIMO_TRIMESTRES_CONSECUTIVOS_ENSO,
    URL_ONI_NOAA,
)
from utilidades import requisitar_com_tentativas

MES_CENTRAL_POR_TRIMESTRE = {
    "DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
    "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12,
}


def baixar_texto_oni():
    if not ARQUIVO_ONI.exists():
        ARQUIVO_ONI.parent.mkdir(parents=True, exist_ok=True)
        ARQUIVO_ONI.write_text(requisitar_com_tentativas(URL_ONI_NOAA).text, encoding="utf-8")
    return ARQUIVO_ONI.read_text(encoding="utf-8")


def classificar_fases_enso(anomalias):
    fases = pd.Series("Neutro", index=anomalias.index)
    for rotulo_fase, condicao in (
        ("El Niño", anomalias >= LIMIAR_ANOMALIA_ENSO),
        ("La Niña", anomalias <= -LIMIAR_ANOMALIA_ENSO),
    ):
        identificador_sequencia = (condicao != condicao.shift()).cumsum()
        tamanho_sequencia = condicao.groupby(identificador_sequencia).transform("size")
        sequencia_em_andamento = identificador_sequencia == identificador_sequencia.iloc[-1]
        evento_valido = tamanho_sequencia >= MINIMO_TRIMESTRES_CONSECUTIVOS_ENSO
        fases[condicao & (evento_valido | sequencia_em_andamento)] = rotulo_fase
    return fases


def montar_enso_mensal():
    tabela_oni = pd.read_csv(io.StringIO(baixar_texto_oni()), sep=r"\s+")
    tabela_oni.columns = ["trimestre", "ano", "temperatura_media", "anomalia_oni"]
    tabela_oni["mes"] = tabela_oni["trimestre"].map(MES_CENTRAL_POR_TRIMESTRE)
    tabela_oni = tabela_oni.dropna(subset=["mes"]).sort_values(["ano", "mes"]).reset_index(drop=True)
    tabela_oni["fase_enso"] = classificar_fases_enso(tabela_oni["anomalia_oni"])
    return tabela_oni[["ano", "mes", "anomalia_oni", "fase_enso"]].astype({"ano": int, "mes": int})
