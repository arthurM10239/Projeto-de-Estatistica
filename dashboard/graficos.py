import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from preparacao import NOMES_MESES, ORDEM_FASES_ENSO

# Dicionário mapeando cada fase do fenômeno ENSO para uma cor hexadecimal específica
CORES_FASES_ENSO = {"La Niña": "#4a98c9", "Neutro": "#6b6b6b", "El Niño": "#c84a02"}
COR_DESMATAMENTO = "#5C6B3C"
COR_FOCOS = "#9A8B5F"
COR_LINHA_GUIA = "#9A8B5F"

# Paleta de cores sequencial em tons de azul
ESCALA_SEQUENCIAL_ANOS = ["#cfe3f2", "#9cc4e0", "#6aa5cd", "#3f7fae", "#245b85", "#12395b"]

# Extrai os nomes dos meses para ordenar os eixos dos gráficos
ORDEM_NOMES_MESES = list(NOMES_MESES.values())

# Dicionário de configuração padrão de layout
LAYOUT_PADRAO = {
    "template": "plotly_dark",
    "paper_bgcolor": "#101811",
    "plot_bgcolor": "#101811",
    "font": {"color": "#F5F3EC"},
    "hoverlabel": {"font_size": 13},
    "margin": {"l": 60, "r": 30, "t": 70, "b": 60},
}


# Aplica os títulos e o layout padrão na figura
def aplicar_layout_padrao(figura, titulo, titulo_x, titulo_y, titulo_legenda=None):
    figura.update_layout(
        title=titulo, xaxis_title=titulo_x, yaxis_title=titulo_y,
        legend_title=titulo_legenda, **LAYOUT_PADRAO,
    )
    
    # Remove as linhas de grade verticais do eixo X
    figura.update_xaxes(showgrid=False)
    
    # Personaliza as cores das linhas de grade horizontais e do eixo zero no eixo Y
    figura.update_yaxes(gridcolor="#334B2D", zerolinecolor="#5C6B3C")
    
    return figura


# Cria um gráfico de linha com marcadores coloridos para focos de calor
def grafico_serie_temporal(agregado_mensal, coluna_focos, rotulo_focos):
    figura = go.Figure()
    
    # Adiciona a linha contínua base conectando os pontos temporais
    figura.add_trace(go.Scatter(
        x=agregado_mensal["data"], y=agregado_mensal[coluna_focos], mode="lines",
        line={"color": COR_LINHA_GUIA, "width": 2}, showlegend=False, hoverinfo="skip",
    ))
    
    # Sobrepõe os marcadores coloridos de acordo com a fase do ENSO
    for fase in ORDEM_FASES_ENSO:
        pontos = agregado_mensal[agregado_mensal["fase_enso"] == fase]
        figura.add_trace(go.Scatter(
            x=pontos["data"], y=pontos[coluna_focos], mode="markers", name=fase,
            marker={"color": CORES_FASES_ENSO[fase], "size": 9,
                    "line": {"color": "#101811", "width": 2}},
            hovertemplate="%{x|%b/%Y}<br>" + rotulo_focos + ": %{y:,.1f}<extra>" + fase + "</extra>",
        ))
        
    return aplicar_layout_padrao(figura, "Focos de calor por mês e fase do ENSO", "Mês", rotulo_focos, "Fase do ENSO")


# Cria um boxplot para mostrar a dispersão de focos por mês
def grafico_distribuicao_por_mes(agregado_mensal, coluna_focos, rotulo_focos):
    figura = px.box(
        agregado_mensal, x="nome_mes", y=coluna_focos, points="all", hover_data=["ano"],
        category_orders={"nome_mes": ORDEM_NOMES_MESES},
    )
    
    # Personaliza as cores das bolinhas e do contorno da caixa
    figura.update_traces(marker={"color": "#9A8B5F", "size": 7}, line={"color": "#5C6B3C"})
    
    return aplicar_layout_padrao(
        figura, "Distribuição dos focos por mês do ano", "Mês do ano", rotulo_focos
    )


# Cria um boxplot agrupando os focos pela fase climática do ENSO
def grafico_distribuicao_por_fase(agregado_mensal, coluna_focos, rotulo_focos):
    figura = px.box(
        agregado_mensal, x="fase_enso", y=coluna_focos, color="fase_enso", points="all",
        hover_data=["ano", "nome_mes"], category_orders={"fase_enso": ORDEM_FASES_ENSO},
        color_discrete_map=CORES_FASES_ENSO,
    )
    
    # Ajusta o tamanho dos pontos do gráfico
    figura.update_traces(marker={"size": 7})

    # Define o titulo para X e Y
    aplicar_layout_padrao(
        figura, "Distribuição dos focos mensais por fase do ENSO", "Fase do ENSO", rotulo_focos
    )
    
    figura.update_layout(showlegend=False)
    
    return figura


