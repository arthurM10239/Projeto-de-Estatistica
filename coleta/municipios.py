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


# Consulta a API de malhas do IBGE para obter dados geográficos e territoriais de um município específico
def buscar_metadados_malha(codigo_ibge):
    # Faz a requisição na API e converte a resposta para um formato de dicionário Python (JSON)
    conteudo = requisitar_com_tentativas(URL_METADADOS_MALHA_IBGE.format(codigo=codigo_ibge)).json()
    
    # Garante que vai pegar o primeiro registro, independente se a API retornar uma lista ou um objeto único
    registro = conteudo[0] if isinstance(conteudo, list) else conteudo
    
    # Retorna apenas as informações úteis extraídas da resposta bruta, convertendo os textos para números decimais (float)
    return {
        "latitude": float(registro["centroide"]["latitude"]),
        "longitude": float(registro["centroide"]["longitude"]),
        "area_km2": float(registro["area"]["dimensao"]),
    }


# Monta e salva a tabela principal de todos os municípios do Pará, buscando na API caso o arquivo ainda não exista
def carregar_municipios_para():
    # Verifica se o arquivo CSV já foi gerado anteriormente para evitar fazer requisições demoradas novamente
    if ARQUIVO_MUNICIPIOS.exists():
        return pd.read_csv(ARQUIVO_MUNICIPIOS)
        
    # Pede para a API do IBGE a lista completa de todos os municípios pertencentes ao estado do Pará
    lista_municipios = requisitar_com_tentativas(URL_MUNICIPIOS_IBGE.format(uf=CODIGO_UF_PARA)).json()
    registros = []
    
    # Percorre a lista retornada pela API, mostrando o progresso no terminal
    for posicao, municipio in enumerate(lista_municipios, start=1):
        print(f"  IBGE {posicao}/{len(lista_municipios)}: {municipio['nome']}")
        
        # Adiciona os dados básicos do município e junta com os dados geográficos detalhados
        registros.append({
            "codigo_ibge": int(municipio["id"]),
            "nome_municipio": municipio["nome"],
            "nome_normalizado": normalizar_nome(municipio["nome"]), # Remove acentos e padroniza para facilitar cruzamentos futuros
            **buscar_metadados_malha(municipio["id"]), # Desempacota (**) o dicionário de latitude/longitude e área diretamente aqui
        })
        
        # Faz uma pequena pausa de 0.2 segundos para não sobrecarregar a API do IBGE com muitas requisições simultâneas
        time.sleep(0.2)
        
    # Converte a lista de dicionários em uma tabela estruturada do Pandas (DataFrame)
    tabela_municipios = pd.DataFrame(registros)
    
    # Cria a pasta de destino caso não exista e salva a tabela no formato CSV para usos futuros
    ARQUIVO_MUNICIPIOS.parent.mkdir(parents=True, exist_ok=True)
    tabela_municipios.to_csv(ARQUIVO_MUNICIPIOS, index=False)
    
    return tabela_municipios


# Baixa e salva o arquivo geográfico (GeoJSON) que contém o desenho do mapa (fronteiras) de todos os municípios
def baixar_malha_municipios_para():
    # Se o arquivo de mapa já existir na pasta local, encerra a função sem fazer nada
    if ARQUIVO_MALHA_MUNICIPIOS.exists():
        return
        
    # Define as configurações exigidas pela API do IBGE para retornar o mapa desenhado das cidades
    parametros = {
        "formato": "application/vnd.geo+json", # Pede o retorno especificamente no formato de mapa GeoJSON
        "intrarregiao": "municipio",           # Especifica que queremos a divisão por municípios
        "qualidade": "intermediaria",          # Define o nível de detalhe do desenho das bordas
    }
    
    # Faz a requisição passando a UF do Pará e os parâmetros configurados acima
    resposta = requisitar_com_tentativas(URL_MALHA_ESTADO_IBGE.format(uf=CODIGO_UF_PARA), parametros)
    
    # Cria a pasta de destino caso não exista e grava o texto puro da resposta no arquivo GeoJSON
    ARQUIVO_MALHA_MUNICIPIOS.parent.mkdir(parents=True, exist_ok=True)
    ARQUIVO_MALHA_MUNICIPIOS.write_text(resposta.text, encoding="utf-8")