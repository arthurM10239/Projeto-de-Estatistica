import io

import pandas as pd

from configuracao import (
    ARQUIVO_ONI,
    LIMIAR_ANOMALIA_ENSO,
    MINIMO_TRIMESTRES_CONSECUTIVOS_ENSO,
    URL_ONI_NOAA,
)
from utilidades import requisitar_com_tentativas

# Dicionário que mapeia a sigla do trimestre em inglês (DJF = Dezembro, Janeiro, Fevereiro) para o número do mês central correspondente
MES_CENTRAL_POR_TRIMESTRE = {
    "DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
    "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12,
}

# Baixa o arquivo de texto contendo o histórico do índice ONI direto do site da NOAA caso ele ainda não esteja salvo localmente
def baixar_texto_oni():
    if not ARQUIVO_ONI.exists():
        ARQUIVO_ONI.parent.mkdir(parents=True, exist_ok=True)
        ARQUIVO_ONI.write_text(requisitar_com_tentativas(URL_ONI_NOAA).text, encoding="utf-8")
    return ARQUIVO_ONI.read_text(encoding="utf-8")

# Classifica os meses em "El Niño", "La Niña" ou "Neutro" seguindo a regra oficial (a anomalia de temperatura deve atingir o limiar por meses consecutivos)
def classificar_fases_enso(anomalias):
    # Inicializa uma série onde todos os meses começam classificados como "Neutro" por padrão
    fases = pd.Series("Neutro", index=anomalias.index)
    
    # Loop que avalia separadamente as condições para El Niño (anomalia positiva) e La Niña (anomalia negativa)
    for rotulo_fase, condicao in (
        ("El Niño", anomalias >= LIMIAR_ANOMALIA_ENSO),
        ("La Niña", anomalias <= -LIMIAR_ANOMALIA_ENSO),
    ):
        # Lógica para criar um ID único para cada bloco ininterrupto de meses que atendem à condição
        identificador_sequencia = (condicao != condicao.shift()).cumsum()
        
        # Conta quantos meses durou cada uma dessas sequências contínuas
        tamanho_sequencia = condicao.groupby(identificador_sequencia).transform("size")
        
        # Verifica se estamos na última sequência registrada (para lidar com eventos atuais que ainda não atingiram o tempo mínimo, mas estão em andamento)
        sequencia_em_andamento = identificador_sequencia == identificador_sequencia.iloc[-1]
        
        # Valida se a sequência durou o número mínimo de trimestres exigidos para ser oficialmente declarada como fenômeno
        evento_valido = tamanho_sequencia >= MINIMO_TRIMESTRES_CONSECUTIVOS_ENSO
        
        # Aplica o rótulo ("El Niño" ou "La Niña") apenas aos meses que satisfazem todas as regras meteorológicas
        fases[condicao & (evento_valido | sequencia_em_andamento)] = rotulo_fase
        
    return fases

# Processa o texto bruto baixado da NOAA e constrói uma tabela organizada com o histórico mensal de fases do clima
def montar_enso_mensal():
    # Lê os dados em formato de texto interpretando qualquer quantidade de espaços em branco (\s+) como divisores de coluna
    tabela_oni = pd.read_csv(io.StringIO(baixar_texto_oni()), sep=r"\s+")
    
    # Renomeia as colunas para o padrão do projeto
    tabela_oni.columns = ["trimestre", "ano", "temperatura_media", "anomalia_oni"]
    
    # Cria a coluna numérica do mês cruzando a sigla do trimestre com o dicionário definido no topo do arquivo
    tabela_oni["mes"] = tabela_oni["trimestre"].map(MES_CENTRAL_POR_TRIMESTRE)
    
    # Remove eventuais linhas sem mês mapeado (lixo do texto lido), ordena tudo cronologicamente e redefine o índice da tabela
    tabela_oni = tabela_oni.dropna(subset=["mes"]).sort_values(["ano", "mes"]).reset_index(drop=True)
    
    # Aciona a função de classificação matemática para rotular cada linha baseada na variação histórica da anomalia
    tabela_oni["fase_enso"] = classificar_fases_enso(tabela_oni["anomalia_oni"])
    
    # Retorna a tabela final selecionando apenas as colunas úteis e garantindo que ano e mês sejam números inteiros
    return tabela_oni[["ano", "mes", "anomalia_oni", "fase_enso"]].astype({"ano": int, "mes": int})