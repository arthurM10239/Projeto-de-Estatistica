# Adiciona o diretório atual ao caminho do sistema para permitir a importação de módulos locais
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Importação das bibliotecas de análise de dados e criação de interface
import pandas as pd
import streamlit as st

# Importação de funções personalizadas para geração dos gráficos
from graficos import (
    grafico_distribuicao_por_fase,
    grafico_distribuicao_por_mes,
    grafico_evolucao_por_ciclo,
    grafico_mapa_municipios,
    grafico_relacao_clima_focos,
    grafico_relacao_desmatamento_focos,
    grafico_serie_temporal,
)

# Importação de funções personalizadas de preparação de dados e constantes
from preparacao import (
    METRICAS_FOCOS,
    NOMES_MESES,
    ORDEM_FASES_ENSO,
    agregar_por_ciclo_prodes,
    agregar_por_mes,
    agregar_por_municipio,
    calcular_desvio_da_media_do_mes,
    carregar_base_anual,
    carregar_base_mensal,
    carregar_malha_municipios,
    filtrar_base_anual,
    filtrar_base_mensal,
    listar_variaveis_climaticas_disponiveis,
)

# Configuração inicial da página do Streamlit (título da aba e layout de tela cheia)
st.set_page_config(page_title="Focos de calor, clima e desmatamento no Pará", layout="wide")

# Constante com os créditos e fontes dos dados utilizados no dashboard
FONTES = (
    "Fontes: INPE (BDQueimadas, satélite de referência AQUA_M-T; PRODES), "
    "NASA POWER, NOAA CPC (índice ONI), IBGE."
)

def montar_filtros_laterais(base_mensal):
    
    # Cria o cabeçalho da barra lateral
    st.sidebar.header("Filtros")

    # variaveis armazenar valores max/min de ano
    ano_minimo, ano_maximo = int(base_mensal["ano"].min()), int(base_mensal["ano"].max())

    # 1° parametro aba lateral: Slider de intervalo para os anos
    intervalo_anos = st.sidebar.slider("Período (anos)", ano_minimo, ano_maximo, (ano_minimo, ano_maximo))

    # 2° parametro aba lateral: Slider duplo para o intervalo de meses (usando os nomes dos meses como rótulos)
    mes_inicial, mes_final = st.sidebar.select_slider(
        "Meses do ano", 
        options=list(NOMES_MESES), 
        value=(1, 12), 
        format_func=NOMES_MESES.get
    )

    # Tratamento dado (exclusao dados repetidos e organização crescendo de A-Z nome dos municipios)
    municipios = base_mensal[["codigo_ibge", "nome_municipio"]].drop_duplicates().sort_values("nome_municipio")

    # uniao das colunas com zip, e criacao de referencia com chave utilizando dict
    nome_por_codigo = dict( zip(municipios["codigo_ibge"], municipios["nome_municipio"]) )

    # 3° parametro aba lateral: Caixa de seleção múltipla para filtrar municípios específicos
    codigos_municipios = st.sidebar.multiselect(
        "Municípios", 
        options=list(nome_por_codigo), 
        format_func=nome_por_codigo.get, 
        placeholder="Todos"
    )

    # Filtra as fases do fenômeno ENSO (El Niño/La Niña) presentes na base de dados
    fases_disponiveis = [f for f in ORDEM_FASES_ENSO if f in set(base_mensal["fase_enso"])]
    
    # 4° parametro aba lateral: Seleção múltipla para a fase do ENSO (El Niño, La Niña, Neutro)
    fases_enso = st.sidebar.multiselect("Fase do ENSO", fases_disponiveis, default=fases_disponiveis)
    
    # 5° parametro aba lateral: Botão de opção (radio) para escolher a métrica de focos de calor a ser analisada
    rotulo_metrica = st.sidebar.radio("Medida de focos", list(METRICAS_FOCOS))
    
    # Texto de ajuda/dica exibido na barra lateral inferior
    st.sidebar.caption(
        "Para comparar o ano parcial com os anos fechados, limite os meses ao mesmo intervalo em todos eles."
    )
    
    # Retorna um dicionário contendo todas as escolhas feitas pelo usuário nos filtros
    return {
        "intervalo_anos": intervalo_anos,
        "intervalo_meses": (mes_inicial, mes_final),
        "codigos_municipios": codigos_municipios,
        "fases_enso": fases_enso or fases_disponiveis,
        "rotulo_metrica": rotulo_metrica,
        "coluna_metrica": METRICAS_FOCOS[rotulo_metrica],
    }


