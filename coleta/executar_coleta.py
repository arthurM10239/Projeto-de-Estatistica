import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from clima import montar_clima_mensal_para
from configuracao import (
    ARQUIVO_BASE_ANUAL,
    ARQUIVO_BASE_MENSAL,
    PASTA_DADOS_TRATADOS,
    PASTA_FOCOS,
    PASTA_PRODES_SHAPEFILE,
)
from desmatamento import carregar_desmatamento_anual_para
from enso import montar_enso_mensal
from focos import contar_focos_mensais_por_municipio
from montagem import montar_base_anual_prodes, montar_base_mensal_completa, recortar_base_mensal_analise
from municipios import baixar_malha_municipios_para, carregar_municipios_para

CORRECOES_NOMES_MUNICIPIOS = {}

BAIXAR_CLIMA = True


def executar():
    for pasta in (PASTA_DADOS_TRATADOS, PASTA_FOCOS, PASTA_PRODES_SHAPEFILE):
        pasta.mkdir(parents=True, exist_ok=True)

    print("[1/5] Municipios e malha do IBGE")
    tabela_municipios = carregar_municipios_para()
    baixar_malha_municipios_para()
    print(f"  {len(tabela_municipios)} municipios carregados")

    print("[2/5] Focos de calor")
    focos_mensais = contar_focos_mensais_por_municipio(tabela_municipios, CORRECOES_NOMES_MUNICIPIOS)
    if focos_mensais is None:
        print(f"  Nenhum arquivo de focos em {PASTA_FOCOS}. Coloque os CSV ou ZIP do BDQueimadas e rode de novo.")
        return

    print("[3/5] Indice ONI da NOAA")
    enso_mensal = montar_enso_mensal()
    print(f"  {len(enso_mensal)} trimestres classificados")

    print("[4/5] Clima da NASA POWER")
    clima_mensal = montar_clima_mensal_para(tabela_municipios) if BAIXAR_CLIMA else None
    if clima_mensal is None:
        print("  Pulado (BAIXAR_CLIMA = False)")

    print("[5/5] Montagem das bases")
    base_mensal_completa = montar_base_mensal_completa(
        tabela_municipios, focos_mensais, clima_mensal, enso_mensal
    )
    base_mensal = recortar_base_mensal_analise(base_mensal_completa)
    base_mensal.to_csv(ARQUIVO_BASE_MENSAL, index=False)
    print(f"  base_mensal.csv: {len(base_mensal)} linhas, anos {base_mensal['ano'].min()} a {base_mensal['ano'].max()}")

    desmatamento_anual = carregar_desmatamento_anual_para()
    if desmatamento_anual is None:
        print("  Shapefile do PRODES nao encontrado. Base anual nao gerada.")
        return
    base_anual = montar_base_anual_prodes(base_mensal_completa, desmatamento_anual)
    base_anual.to_csv(ARQUIVO_BASE_ANUAL, index=False)
    print(f"  base_anual_prodes.csv: {len(base_anual)} linhas")


if __name__ == "__main__":
    executar()
