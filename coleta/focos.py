import zipfile

import pandas as pd

from configuracao import NOME_ESTADO_PARA, PASTA_FOCOS, SATELITE_REFERENCIA
from utilidades import normalizar_nome

# Dicionário mapeando as variações de nomes de colunas que podem vir no arquivo bruto para um nome padrão interno
APELIDOS_COLUNAS_FOCOS = {
    "datahora": "data_hora",
    "data_hora_gmt": "data_hora",
    "data_pas": "data_hora",
    "satelite": "satelite",
    "municipio": "municipio",
    "estado": "estado",
}

# Define quantas linhas do CSV o Pandas vai ler por vez, evitando que o computador trave por falta de memória RAM
TAMANHO_BLOCO_LEITURA = 400_000

# Tipos de arquivos aceitos pelo sistema para a leitura dos focos de calor
EXTENSOES_ACEITAS = (".csv", ".zip")

# Varre a pasta configurada e retorna uma lista em ordem alfabética com todos os arquivos válidos para processamento
def listar_arquivos_focos():
    if not PASTA_FOCOS.exists():
        return []
    # Ignora arquivos ocultos (que começam com ".") e arquivos com extensões não permitidas
    return sorted(
        caminho for caminho in PASTA_FOCOS.iterdir()
        if caminho.suffix.lower() in EXTENSOES_ACEITAS and not caminho.name.startswith(".")
    )

# Prepara a leitura de forma inteligente, lidando com um CSV comum ou extraindo automaticamente o CSV de dentro de um arquivo ZIP
def abrir_arquivo_focos(caminho_arquivo):
    if caminho_arquivo.suffix.lower() != ".zip":
        return caminho_arquivo.open("rb")
        
    arquivo_zip = zipfile.ZipFile(caminho_arquivo)
    
    # Procura dentro do arquivo zipado o nome de qualquer arquivo que termine em .csv
    nomes_csv = [nome for nome in arquivo_zip.namelist() if nome.lower().endswith(".csv")]
    if not nomes_csv:
        raise ValueError(f"O arquivo {caminho_arquivo.name} nao contem CSV.")
        
    # Abre e retorna o fluxo de leitura do primeiro arquivo CSV encontrado no ZIP
    return arquivo_zip.open(nomes_csv[0])

# Função auxiliar de otimização que diz ao Pandas para carregar na memória apenas as colunas que estão no nosso dicionário
def eh_coluna_de_interesse(nome_coluna):
    return nome_coluna.strip().lower() in APELIDOS_COLUNAS_FOCOS

# Lê os dados brutos em lotes, aplica os filtros de satélite e estado, e retorna apenas os registros úteis do Pará
def extrair_focos_referencia_para(caminho_arquivo):
    blocos_filtrados = []
    
    # Abre o fluxo de leitura do arquivo (seja ZIP ou CSV) e garante seu fechamento automático após o uso
    with abrir_arquivo_focos(caminho_arquivo) as fluxo:
        
        # Inicia a leitura do CSV quebrado em lotes (chunks)
        leitor = pd.read_csv(
            fluxo,
            usecols=eh_coluna_de_interesse, # Carrega apenas as colunas validadas
            dtype=str, # Lê tudo como texto inicialmente para evitar erros de tipagem
            encoding="utf-8",
            encoding_errors="replace", # Substitui caracteres estranhos sem quebrar a execução
            chunksize=TAMANHO_BLOCO_LEITURA,
        )
        
        # Itera sobre cada pedaço (bloco) do arquivo grande
        for bloco in leitor:
            # Padroniza os nomes das colunas de acordo com o dicionário
            bloco.columns = [APELIDOS_COLUNAS_FOCOS[coluna.strip().lower()] for coluna in bloco.columns]
            
            # Filtra os dados descartando todos os satélites que não sejam o oficial de referência (AQUA_M-T)
            bloco = bloco[bloco["satelite"].str.strip() == SATELITE_REFERENCIA]
            
            # Normaliza os nomes dos estados do bloco removendo acentos e deixando tudo em minúsculo
            estados_normalizados = {valor: normalizar_nome(valor) for valor in bloco["estado"].dropna().unique()}
            
            # Filtra os dados descartando os focos que aconteceram fora do estado alvo (Pará)
            bloco = bloco[bloco["estado"].map(estados_normalizados) == NOME_ESTADO_PARA]
            
            # Se restou algum dado após os filtros, guarda apenas as colunas de data e município na lista
            if not bloco.empty:
                blocos_filtrados.append(bloco[["data_hora", "municipio"]])
                
    # Se ao final da leitura nenhum bloco teve focos do Pará no satélite de referência, retorna uma tabela vazia com as colunas corretas
    if not blocos_filtrados:
        return pd.DataFrame(columns=["data_hora", "municipio"])
        
    # Junta todos os pequenos blocos filtrados em uma única tabela contínua
    return pd.concat(blocos_filtrados, ignore_index=True)