def exibir_indicadores(base_filtrada, agregado_mensal):

    # Calcula a área total (em km²) dos municípios selecionados, sem duplicar valores
    area_total = base_filtrada.drop_duplicates("codigo_ibge")["area_km2"].sum()

    # Soma a quantidade total de focos de calor no período filtrado
    total_focos = int(agregado_mensal["quantidade_focos"].sum())

    # Divide a interface horizontalmente em 5 colunas para exibir cartões de métricas (KPIs)
    colunas = st.columns(5)

    # 1ª métrica: Total de focos de calor (com formatação de milhar usando ponto)
    colunas[0].metric("Total de focos", f"{total_focos:,}".replace(",", "."))

    # 2ª métrica: Densidade de focos proporcional à área (focos por 1000 km²)
    colunas[1].metric("Focos por 1000 km²", f"{total_focos / area_total * 1000:.1f}")

    # 3ª métrica: Temperatura máxima média (se a coluna existir nos dados)
    if "temperatura_maxima_media_c" in agregado_mensal.columns:
        colunas[2].metric("Temp. máxima média", f"{agregado_mensal['temperatura_maxima_media_c'].mean():.1f} °C")

    # 4ª métrica: Precipitação/Chuva média mensal (se a coluna existir nos dados)
    if "precipitacao_total_mm" in agregado_mensal.columns:
        colunas[3].metric("Chuva média mensal", f"{agregado_mensal['precipitacao_total_mm'].mean():.0f} mm")

    # 5ª métrica: Quantidade de meses abrangidos pelo recorte do filtro
    colunas[4].metric("Meses no recorte", len(agregado_mensal))


def exibir_relacao_clima(agregado_mensal, filtros):
    # Identifica as colunas de clima disponíveis na base de dados
    variaveis = listar_variaveis_climaticas_disponiveis(agregado_mensal)

    # Se não houver dados de clima, exibe uma mensagem de aviso e interrompe a função
    if not variaveis:
        st.info("Nenhuma variável climática na base. Rode a coleta com BAIXAR_CLIMA = True.")
        return
    
    # Cria duas colunas assimétricas: uma mais estreita para os controles e uma mais larga para o gráfico
    coluna_controles, coluna_grafico = st.columns([1, 3])

    # Controle: Menu suspenso para escolher qual variável climática será cruzada com os focos
    coluna_clima = coluna_controles.selectbox("Variável climática", list(variaveis), format_func=variaveis.get)

    # Controle: Botões de opção para ver os dados brutos ou o desvio (anomalia) em relação à média
    forma_valores = coluna_controles.radio("Valores", ["Originais", "Desvio da média do mês do ano"])

    # Define qual métrica de focos está sendo utilizada
    coluna_metrica = filtros["coluna_metrica"]
    
    tabela = agregado_mensal
    rotulo_clima, rotulo_focos = variaveis[coluna_clima], filtros["rotulo_metrica"]

    # Se o usuário escolheu "Desvio da média", aplica a transformação matemática na tabela e altera os rótulos
    if forma_valores != "Originais":
        tabela = calcular_desvio_da_media_do_mes(agregado_mensal, [coluna_clima, coluna_metrica])
        rotulo_clima, rotulo_focos = f"Desvio: {rotulo_clima}", f"Desvio: {rotulo_focos}"

    # Isola as duas colunas escolhidas (clima e focos) e remove valores nulos (NaN)
    pares = tabela[[coluna_clima, coluna_metrica]].dropna()

    # Calcula a correlação estatística de Spearman se houver mais de 2 pontos de dados
    correlacao = pares.corr(method="spearman").iloc[0, 1] if len(pares) > 2 else float("nan")

    # Exibe o valor numérico da correlação e a quantidade de pares analisados na coluna de controles
    coluna_controles.metric("Correlação de Spearman", "—" if pd.isna(correlacao) else f"{correlacao:.2f}")
    coluna_controles.metric("Pares de valores", len(pares))

    # Renderiza o gráfico de dispersão (scatter plot) relacionando clima e focos na coluna de gráfico
    coluna_grafico.plotly_chart(
        grafico_relacao_clima_focos(tabela, coluna_clima, rotulo_clima, coluna_metrica, rotulo_focos),
        width="stretch",
    )


