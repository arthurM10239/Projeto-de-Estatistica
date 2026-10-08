import zipfile

import geopandas as gpd
import pandas as pd

from configuracao import (
    ANO_FINAL_COMPLETO,
    ANO_INICIAL_ANALISE,
    ARQUIVO_DESMATAMENTO_MUNICIPIOS,
    ARQUIVO_MALHA_MUNICIPIOS,
    PASTA_PRODES_SHAPEFILE,
    PROJECAO_AREA_EQUIVALENTE,
)

# Listas de possíveis nomes para as colunas dentro do arquivo Shapefile (para garantir compatibilidade com diferentes versões e anos dos dados do PRODES)
NOMES_POSSIVEIS_COLUNA_ANO = ("year", "ano", "ano_prodes")
NOMES_POSSIVEIS_COLUNA_CLASSE = ("main_class", "class_name", "classe", "classname")


# Procura o arquivo Shapefile do PRODES dentro da pasta configurada, aceitando tanto arquivos compactados (.zip) quanto já extraídos (.shp)
def localizar_shapefile_prodes():
    for arquivo_zip in sorted(PASTA_PRODES_SHAPEFILE.glob("*.zip")):
        with zipfile.ZipFile(arquivo_zip) as conteudo_zip:
            camadas = [nome for nome in conteudo_zip.namelist() if nome.lower().endswith(".shp")]
        if camadas:
            return f"zip://{arquivo_zip.resolve().as_posix()}!{camadas[0]}"
    for arquivo_shp in sorted(PASTA_PRODES_SHAPEFILE.rglob("*.shp")):
        return str(arquivo_shp)
    return None


# Função auxiliar para buscar o nome exato de uma coluna ignorando se ela foi escrita com letras maiúsculas ou minúsculas no arquivo original
def encontrar_coluna_por_nome(colunas, nomes_possiveis):
    colunas_minusculas = {coluna.lower(): coluna for coluna in colunas}
    for nome in nomes_possiveis:
        if nome in colunas_minusculas:
            return colunas_minusculas[nome]
    return None


# Carrega o arquivo geográfico (GeoJSON) contendo o desenho (polígonos) dos municípios e converte o código da área para o padrão IBGE
def carregar_malha_municipios_geografica():
    malha = gpd.read_file(ARQUIVO_MALHA_MUNICIPIOS)
    malha["codigo_ibge"] = malha["codarea"].astype(int)
    return malha[["codigo_ibge", "geometry"]]


# Lê os polígonos de desmatamento do PRODES, otimizando a leitura para carregar apenas as áreas que caem dentro do estado do Pará (bbox) e filtrando as classes corretas
def carregar_poligonos_desmatamento(caminho_shapefile, malha_municipios):
    poligonos = gpd.read_file(caminho_shapefile, bbox=malha_municipios)
    print(f"  Poligonos lidos na area do Para: {len(poligonos)}")
    print(f"  Colunas do shapefile: {list(poligonos.columns)}")
    
    coluna_ano = encontrar_coluna_por_nome(poligonos.columns, NOMES_POSSIVEIS_COLUNA_ANO)
    if coluna_ano is None:
        raise KeyError(f"Coluna de ano nao encontrada. Colunas: {list(poligonos.columns)}")
        
    poligonos["ano_prodes"] = pd.to_numeric(poligonos[coluna_ano], errors="coerce")
    poligonos = poligonos[poligonos["ano_prodes"].between(ANO_INICIAL_ANALISE, ANO_FINAL_COMPLETO)]
    
    coluna_classe = encontrar_coluna_por_nome(poligonos.columns, NOMES_POSSIVEIS_COLUNA_CLASSE)
    if coluna_classe is not None:
        print(f"  Classes em '{coluna_classe}': {poligonos[coluna_classe].value_counts().to_dict()}")
        eh_desmatamento = poligonos[coluna_classe].astype(str).str.lower().str.startswith("desmat")
        if eh_desmatamento.any():
            poligonos = poligonos[eh_desmatamento]
        else:
            print("  Nenhuma classe comeca com 'desmat'; todos os poligonos foram mantidos.")
            
    return poligonos[["ano_prodes", "geometry"]]