# Processa todos os arquivos de focos, extrai o mês/ano e cruza os nomes das cidades com a base oficial do IBGE para gerar a contagem
def contar_focos_mensais_por_municipio(tabela_municipios, correcoes_nomes=None):
    arquivos_focos = listar_arquivos_focos()
    
    # Se não encontrar nenhum arquivo na pasta, encerra a função
    if not arquivos_focos:
        return None
        
    partes = []
    
    # Executa a extração filtrada para cada arquivo encontrado na pasta
    for caminho_arquivo in arquivos_focos:
        focos_do_arquivo = extrair_focos_referencia_para(caminho_arquivo)
        print(f"  {caminho_arquivo.name}: {len(focos_do_arquivo)} focos do Para no satelite de referencia")
        partes.append(focos_do_arquivo)
        
    # Empilha todos os dados filtrados de todos os arquivos em uma grande tabela geral de focos do Pará
    focos_para = pd.concat(partes, ignore_index=True)
    
    # Converte a coluna de texto para formato Data/Hora oficial do Pandas
    datas = pd.to_datetime(focos_para["data_hora"], errors="coerce", format="mixed")
    
    # Extrai ano e mês e descarta qualquer linha onde não foi possível identificar a data
    focos_para = focos_para.assign(ano=datas.dt.year, mes=datas.dt.month).dropna(subset=["ano", "mes"])
    
    # Remove acentos do nome do município vindo dos focos e aplica possíveis correções manuais (ex: "Belem" -> "Belém") passadas por parâmetro
    focos_para["nome_normalizado"] = focos_para["municipio"].map(normalizar_nome).replace(correcoes_nomes or {})
    
    # Cruza a tabela de focos com a base oficial de municípios do IBGE usando o nome normalizado como ponte (Merge / Join)
    focos_com_codigo = focos_para.merge(
        tabela_municipios[["nome_normalizado", "codigo_ibge"]], on="nome_normalizado", how="left"
    )
    
    # Isola e avisa no terminal caso existam municípios listados no arquivo de focos que não foram encontrados na tabela do IBGE
    sem_correspondencia = focos_com_codigo[focos_com_codigo["codigo_ibge"].isna()]
    if not sem_correspondencia.empty:
        print("  ATENCAO: municipios sem correspondencia no IBGE (focos descartados):")
        print("  ", sem_correspondencia["municipio"].value_counts().to_dict())
        
    # Gera a tabela final: Agrupa por cidade, ano e mês, contando o tamanho (size) de focos em cada grupo
    contagem = (
        focos_com_codigo.dropna(subset=["codigo_ibge"])
        .groupby(["codigo_ibge", "ano", "mes"])
        .size()
        .rename("quantidade_focos")
        .reset_index()
    )
    
    # Retorna o resultado final garantindo que os identificadores sejam tratados como números inteiros, e não como decimais
    return contagem.astype({"codigo_ibge": int, "ano": int, "mes": int})