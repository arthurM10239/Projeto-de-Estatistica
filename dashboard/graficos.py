import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from preparacao import NOMES_MESES, ORDEM_FASES_ENSO

CORES_FASES_ENSO = {"La Niña": "#4a98c9", "Neutro": "#6b6b6b", "El Niño": "#c84a02"}
COR_DESMATAMENTO = "#2b8a4a"
COR_FOCOS = "#c84a02"
COR_LINHA_GUIA = "#c9c9c9"
ESCALA_SEQUENCIAL_ANOS = ["#cfe3f2", "#9cc4e0", "#6aa5cd", "#3f7fae", "#245b85", "#12395b"]
ORDEM_NOMES_MESES = list(NOMES_MESES.values())

LAYOUT_PADRAO = {
    "template": "plotly_white",
    "hoverlabel": {"font_size": 13},
    "margin": {"l": 60, "r": 30, "t": 70, "b": 60},
}


def aplicar_layout_padrao(figura, titulo, titulo_x, titulo_y, titulo_legenda=None):
    figura.update_layout(
        title=titulo, xaxis_title=titulo_x, yaxis_title=titulo_y,
        legend_title=titulo_legenda, **LAYOUT_PADRAO,
    )
    figura.update_xaxes(showgrid=False)
    figura.update_yaxes(gridcolor="#ececec", zerolinecolor="#d8d8d8")
    return figura


def grafico_serie_temporal(agregado_mensal, coluna_focos, rotulo_focos):
    figura = go.Figure()
    figura.add_trace(go.Scatter(
        x=agregado_mensal["data"], y=agregado_mensal[coluna_focos], mode="lines",
        line={"color": COR_LINHA_GUIA, "width": 2}, showlegend=False, hoverinfo="skip",
    ))
    for fase in ORDEM_FASES_ENSO:
        pontos = agregado_mensal[agregado_mensal["fase_enso"] == fase]
        figura.add_trace(go.Scatter(
            x=pontos["data"], y=pontos[coluna_focos], mode="markers", name=fase,
            marker={"color": CORES_FASES_ENSO[fase], "size": 9,
                    "line": {"color": "#ffffff", "width": 2}},
            hovertemplate="%{x|%b/%Y}<br>" + rotulo_focos + ": %{y:,.1f}<extra>" + fase + "</extra>",
        ))
    return aplicar_layout_padrao(figura, "Focos de calor por mês e fase do ENSO", "Mês", rotulo_focos, "Fase do ENSO")


def grafico_distribuicao_por_mes(agregado_mensal, coluna_focos, rotulo_focos):
    figura = px.box(
        agregado_mensal, x="nome_mes", y=coluna_focos, points="all", hover_data=["ano"],
        category_orders={"nome_mes": ORDEM_NOMES_MESES},
    )
    figura.update_traces(marker={"color": "#3f7fae", "size": 7}, line={"color": "#245b85"})
    return aplicar_layout_padrao(
        figura, "Distribuição dos focos por mês do ano", "Mês do ano", rotulo_focos
    )


def grafico_distribuicao_por_fase(agregado_mensal, coluna_focos, rotulo_focos):
    figura = px.box(
        agregado_mensal, x="fase_enso", y=coluna_focos, color="fase_enso", points="all",
        hover_data=["ano", "nome_mes"], category_orders={"fase_enso": ORDEM_FASES_ENSO},
        color_discrete_map=CORES_FASES_ENSO,
    )
    figura.update_traces(marker={"size": 7})
    aplicar_layout_padrao(
        figura, "Distribuição dos focos mensais por fase do ENSO", "Fase do ENSO", rotulo_focos
    )
    figura.update_layout(showlegend=False)
    return figura


