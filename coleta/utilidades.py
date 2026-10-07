import time
import unicodedata

import requests


def normalizar_nome(texto):
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    return " ".join(sem_acento.upper().replace("-", " ").replace("'", " ").split())


def requisitar_com_tentativas(url, parametros=None, tentativas=4, espera_segundos=5, **opcoes):
    ultimo_erro = None
    for numero_tentativa in range(1, tentativas + 1):
        try:
            resposta = requests.get(url, params=parametros, timeout=opcoes.pop("timeout", 180), **opcoes)
            resposta.raise_for_status()
            return resposta
        except requests.RequestException as erro:
            ultimo_erro = erro
            if numero_tentativa < tentativas:
                time.sleep(espera_segundos * numero_tentativa)
    raise ultimo_erro