# Cria um gráfico de dispersão correlacionando variáveis climáticas com focos
def grafico_relacao_clima_focos(tabela, coluna_clima, rotulo_clima, coluna_focos, rotulo_focos):
    figura = px.scatter(
        tabela, x=coluna_clima, y=coluna_focos, color="fase_enso", hover_data=["ano", "nome_mes"],
        category_orders={"fase_enso": ORDEM_FASES_ENSO}, color_discrete_map=CORES_FASES_ENSO,
    )
    
    # Ajusta o tamanho e adiciona borda aos pontos
    figura.update_traces(marker={"size": 10, "line": {"color": "#101811", "width": 2}})
    
    return aplicar_layout_padrao(
        figura, f"{rotulo_clima} e focos de calor por mês", rotulo_clima, rotulo_focos, "Fase do ENSO"
    )


# Cria um mapa coroplético usando um arquivo GeoJSON de municípios
def grafico_mapa_municipios(agregado_municipios, malha, coluna_focos, rotulo_focos):
    figura = px.choropleth(
        agregado_municipios, geojson=malha, locations="codigo_ibge_texto",
        featureidkey="properties.codarea", color=coluna_focos,
        color_continuous_scale=ESCALA_SEQUENCIAL_ANOS, hover_name="nome_municipio",
        hover_data={"codigo_ibge_texto": False, "quantidade_focos": ":,", coluna_focos: ":.1f"},
        labels={coluna_focos: rotulo_focos, "quantidade_focos": "Focos"},
    )
    
    # Centraliza o mapa nas áreas com dados e oculta o restante do globo
    figura.update_geos(fitbounds="locations", visible=False, bgcolor="#101811")
    
    # Ajusta a espessura e a cor das linhas divisórias dos municípios
    figura.update_traces(marker_line={"color": "#1A2B1E", "width": 0.6})
    
    # Adiciona o título e repassa o layout padrão
    figura.update_layout(
        title="Focos de calor por município no recorte selecionado",
        height=620, **LAYOUT_PADRAO,
    )
    
    # Zera as margens laterais e inferiores para o mapa ocupar mais espaço
    figura.update_layout(margin={"l": 0, "r": 0, "t": 60, "b": 0})
    
    return figura


# Cria um gráfico de dispersão da área desmatada versus focos de calor
def grafico_relacao_desmatamento_focos(base_anual_filtrada, usar_escala_logaritmica):
    tabela = base_anual_filtrada.dropna(subset=["desmatamento_pct_area"])
    
    # Remove os valores nulos ou zerados caso a escala logarítmica esteja ativada
    if usar_escala_logaritmica:
        tabela = tabela[(tabela["desmatamento_pct_area"] > 0) & (tabela["focos_por_1000_km2"] > 0)]
        
    figura = px.scatter(
        tabela, x="desmatamento_pct_area", y="focos_por_1000_km2", color="ano_prodes",
        hover_name="nome_municipio", log_x=usar_escala_logaritmica, log_y=usar_escala_logaritmica,
        color_continuous_scale=ESCALA_SEQUENCIAL_ANOS,
        labels={"ano_prodes": "Ciclo PRODES"},
    )
    
    # Ajusta o tamanho dos pontos
    figura.update_traces(marker={"size": 9, "line": {"color": "#101811", "width": 1}})
    
    return aplicar_layout_padrao(
        figura, "Desmatamento e focos de calor por município e ciclo PRODES",
        "Desmatamento no ciclo (% da área do município)", "Focos por 1000 km²",
    )


# Cria gráficos de barra duplos compartilhando o mesmo eixo X para ciclos PRODES
def grafico_evolucao_por_ciclo(agregado_ciclos):
    figura = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
        subplot_titles=("Desmatamento (km²)", "Focos de calor"),
    )
    
    # Gráfico superior de barras para o desmatamento
    figura.add_trace(go.Bar(
        x=agregado_ciclos["ano_prodes"], y=agregado_ciclos["desmatamento_km2"],
        marker_color=COR_DESMATAMENTO, marker_line={"color": "#101811", "width": 1},
        hovertemplate="Ciclo %{x}<br>%{y:,.0f} km²<extra></extra>",
    ), row=1, col=1)
    
    # Gráfico inferior de barras para os focos de calor
    figura.add_trace(go.Bar(
        x=agregado_ciclos["ano_prodes"], y=agregado_ciclos["quantidade_focos"],
        marker_color=COR_FOCOS, marker_line={"color": "#101811", "width": 1},
        hovertemplate="Ciclo %{x}<br>%{y:,.0f} focos<extra></extra>",
    ), row=2, col=1)
    
    # Configurações globais exclusivas do layout dos subplots
    figura.update_layout(
        title="Desmatamento e focos de calor por ciclo PRODES (agosto a julho)",
        showlegend=False, height=600, template="plotly_dark",
        paper_bgcolor="#101811", plot_bgcolor="#101811", font={"color": "#F5F3EC"},
        margin={"l": 60, "r": 30, "t": 90, "b": 60}, bargap=0.25,
    )
    
    # Configura o eixo X para pular de 1 em 1 ano e limpa as linhas de grade
    figura.update_xaxes(showgrid=False, dtick=1, title_text="Ciclo PRODES", row=2, col=1)
    
    # Personaliza as linhas de grade horizontais do eixo Y
    figura.update_yaxes(gridcolor="#334B2D", zerolinecolor="#5C6B3C")
    
    return figura