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

# Dicionário reservado para aplicar correções manuais em nomes de municípios que possam vir escritos de forma inconsistente das fontes oficiais
CORRECOES_NOMES_MUNICIPIOS = {}

# Chave de controle para ativar ou desativar o download dos dados climáticos da NASA, pois é a etapa mais demorada do processo
BAIXAR_CLIMA = True


# Função orquestradora principal que executa o fluxo de coleta e cruzamento de dados passo a passo
def executar():
    # Garante que todas as pastas de diretório necessárias existam no sistema antes de iniciar, criando-as caso não existam
    for pasta in (PASTA_DADOS_TRATADOS, PASTA_FOCOS, PASTA_PRODES_SHAPEFILE):
        pasta.mkdir(parents=True, exist_ok=True)

    # Primeira etapa: Carrega a lista base de municípios do Pará e baixa o arquivo geográfico com os desenhos das fronteiras municipais
    print("[1/5] Municipios e malha do IBGE")
    tabela_municipios = carregar_municipios_para()
    baixar_malha_municipios_para()
    print(f"  {len(tabela_municipios)} municipios carregados")

    # Segunda etapa: Lê os arquivos brutos na pasta local, contabiliza os focos de calor por município e valida se os dados foram fornecidos pelo usuário
    print("[2/5] Focos de calor")
    focos_mensais = contar_focos_mensais_por_municipio(tabela_municipios, CORRECOES_NOMES_MUNICIPIOS)
    if focos_mensais is None:
        print(f"  Nenhum arquivo de focos em {PASTA_FOCOS}. Coloque os CSV ou ZIP do BDQueimadas e rode de novo.")
        return

    # Terceira etapa: Conecta com a base da NOAA para baixar os índices oceânicos e classificar o período histórico nas fases climáticas como El Niño e La Niña
    print("[3/5] Indice ONI da NOAA")
    enso_mensal = montar_enso_mensal()
    print(f"  {len(enso_mensal)} trimestres classificados")

    # Quarta etapa: Se a chave de permissão estiver ativada, faz a requisição na API da NASA baixando o histórico de chuvas e temperaturas para cada município da lista
    print("[4/5] Clima da NASA POWER")
    clima_mensal = montar_clima_mensal_para(tabela_municipios) if BAIXAR_CLIMA else None
    if clima_mensal is None:
        print("  Pulado (BAIXAR_CLIMA = False)")

    # Quinta etapa: Inicia o processo de união de todas as fontes de dados independentes coletadas nos passos anteriores em tabelas únicas
    print("[5/5] Montagem das bases")
    
    # Consolida municípios, focos, clima e fases oceânicas em uma única tabela de granularidade mensal e aplica o recorte temporal da análise
    base_mensal_completa = montar_base_mensal_completa(
        tabela_municipios, focos_mensais, clima_mensal, enso_mensal
    )
    base_mensal = recortar_base_mensal_analise(base_mensal_completa)
    
    # Exporta a tabela mensal consolidada e tratada para um arquivo CSV final, que será consumido diretamente pelo painel interativo
    base_mensal.to_csv(ARQUIVO_BASE_MENSAL, index=False)
    print(f"  base_mensal.csv: {len(base_mensal)} linhas, anos {base_mensal['ano'].min()} a {base_mensal['ano'].max()}")

    # Tenta ler ou calcular os dados pesados de desmatamento a partir dos arquivos do PRODES
    desmatamento_anual = carregar_desmatamento_anual_para()
    
    # Se o arquivo de desmatamento não existir, emite um aviso e encerra a criação da base anual por aqui
    if desmatamento_anual is None:
        print("  Shapefile do PRODES nao encontrado. Base anual nao gerada.")
        return
        
    # Cruza os dados da tabela mensal consolidada com os cálculos de desmatamento, agrupando as informações pelo calendário do ciclo PRODES e salvando o arquivo CSV final
    base_anual = montar_base_anual_prodes(base_mensal_completa, desmatamento_anual)
    base_anual.to_csv(ARQUIVO_BASE_ANUAL, index=False)
    print(f"  base_anual_prodes.csv: {len(base_anual)} linhas")


# Bloco de execução condicional padrão do Python que garante que a função principal só rode se este arquivo for executado diretamente no terminal
if __name__ == "__main__":
    executar()