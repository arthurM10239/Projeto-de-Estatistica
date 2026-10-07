import time

import pandas as pd

from configuracao import (
    ARQUIVO_MALHA_MUNICIPIOS,
    ARQUIVO_MUNICIPIOS,
    CODIGO_UF_PARA,
    URL_MALHA_ESTADO_IBGE,
    URL_METADADOS_MALHA_IBGE,
    URL_MUNICIPIOS_IBGE,
)
from utilidades import normalizar_nome, requisitar_com_tentativas


def buscar_metadados_malha(codigo_ibge):
    conteudo = requisitar_com_tentativas(URL_METADADOS_MALHA_IBGE.format(codigo=codigo_ibge)).json()
    registro = conteudo[0] if isinstance(conteudo, list) else conteudo
    return {
        "latitude": float(registro["centroide"]["latitude"]),
        "longitude": float(registro["centroide"]["longitude"]),
        "area_km2": float(registro["area"]["dimensao"]),
    }


def carregar_municipios_para():
    if ARQUIVO_MUNICIPIOS.exists():
        return pd.read_csv(ARQUIVO_MUNICIPIOS)
    lista_municipios = requisitar_com_tentativas(URL_MUNICIPIOS_IBGE.format(uf=CODIGO_UF_PARA)).json()
    registros = []
    for posicao, municipio in enumerate(lista_municipios, start=1):
        print(f"  IBGE {posicao}/{len(lista_municipios)}: {municipio['nome']}")
        registros.append({
            "codigo_ibge": int(municipio["id"]),
            "nome_municipio": municipio["nome"],
            "nome_normalizado": normalizar_nome(municipio["nome"]),
            **buscar_metadados_malha(municipio["id"]),
        })
        time.sleep(0.2)
    tabela_municipios = pd.DataFrame(registros)
    ARQUIVO_MUNICIPIOS.parent.mkdir(parents=True, exist_ok=True)
    tabela_municipios.to_csv(ARQUIVO_MUNICIPIOS, index=False)
    return tabela_municipios


def baixar_malha_municipios_para():
    if ARQUIVO_MALHA_MUNICIPIOS.exists():
        return
    parametros = {
        "formato": "application/vnd.geo+json",
        "intrarregiao": "municipio",
        "qualidade": "intermediaria",
    }
    resposta = requisitar_com_tentativas(URL_MALHA_ESTADO_IBGE.format(uf=CODIGO_UF_PARA), parametros)
    ARQUIVO_MALHA_MUNICIPIOS.parent.mkdir(parents=True, exist_ok=True)
    ARQUIVO_MALHA_MUNICIPIOS.write_text(resposta.text, encoding="utf-8")
