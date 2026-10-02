# Projeto-de-Estatistica

1. Focos de calor — INPE/BDQueimadas

Anuais (2015–2025): https://terrabrasilis.dpi.inpe.br/queimadas/bdqueimadas/#exportar-dados (troquem o ano no fim)
Mensais (2026): https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/mensal/Brasil/focos_mensal_br_202601.csv (troquem 01 pelo mês)
Portal com filtros: https://terrabrasilis.dpi.inpe.br/queimadas/bdqueimadas/
São do Brasil inteiro e todos os satélites. Filtrem estado == "PARÁ" e satelite == "AQUA_M-T".

2. Clima — NASA POWER

Interface: https://power.larc.nasa.gov/data-access-viewer/
API: https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,T2M_MAX,PRECTOTCORR,RH2M&community=AG&latitude=-1.45&longitude=-48.5&start=20140101&end=20260831&format=CSV
A interface limita a 366 dias por download, a API não.

3. El Niño — NOAA/CPC

https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt

4. Desmatamento — PRODES

Shapefile de incremento anual: https://terrabrasilis.dpi.inpe.br/downloads/ (aquele que vocês acharam)
Totais por estado, pra conferência: https://terrabrasilis.dpi.inpe.br/app/dashboard/deforestation/biomes/legal_amazon/increments

5. Municípios do Pará — IBGE

Lista: https://servicodados.ibge.gov.br/api/v1/localidades/estados/15/municipios
Centroide e área de cada um: https://servicodados.ibge.gov.br/api/v3/malhas/municipios/{codigo}/metadados
Mapa: https://servicodados.ibge.gov.br/api/v3/malhas/estados/15?formato=application/vnd.geo+json&intrarregiao=municipio
