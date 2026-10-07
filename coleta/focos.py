import zipfile

import pandas as pd

from configuracao import NOME_ESTADO_PARA, PASTA_FOCOS, SATELITE_REFERENCIA
from utilidades import normalizar_nome

APELIDOS_COLUNAS_FOCOS = {
    "datahora": "data_hora",
    "data_hora_gmt": "data_hora",
    "data_pas": "data_hora",
    "satelite": "satelite",
    "municipio": "municipio",
    "estado": "estado",
}

TAMANHO_BLOCO_LEITURA = 400_000
EXTENSOES_ACEITAS = (".csv", ".zip")


def listar_arquivos_focos():
    if not PASTA_FOCOS.exists():
        return []
    return sorted(
        caminho for caminho in PASTA_FOCOS.iterdir()
        if caminho.suffix.lower() in EXTENSOES_ACEITAS and not caminho.name.startswith(".")
    )


def abrir_arquivo_focos(caminho_arquivo):
    if caminho_arquivo.suffix.lower() != ".zip":
        return caminho_arquivo.open("rb")
    arquivo_zip = zipfile.ZipFile(caminho_arquivo)
    nomes_csv = [nome for nome in arquivo_zip.namelist() if nome.lower().endswith(".csv")]
    if not nomes_csv:
        raise ValueError(f"O arquivo {caminho_arquivo.name} nao contem CSV.")
    return arquivo_zip.open(nomes_csv[0])


def eh_coluna_de_interesse(nome_coluna):
    return nome_coluna.strip().lower() in APELIDOS_COLUNAS_FOCOS


def extrair_focos_referencia_para(caminho_arquivo):
    blocos_filtrados = []
    with abrir_arquivo_focos(caminho_arquivo) as fluxo:
        leitor = pd.read_csv(
            fluxo,
            usecols=eh_coluna_de_interesse,
            dtype=str,
            encoding="utf-8",
            encoding_errors="replace",
            chunksize=TAMANHO_BLOCO_LEITURA,
        )
        for bloco in leitor:
            bloco.columns = [APELIDOS_COLUNAS_FOCOS[coluna.strip().lower()] for coluna in bloco.columns]
            bloco = bloco[bloco["satelite"].str.strip() == SATELITE_REFERENCIA]
            estados_normalizados = {valor: normalizar_nome(valor) for valor in bloco["estado"].dropna().unique()}
            bloco = bloco[bloco["estado"].map(estados_normalizados) == NOME_ESTADO_PARA]
            if not bloco.empty:
                blocos_filtrados.append(bloco[["data_hora", "municipio"]])
    if not blocos_filtrados:
        return pd.DataFrame(columns=["data_hora", "municipio"])
    return pd.concat(blocos_filtrados, ignore_index=True)


def contar_focos_mensais_por_municipio(tabela_municipios, correcoes_nomes=None):
    arquivos_focos = listar_arquivos_focos()
    if not arquivos_focos:
        return None
    partes = []
    for caminho_arquivo in arquivos_focos:
        focos_do_arquivo = extrair_focos_referencia_para(caminho_arquivo)
        print(f"  {caminho_arquivo.name}: {len(focos_do_arquivo)} focos do Para no satelite de referencia")
        partes.append(focos_do_arquivo)
    focos_para = pd.concat(partes, ignore_index=True)
    datas = pd.to_datetime(focos_para["data_hora"], errors="coerce", format="mixed")
    focos_para = focos_para.assign(ano=datas.dt.year, mes=datas.dt.month).dropna(subset=["ano", "mes"])
    focos_para["nome_normalizado"] = focos_para["municipio"].map(normalizar_nome).replace(correcoes_nomes or {})
    focos_com_codigo = focos_para.merge(
        tabela_municipios[["nome_normalizado", "codigo_ibge"]], on="nome_normalizado", how="left"
    )
    sem_correspondencia = focos_com_codigo[focos_com_codigo["codigo_ibge"].isna()]
    if not sem_correspondencia.empty:
        print("  ATENCAO: municipios sem correspondencia no IBGE (focos descartados):")
        print("  ", sem_correspondencia["municipio"].value_counts().to_dict())
    contagem = (
        focos_com_codigo.dropna(subset=["codigo_ibge"])
        .groupby(["codigo_ibge", "ano", "mes"])
        .size()
        .rename("quantidade_focos")
        .reset_index()
    )
    return contagem.astype({"codigo_ibge": int, "ano": int, "mes": int})
