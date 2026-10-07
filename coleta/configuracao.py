from pathlib import Path

PASTA_RAIZ = Path(__file__).resolve().parent.parent
PASTA_DADOS_BRUTOS = PASTA_RAIZ / "dados" / "brutos"
PASTA_DADOS_TRATADOS = PASTA_RAIZ / "dados" / "tratados"
PASTA_FOCOS = PASTA_DADOS_BRUTOS / "focos"
PASTA_CLIMA = PASTA_DADOS_BRUTOS / "clima_diario"
PASTA_PRODES_SHAPEFILE = PASTA_DADOS_BRUTOS / "prodes_shapefile"

ARQUIVO_MUNICIPIOS = PASTA_DADOS_BRUTOS / "municipios_para.csv"
ARQUIVO_MALHA_MUNICIPIOS = PASTA_DADOS_BRUTOS / "malha_municipios_para.geojson"
ARQUIVO_ONI = PASTA_DADOS_BRUTOS / "oni.ascii.txt"
ARQUIVO_DESMATAMENTO_MUNICIPIOS = PASTA_DADOS_BRUTOS / "prodes_municipios_para.csv"
ARQUIVO_BASE_MENSAL = PASTA_DADOS_TRATADOS / "base_mensal.csv"
ARQUIVO_BASE_ANUAL = PASTA_DADOS_TRATADOS / "base_anual_prodes.csv"

CODIGO_UF_PARA = 15
NOME_ESTADO_PARA = "PARA"
SATELITE_REFERENCIA = "AQUA_M-T"

ANO_INICIAL_COLETA = 2014
ANO_INICIAL_ANALISE = 2015
ANO_FINAL_COMPLETO = 2025
ANO_PARCIAL = 2026
ULTIMO_MES_PARCIAL = 9
MES_INICIO_ANO_PRODES = 8

LIMIAR_ANOMALIA_ENSO = 0.5
MINIMO_TRIMESTRES_CONSECUTIVOS_ENSO = 5

PARAMETROS_CLIMATICOS = ["T2M", "T2M_MAX", "PRECTOTCORR", "RH2M"]
PROJECAO_AREA_EQUIVALENTE = "ESRI:102033"

URL_MUNICIPIOS_IBGE = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios"
URL_METADADOS_MALHA_IBGE = "https://servicodados.ibge.gov.br/api/v3/malhas/municipios/{codigo}/metadados"
URL_MALHA_ESTADO_IBGE = "https://servicodados.ibge.gov.br/api/v3/malhas/estados/{uf}"
URL_NASA_POWER_DIARIO = "https://power.larc.nasa.gov/api/temporal/daily/point"
URL_ONI_NOAA = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
