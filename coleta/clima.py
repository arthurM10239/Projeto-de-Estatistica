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

# Constante que a API da NASA POWER usa para indicar que um dado está faltando ou é inválido
VALOR_AUSENTE_NASA_POWER = -999

# Dicionário mapeando a sigla da variável na API da NASA para o nome final da coluna e o tipo de cálculo mensal
AGREGACAO_MENSAL_CLIMA = {
    "T2M": ("temperatura_media_c", "media"),
    "T2M_MAX": ("temperatura_maxima_media_c", "media"),
    "PRECTOTCORR": ("precipitacao_total_mm", "soma"),
    "RH2M": ("umidade_relativa_media_pct", "media"),
}

# Baixa os dados climáticos diários de um município específico através da API da NASA POWER
def baixar_clima_diario_municipio(codigo_ibge, latitude, longitude):
    # Define o caminho onde o arquivo CSV deste município deve ser salvo localmente
    destino = PASTA_CLIMA / f"{codigo_ibge}.csv"
    
    # Verifica se o arquivo já existe para evitar fazer um download redundante (funciona como cache local)
    if destino.exists():
        return pd.read_csv(destino, index_col="data", parse_dates=["data"])
        
    # Descobre qual é o último dia do mês para limitar o período parcial final estipulado
    ultimo_dia = calendar.monthrange(ANO_PARCIAL, ULTIMO_MES_PARCIAL)[1]
    
    # Monta o dicionário de parâmetros exigidos para realizar a requisição na API da NASA
    parametros = {
        "parameters": ",".join(PARAMETROS_CLIMATICOS),
        "community": "AG", # Comunidade de Agroclimatologia
        "latitude": round(latitude, 4),
        "longitude": round(longitude, 4),
        "start": f"{ANO_INICIAL_COLETA}0101",
        "end": f"{ANO_PARCIAL}{ULTIMO_MES_PARCIAL:02d}{ultimo_dia}",
        "format": "JSON",
    }
    
    # Faz a requisição na API utilizando uma função customizada que tenta novamente em caso de falha de conexão
    conteudo = requisitar_com_tentativas(URL_NASA_POWER_DIARIO, parametros).json()
    
    # Transforma a resposta JSON em uma tabela Pandas (DataFrame) e substitui o código de erro -999 por nulo (NaN)
    clima_diario = pd.DataFrame(conteudo["properties"]["parameter"]).replace(VALOR_AUSENTE_NASA_POWER, np.nan)
    
    # Converte o índice da tabela de texto ("AAAAMMDD") para o formato oficial de data (DateTime)
    clima_diario.index = pd.to_datetime(clima_diario.index, format="%Y%m%d")
    clima_diario.index.name = "data"
    
    # Cria a pasta de destino no sistema caso ela ainda não exista
    destino.parent.mkdir(parents=True, exist_ok=True)
    
    # Salva os dados baixados em formato CSV para consultas futuras
    clima_diario.to_csv(destino)
    
    # Aguarda 1 segundo antes de liberar a função para evitar bloqueio por limite de taxa da API (Rate Limit)
    time.sleep(1)
    
    return clima_diario

# Transforma os dados climáticos baseados em dias para uma visão agregada por meses
def agregar_clima_mensal(clima_diario):
    # Agrupa os dados diários utilizando a frequência mensal (MS = Month Start)
    agrupado = clima_diario.resample("MS")
    colunas_mensais = {}
    
    # Percorre as regras matemáticas definidas no topo do código para aplicar no agrupamento
    for parametro, (nome_coluna, operacao) in AGREGACAO_MENSAL_CLIMA.items():
        if operacao == "soma":
            # Soma os valores do mês (ex: chuvas), exigindo pelo menos 1 dado válido para não gerar falsos zeros
            colunas_mensais[nome_coluna] = agrupado[parametro].sum(min_count=1)
        else:
            # Calcula a média do mês (ex: umidade, temperatura)
            colunas_mensais[nome_coluna] = agrupado[parametro].mean()
            
    # Cria uma nova tabela apenas com as colunas agregadas mensalmente
    clima_mensal = pd.DataFrame(colunas_mensais)
    
    # Adiciona uma coluna de controle (auditoria) para saber quantos dias no mês continham registros de temperatura
    clima_mensal["dias_com_dado"] = agrupado["T2M"].count()
    
    return clima_mensal

# Orquestra todo o processo de baixar e agregar os dados para todos os municípios listados
def montar_clima_mensal_para(tabela_municipios):
    tabelas_municipais = []
    total = len(tabela_municipios)
    
    # Itera linha a linha a tabela de municípios (usando itertuples para ter melhor performance no Pandas)
    for posicao, municipio in enumerate(tabela_municipios.itertuples(index=False), start=1):
        
        # Mostra o progresso no terminal (console) para o usuário acompanhar a execução
        print(f"  NASA POWER {posicao}/{total}: {municipio.nome_municipio}")
        
        # 1º Baixa o dado diário do município atual e 2º Repassa direto para a função que agrega por mês
        clima_mensal = agregar_clima_mensal(
            baixar_clima_diario_municipio(municipio.codigo_ibge, municipio.latitude, municipio.longitude)
        )
        
        # Adiciona o código do município e quebra o índice de datas gerando novas colunas separadas de ano e mês
        clima_mensal = clima_mensal.assign(
            codigo_ibge=municipio.codigo_ibge, ano=clima_mensal.index.year, mes=clima_mensal.index.month
        )
        
        # Remove o índice transformando em uma tabela comum e adiciona o resultado na lista mestre
        tabelas_municipais.append(clima_mensal.reset_index(drop=True))
        
    # Junta a lista de tabelas de todos os municípios em um único DataFrame gigante e retorna
    return pd.concat(tabelas_municipais, ignore_index=True)