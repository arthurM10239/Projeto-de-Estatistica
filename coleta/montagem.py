import pandas as pd

from configuracao import (
    ANO_FINAL_COMPLETO,
    ANO_INICIAL_ANALISE,
    ANO_INICIAL_COLETA,
    ANO_PARCIAL,
    MES_INICIO_ANO_PRODES,
    ULTIMO_MES_PARCIAL,
)

# Cria uma matriz completa cruzando todos os municípios com todos os meses do período, garantindo que não existam buracos na linha do tempo (meses sem dados)
def criar_grade_municipio_mes(tabela_municipios):
    # Gera uma lista contínua de datas, mês a mês, desde o ano inicial até o último mês parcial do ano atual
    meses = pd.date_range(
        f"{ANO_INICIAL_COLETA}-01-01", f"{ANO_PARCIAL}-{ULTIMO_MES_PARCIAL:02d}-01", freq="MS"
    )
    
    # Transforma essa lista de datas em uma tabela contendo apenas as colunas de ano e mês
    calendario = pd.DataFrame({"ano": meses.year, "mes": meses.month})
    
    # Faz um cruzamento cartesiano (cross join): para cada município da base, anexa o calendário inteiro
    return tabela_municipios[["codigo_ibge", "nome_municipio", "area_km2"]].merge(calendario, how="cross")


# Unifica todas as fontes de dados independentes (focos, clima, ENSO) dentro da grade completa de municípios
def montar_base_mensal_completa(tabela_municipios, focos_mensais, clima_mensal, enso_mensal):
    # Inicia pela matriz base contendo todas as cidades e todos os meses possíveis
    base = criar_grade_municipio_mes(tabela_municipios)
    
    # Agrega os dados de focos de calor cruzando pelo código da cidade, ano e mês (mantendo a base intacta caso não haja focos no mês)
    base = base.merge(focos_mensais, on=["codigo_ibge", "ano", "mes"], how="left")
    
    # Preenche com zero os meses em que o município não registrou nenhum foco de calor e converte para número inteiro
    base["quantidade_focos"] = base["quantidade_focos"].fillna(0).astype(int)
    
    # Calcula a métrica de densidade proporcional (quantos focos ocorreram a cada 1000 km² de área do município)
    base["focos_por_1000_km2"] = base["quantidade_focos"] / base["area_km2"] * 1000
    
    # Se os dados de clima da NASA tiverem sido baixados, junta eles na tabela principal
    if clima_mensal is not None:
        base = base.merge(clima_mensal, on=["codigo_ibge", "ano", "mes"], how="left")
        
    # Junta os dados do fenômeno climático (El Niño/La Niña), que independem de cidade, apenas por ano e mês
    base = base.merge(enso_mensal, on=["ano", "mes"], how="left")
    
    # Cria uma nova coluna indicando a qual ciclo do PRODES esse mês pertence (se o mês for >= agosto, ele já pertence ao ano PRODES seguinte)
    base["ano_prodes"] = base["ano"] + (base["mes"] >= MES_INICIO_ANO_PRODES).astype(int)
    
    # Cria um marcador (booleano) para identificar se o dado pertence a um ano fechado ou ao ano parcial corrente
    base["ano_completo"] = base["ano"] <= ANO_FINAL_COMPLETO
    
    return base


# Filtra a tabela final removendo o histórico antigo e deixando apenas os dados a partir do ano estipulado para a análise
def recortar_base_mensal_analise(base_mensal_completa):
    # Mantém apenas as linhas onde o ano é maior ou igual ao início da análise definida nas configurações
    recorte = base_mensal_completa[base_mensal_completa["ano"] >= ANO_INICIAL_ANALISE]
    
    # Ordena a tabela por município e cronologia, e reseta o índice de linhas para ficar sequencial e limpo
    return recorte.sort_values(["codigo_ibge", "ano", "mes"]).reset_index(drop=True)


# Condensa os 12 meses do calendário PRODES (agosto a julho) em uma única linha anual e cruza com os dados de desmatamento
def montar_base_anual_prodes(base_mensal_completa, desmatamento_anual):
    # Pega apenas os dados que caem dentro do intervalo de ciclos PRODES completos (ignorando ciclos parciais)
    ciclos_completos = base_mensal_completa[
        base_mensal_completa["ano_prodes"].between(ANO_INICIAL_ANALISE, ANO_FINAL_COMPLETO)
    ]
    
    # Define as regras de agregação base: soma de focos, média da anomalia climática e contagem de meses no ciclo
    agregacoes = {
        "quantidade_focos": ("quantidade_focos", "sum"),
        "anomalia_oni_media": ("anomalia_oni", "mean"),
        "meses_no_ciclo": ("mes", "size"),
    }
    
    # Adiciona dinamicamente as regras para variáveis de temperatura e umidade, fazendo a média anual caso existam
    for coluna in ["temperatura_media_c", "temperatura_maxima_media_c", "umidade_relativa_media_pct"]:
        if coluna in ciclos_completos.columns:
            agregacoes[coluna] = (coluna, "mean")
            
    # Adiciona dinamicamente a regra para chuvas, somando a precipitação anual caso a coluna exista
    if "precipitacao_total_mm" in ciclos_completos.columns:
        agregacoes["precipitacao_total_mm"] = ("precipitacao_total_mm", "sum")
        
    # Executa o agrupamento de fato, unindo as linhas por município e ciclo PRODES, aplicando as regras matemáticas definidas acima
    base_anual = (
        ciclos_completos.groupby(["codigo_ibge", "nome_municipio", "area_km2", "ano_prodes"])
        .agg(**agregacoes)
        .reset_index()
    )
    
    # Garante a integridade dos dados descartando qualquer ciclo que não tenha exatamente 12 meses computados
    base_anual = base_anual[base_anual["meses_no_ciclo"] == 12]
    
    # Recalcula a densidade de focos agora com o novo total somado do ciclo anual
    base_anual["focos_por_1000_km2"] = base_anual["quantidade_focos"] / base_anual["area_km2"] * 1000
    
    # Cruza a tabela consolidada com a base oficial de desmatamento (calculada por cruzamento geoespacial)
    base_anual = base_anual.merge(desmatamento_anual, on=["codigo_ibge", "ano_prodes"], how="left")
    
    # Calcula qual porcentagem da área total da cidade foi desmatada naquele ano específico
    base_anual["desmatamento_pct_area"] = base_anual["desmatamento_km2"] / base_anual["area_km2"] * 100
    
    return base_anual.reset_index(drop=True)