def exibir_aba_mensal(base_filtrada, filtros):
    # Agrupa os dados em granularidade mensal
    agregado_mensal = agregar_por_mes(base_filtrada)

    # Variáveis auxiliares de rótulos baseadas nos filtros
    coluna_metrica, rotulo_metrica = filtros["coluna_metrica"], filtros["rotulo_metrica"]

    # Chamada da função que monta a barra superior com métricas principais (KPIs)
    exibir_indicadores(base_filtrada, agregado_mensal)

    # Gráfico 1: Linha do tempo (série histórica) dos focos ao longo dos meses
    st.plotly_chart(grafico_serie_temporal(agregado_mensal, coluna_metrica, rotulo_metrica), width="stretch")

    # Divide a tela ao meio para posicionar dois gráficos lado a lado
    esquerda, direita = st.columns(2)

    # Gráfico 2 (Esquerda): Gráfico de barras com a sazonalidade (distribuição por meses do ano)
    esquerda.plotly_chart(
        grafico_distribuicao_por_mes(agregado_mensal, coluna_metrica, rotulo_metrica), width="stretch"
    )

    # Gráfico 3 (Direita): Gráfico com a distribuição de focos em relação à fase do ENSO (El Niño, etc)
    direita.plotly_chart(
        grafico_distribuicao_por_fase(agregado_mensal, coluna_metrica, rotulo_metrica), width="stretch"
    )

    # Chamada da função que monta a seção de cruzamento de dados meteorológicos
    exibir_relacao_clima(agregado_mensal, filtros)

    # Carrega os dados geográficos em GeoJSON para plotar o mapa
    malha = carregar_malha_municipios()

    # Valida se o mapa existe. Se sim, plota o mapa coroplético; se não, exibe aviso
    if malha is None:
        st.info("Mapa indisponível: falta o arquivo malha_municipios_para.geojson em dados/brutos.")
    else:
        st.plotly_chart(
            grafico_mapa_municipios(agregar_por_municipio(base_filtrada), malha, coluna_metrica, rotulo_metrica),
            width="stretch",
        )

    # Cria uma seção recolhível (expander) para que o usuário possa visualizar e inspecionar a tabela de dados brutos
    with st.expander("Ver tabela mensal agregada"):
        st.dataframe(agregado_mensal, width="stretch", hide_index=True)


def exibir_aba_anual(base_anual, filtros):

    # Aviso ao usuário de que filtros de meses ou ENSO não afetam esta visualização anual
    st.caption("Esta aba usa apenas os filtros de período e de municípios.")

    # Filtra os dados anuais baseados no intervalo de anos e municípios escolhidos na barra lateral
    base_anual_filtrada = filtrar_base_anual(base_anual, filtros["intervalo_anos"], filtros["codigos_municipios"])

    # Tratamento de erro caso os filtros resultem em uma base vazia
    if base_anual_filtrada.empty:
        st.warning("Nenhum dado para os filtros selecionados.")
        return
    
    # Agrupa os dados pelos ciclos do PRODES (agosto de um ano a julho do outro)
    agregado_ciclos = agregar_por_ciclo_prodes(base_anual_filtrada)

    # Gráfico 1 (Anual): Gráfico de evolução temporal do desmatamento por ciclo
    st.plotly_chart(grafico_evolucao_por_ciclo(agregado_ciclos), width="stretch")

    # Cria um interruptor (toggle) interativo para permitir visualização logarítmica
    usar_escala_logaritmica = st.toggle("Escala logarítmica nos dois eixos")

    # Gráfico 2 (Anual): Gráfico de relação/dispersão entre a área desmatada e quantidade de focos
    st.plotly_chart(
        grafico_relacao_desmatamento_focos(base_anual_filtrada, usar_escala_logaritmica), width="stretch"
    )

    # Seção recolhível (expander) mostrando os dados em tabela da aba anual
    with st.expander("Ver tabela por ciclo PRODES"):
        st.dataframe(agregado_ciclos, width="stretch", hide_index=True)


def executar_dashboard():
    # Define o título principal em exibição no topo da aplicação
    st.title("Focos de calor, clima e desmatamento no Pará")

    # Carrega o conjunto de dados principal (mensal) a ser utilizado
    base_mensal = carregar_base_mensal()

    # Verifica se os dados foram encontrados. Se não, orienta o usuário a rodar o script de coleta
    if base_mensal is None:
        st.error("base_mensal.csv não encontrado. Rode antes: python coleta/executar_coleta.py")
        st.caption(FONTES)
        return
    
    # Inicializa a barra lateral e captura os inputs de filtros escolhidos pelo usuário
    filtros = montar_filtros_laterais(base_mensal)

    # Aplica efetivamente todos os filtros capturados em cima da base de dados original
    base_filtrada = filtrar_base_mensal(
        base_mensal, filtros["intervalo_anos"], filtros["intervalo_meses"],
        filtros["codigos_municipios"], filtros["fases_enso"],
    )

    # Cria os elementos de abas (Tabs) para separar visualizações mensais de visões anuais
    aba_mensal, aba_anual = st.tabs(["Mensal", "Anual (ciclo PRODES)"])

    # Lógica de renderização para o conteúdo da aba "Mensal"
    with aba_mensal:
        if base_filtrada.empty:
            st.warning("Nenhum dado para os filtros selecionados.")
        else:
            exibir_aba_mensal(base_filtrada, filtros)
            
    # Lógica de renderização para o conteúdo da aba "Anual"
    with aba_anual:
        base_anual = carregar_base_anual()
        if base_anual is None:
            st.warning("base_anual_prodes.csv não encontrado. Falta o shapefile do PRODES.")
        else:
            exibir_aba_anual(base_anual, filtros)
            
    # Insere o rodapé final do dashboard com as fontes dos dados
    st.caption(FONTES)

# Aciona a função principal que executa e engatilha toda a construção do Dashboard
executar_dashboard()