# Realiza o processamento geoespacial pesado: cruza os polígonos de desmatamento com o mapa dos municípios para calcular a área exata desmatada (em km²) por cidade a cada ano
def calcular_desmatamento_por_municipio():
    caminho_shapefile = localizar_shapefile_prodes()
    if caminho_shapefile is None:
        return None
        
    malha_municipios = carregar_malha_municipios_geografica()
    poligonos = carregar_poligonos_desmatamento(caminho_shapefile, malha_municipios)
    
    # Converte os mapas para uma projeção cartográfica de área equivalente para garantir que o cálculo de km² seja matematicamente correto
    poligonos = poligonos.to_crs(PROJECAO_AREA_EQUIVALENTE)
    malha_projetada = malha_municipios.to_crs(PROJECAO_AREA_EQUIVALENTE)
    
    # Corrige possíveis defeitos na geometria dos polígonos (ex: linhas se cruzando) antes de fazer o recorte
    poligonos["geometry"] = poligonos.geometry.make_valid()
    malha_projetada["geometry"] = malha_projetada.geometry.make_valid()
    
    # Recorta (faz a interseção) o mapa de desmatamento usando as fronteiras dos municípios como molde
    intersecoes = gpd.overlay(poligonos, malha_projetada, how="intersection", keep_geom_type=True)
    
    # Calcula a área da geometria recortada e divide por 1 milhão para converter de metros quadrados para quilômetros quadrados
    intersecoes["desmatamento_km2"] = intersecoes.geometry.area / 1_000_000
    
    # Soma toda a área desmatada agrupando pelo código da cidade e pelo ano do ciclo PRODES
    desmatamento = intersecoes.groupby(["codigo_ibge", "ano_prodes"])["desmatamento_km2"].sum().reset_index()
    
    # Cria uma tabela matriz vazia garantindo que todas as cidades e todos os anos existam, mesmo as que não tiveram desmatamento
    grade_completa = pd.MultiIndex.from_product(
        [sorted(malha_municipios["codigo_ibge"]), range(ANO_INICIAL_ANALISE, ANO_FINAL_COMPLETO + 1)],
        names=["codigo_ibge", "ano_prodes"],
    ).to_frame(index=False)
    
    # Mescla a matriz vazia com os dados calculados e preenche com zero os municípios/anos sem registro de desmatamento
    desmatamento = grade_completa.merge(desmatamento, on=["codigo_ibge", "ano_prodes"], how="left")
    desmatamento["desmatamento_km2"] = desmatamento["desmatamento_km2"].fillna(0)
    desmatamento = desmatamento.astype({"codigo_ibge": int, "ano_prodes": int})
    
    print("  Total do Para por ciclo PRODES (km2), confira com o TerraBrasilis:")
    print(desmatamento.groupby("ano_prodes")["desmatamento_km2"].sum().round(1).to_string())
    
    # Salva o resultado final em CSV para não precisar refazer esse cálculo demorado nas próximas vezes
    ARQUIVO_DESMATAMENTO_MUNICIPIOS.parent.mkdir(parents=True, exist_ok=True)
    desmatamento.to_csv(ARQUIVO_DESMATAMENTO_MUNICIPIOS, index=False)
    
    return desmatamento


# Função principal que funciona como ponto de entrada: se o arquivo CSV já existe, ele é lido rapidamente; se não, inicia o cálculo geoespacial
def carregar_desmatamento_anual_para():
    if ARQUIVO_DESMATAMENTO_MUNICIPIOS.exists():
        return pd.read_csv(ARQUIVO_DESMATAMENTO_MUNICIPIOS)
    return calcular_desmatamento_por_municipio()