def grafico_relacao_clima_focos(tabela, coluna_clima, rotulo_clima, coluna_focos, rotulo_focos):
    figura = px.scatter(
        tabela, x=coluna_clima, y=coluna_focos, color="fase_enso", hover_data=["ano", "nome_mes"],
        category_orders={"fase_enso": ORDEM_FASES_ENSO}, color_discrete_map=CORES_FASES_ENSO,
    )
    figura.update_traces(marker={"size": 10, "line": {"color": "#ffffff", "width": 2}})
    return aplicar_layout_padrao(
        figura, f"{rotulo_clima} e focos de calor por mês", rotulo_clima, rotulo_focos, "Fase do ENSO"
    )


def grafico_mapa_municipios(agregado_municipios, malha, coluna_focos, rotulo_focos):
    figura = px.choropleth(
        agregado_municipios, geojson=malha, locations="codigo_ibge_texto",
        featureidkey="properties.codarea", color=coluna_focos,
        color_continuous_scale=ESCALA_SEQUENCIAL_ANOS, hover_name="nome_municipio",
        hover_data={"codigo_ibge_texto": False, "quantidade_focos": ":,", coluna_focos: ":.1f"},
        labels={coluna_focos: rotulo_focos, "quantidade_focos": "Focos"},
    )
    figura.update_geos(fitbounds="locations", visible=False)
    figura.update_traces(marker_line={"color": "#ffffff", "width": 0.6})
    figura.update_layout(
        title="Focos de calor por município no recorte selecionado",
        height=620, margin={"l": 0, "r": 0, "t": 60, "b": 0}, template="plotly_white",
    )
    return figura


def grafico_relacao_desmatamento_focos(base_anual_filtrada, usar_escala_logaritmica):
    tabela = base_anual_filtrada.dropna(subset=["desmatamento_pct_area"])
    if usar_escala_logaritmica:
        tabela = tabela[(tabela["desmatamento_pct_area"] > 0) & (tabela["focos_por_1000_km2"] > 0)]
    figura = px.scatter(
        tabela, x="desmatamento_pct_area", y="focos_por_1000_km2", color="ano_prodes",
        hover_name="nome_municipio", log_x=usar_escala_logaritmica, log_y=usar_escala_logaritmica,
        color_continuous_scale=ESCALA_SEQUENCIAL_ANOS,
        labels={"ano_prodes": "Ciclo PRODES"},
    )
    figura.update_traces(marker={"size": 9, "line": {"color": "#ffffff", "width": 1}})
    return aplicar_layout_padrao(
        figura, "Desmatamento e focos de calor por município e ciclo PRODES",
        "Desmatamento no ciclo (% da área do município)", "Focos por 1000 km²",
    )


def grafico_evolucao_por_ciclo(agregado_ciclos):
    figura = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
        subplot_titles=("Desmatamento (km²)", "Focos de calor"),
    )
    figura.add_trace(go.Bar(
        x=agregado_ciclos["ano_prodes"], y=agregado_ciclos["desmatamento_km2"],
        marker_color=COR_DESMATAMENTO, marker_line={"color": "#ffffff", "width": 1},
        hovertemplate="Ciclo %{x}<br>%{y:,.0f} km²<extra></extra>",
    ), row=1, col=1)
    figura.add_trace(go.Bar(
        x=agregado_ciclos["ano_prodes"], y=agregado_ciclos["quantidade_focos"],
        marker_color=COR_FOCOS, marker_line={"color": "#ffffff", "width": 1},
        hovertemplate="Ciclo %{x}<br>%{y:,.0f} focos<extra></extra>",
    ), row=2, col=1)
    figura.update_layout(
        title="Desmatamento e focos de calor por ciclo PRODES (agosto a julho)",
        showlegend=False, height=600, template="plotly_white",
        margin={"l": 60, "r": 30, "t": 90, "b": 60}, bargap=0.25,
    )
    figura.update_xaxes(showgrid=False, dtick=1, title_text="Ciclo PRODES", row=2, col=1)
    figura.update_yaxes(gridcolor="#ececec")
    return figura
