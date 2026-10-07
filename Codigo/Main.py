import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import glob
import os

# Configuração inicial da pagina
st.set_page_config(page_title='Dashboard Queimadas - Pará', layout='wide')

# Título Principal
st.title("Dashboard de Análise de Queimadas no Pará")
st.markdown("Análise estatística e espacial dos focos de calor com base em dados de satélite de múltiplos anos.")

# --- TRATAMENTO DE DADOS ---
@st.cache_data
def carregar_dados():
    # Busca dinamicamente todos os arquivos CSV na pasta DataSets
    arquivos_csv = glob.glob(os.path.join('DataSets', '*.csv'))
    
    if not arquivos_csv:
        # Retorna um DataFrame vazio caso não encontre nenhum arquivo
        return pd.DataFrame()
        
    lista_dfs = []
    for arquivo in arquivos_csv:
        try:
            df_temp = pd.read_csv(arquivo)
            lista_dfs.append(df_temp)
        except Exception as e:
            st.error(f"Erro ao carregar o arquivo {arquivo}: {e}")
            
    # Concatena todos os arquivos lidos em um único DataFrame
    df = pd.concat(lista_dfs, ignore_index=True)
    
    # Tratamento de Data/Hora e criação de novas colunas temporais
    df['DataHora'] = pd.to_datetime(df['DataHora'])
    df['Ano'] = df['DataHora'].dt.year
    df['Mes'] = df['DataHora'].dt.month
    df['Dia_da_Semana'] = df['DataHora'].dt.day_name()
    
    # Coluna auxiliar para gráficos contínuos no tempo
    df['AnoMes'] = df['DataHora'].dt.to_period('M').astype(str)
    
    return df

df = carregar_dados()

if df.empty:
    st.error("Nenhum dado encontrado. Certifique-se de que os arquivos CSV estão na pasta 'DataSets/'.")
    st.stop()

# --- BARRA LATERAL (FILTROS) ---
with st.sidebar:
    st.header("Configurações e Filtros")

    # Filtro de Anos
    anos_disponiveis = sorted(df['Ano'].unique().tolist())
    anos_selecionados = st.multiselect(
        "Selecione os Anos",
        options=anos_disponiveis,
        default=anos_disponiveis # Seleciona todos por padrão
    )

    # Filtro de Municípios
    municipios_disponiveis = sorted(df['Municipio'].unique().tolist())
    municipios_padrao = [m for m in ['MOJU', 'BELÉM', 'SANTANA DO ARAGUAIA'] if m in municipios_disponiveis]
    
    municipios_selecionados = st.multiselect(
        "Selecione os Municípios",
        options=municipios_disponiveis,
        default=municipios_padrao if municipios_padrao else municipios_disponiveis[:5]
    )

    # Filtro de Meses (Slider)
    meses_selecionados = st.slider(
        "Selecione o intervalo de Meses", 
        min_value=1, 
        max_value=12, 
        value=(1, 12)
    )
    
    # Filtro de Bioma
    biomas_disponiveis = df['Bioma'].unique().tolist()
    biomas_selecionados = st.multiselect(
        "Selecione o Bioma",
        options=biomas_disponiveis,
        default=biomas_disponiveis
    )

# --- APLICAÇÃO DOS FILTROS ---
df_filtrado = df[
    (df['Ano'].isin(anos_selecionados)) &
    (df['Municipio'].isin(municipios_selecionados)) &
    (df['Mes'] >= meses_selecionados[0]) &
    (df['Mes'] <= meses_selecionados[1]) &
    (df['Bioma'].isin(biomas_selecionados))
]

# --- ORGANIZAÇÃO EM ABAS ---
aba_visao_geral, aba_mapa, aba_dados = st.tabs([
    'Visão Geral', 'Mapa de Focos', 'Dados Brutos'
])

with aba_visao_geral:
    st.subheader("Métricas Principais do Período Selecionado")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Focos Registrados", f"{len(df_filtrado):,}")
    
    media_chuva = df_filtrado['DiaSemChuva'].mean() if not df_filtrado.empty else 0
    risco_fogo = df_filtrado['RiscoFogo'].mean() if not df_filtrado.empty else 0
    frp_medio = df_filtrado['FRP'].mean() if not df_filtrado.empty else 0
    
    col2.metric("Média de Dias Sem Chuva", f"{media_chuva:.1f}")
    col3.metric("Risco de Fogo Médio", f"{risco_fogo:.2f}")
    col4.metric("FRP Médio (Intensidade)", f"{frp_medio:.1f}")

    st.divider()
    st.subheader("Análises e Relações Estatísticas")
    
    if not df_filtrado.empty:
        col_grafico1, col_grafico2 = st.columns(2)
        
        with col_grafico1:
            # Gráfico de Linha: Evolução Temporal Contínua (Ano-Mês)
            focos_temporal = df_filtrado.groupby(['AnoMes']).size().reset_index(name='Quantidade')
            fig_linha = px.line(focos_temporal, x='AnoMes', y='Quantidade', markers=True, 
                                title='Evolução de Focos de Calor ao longo do Tempo')
            # Ajuste para melhorar a legibilidade do eixo X
            fig_linha.update_layout(xaxis_title='Período', yaxis_title='Qtd. de Focos')
            st.plotly_chart(fig_linha, use_container_width=True)
            
        with col_grafico2:
            # Gráfico de Barras: Top 10 Municípios
            focos_municipio = df_filtrado['Municipio'].value_counts().head(10).reset_index()
            focos_municipio.columns = ['Municipio', 'Quantidade']
            fig_barra = px.bar(focos_municipio, x='Municipio', y='Quantidade', 
                               title='Top 10 Municípios com Mais Focos',
                               color='Quantidade', color_continuous_scale='Reds')
            st.plotly_chart(fig_barra, use_container_width=True)
            
        # Gráfico de Dispersão
        st.markdown("### Correlação: Risco de Fogo vs. Dias Sem Chuva")

        df_scatter = df_filtrado.dropna(subset=['DiaSemChuva', 'RiscoFogo', 'FRP'])

        fig_scatter = px.scatter(df_scatter, x='DiaSemChuva', y='RiscoFogo', 
                                 color='FRP', size='FRP', hover_data=['Municipio', 'DataHora', 'Ano'],
                                 title='Relação entre Dias sem Chuva, Risco de Fogo e Intensidade (FRP)')
        st.plotly_chart(fig_scatter, use_container_width=True)
        
    else:
        st.warning("Ajuste os filtros na barra lateral para gerar as visualizações dos gráficos.")

with aba_mapa:
    st.subheader("Distribuição Espacial dos Focos de Calor")
    st.markdown("Visualização baseada nas coordenadas de latitude e longitude registradas pelos satélites.")
    if not df_filtrado.empty:
        df_mapa = df_filtrado[['Latitude', 'Longitude']].rename(columns={'Latitude': 'lat', 'Longitude': 'lon'})
        st.map(df_mapa)
    else:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")

with aba_dados:
    st.subheader('Tabela de Dados Filtrados')
    st.dataframe(df_filtrado, use_container_width=True)
    
    if not df_filtrado.empty:
        csv = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Baixar Dados Filtrados (CSV)",
            data=csv,
            file_name='dados_queimadas_filtrados.csv',
            mime='text/csv',
        )