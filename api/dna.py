"""Funcao sem estado que entrega o DNA de um usuario.

E a mesma logica do `servidor.py`, embrulhada no formato que a hospedagem
espera: um `handler` de `BaseHTTPRequestHandler` por arquivo. Quem faz o
trabalho continua sendo o `dna.api.responder`, entao nao existe uma segunda
versao das regras aqui.

Duas diferencas em relacao ao servidor local:

- **Nao grava nada.** O disco da funcao e somente leitura, entao o resultado
  fica so no cache em memoria, que sobrevive enquanto a instancia estiver
  quente. Os perfis versionados em `public/dados` continuam sendo lidos.
- **O token vem do ambiente.** `GITHUB_TOKEN` configurado na hospedagem leva o
  limite de 60 para 5000 requisicoes por hora, sem nunca aparecer na pagina.
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# A funcao roda a partir da pasta `api`, entao a raiz do projeto precisa
# entrar no caminho de importacao para que o pacote `dna` seja encontrado.
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from dna.api import ServicoDeDna, responder  # noqa: E402
from dna.github import ClienteGitHub  # noqa: E402

# Criado no escopo do modulo de proposito: instancias reaproveitadas entre
# requisicoes mantem o cache em memoria, o que evita repetir coleta.
SERVICO = ServicoDeDna(
    RAIZ / "public" / "dados",
    ClienteGitHub(token=os.environ.get("GITHUB_TOKEN")),
    gravar_resultado=False,
)

VERDADEIROS = {"1", "true", "sim"}


def _caminho_do_indice() -> Path:
    """Arquivo do indice versionado no repositorio."""
    return RAIZ / "public" / "dados" / "index.json"


def resolver(caminho: str, consulta: dict) -> tuple:
    """Escolhe a resposta a partir do caminho pedido.

    A funcao e o unico ponto de entrada Python da hospedagem, entao ela
    precisa dar conta de tudo que for roteado para ela - inclusive de um
    caminho que nao existe, que vira 404 em JSON em vez de erro cru.
    """
    if caminho.rstrip("/").endswith("/api/indice"):
        try:
            indice = json.loads(_caminho_do_indice().read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            # Devolver lista vazia seria mentir: a cena acharia que a colecao
            # esta vazia e nao desenharia a galeria. Com 404 ela cai no
            # arquivo estatico, que a hospedagem serve de qualquer forma.
            return 404, {"erro": "indice indisponivel"}, ""
        return 200, indice, ""

    if "/api/dna" in caminho:
        usuario = (consulta.get("usuario") or [""])[0]
        if not usuario:
            # Sem rewrite, o nome ainda pode vir no proprio caminho.
            final = caminho.rstrip("/").rsplit("/", 1)[-1]
            usuario = "" if final in ("dna", "api") else final
        forcar = (consulta.get("forcar") or [""])[0].lower() in VERDADEIROS
        return responder(SERVICO, usuario, forcar)

    return 404, {"erro": "rota desconhecida"}, ""


class handler(BaseHTTPRequestHandler):  # noqa: N801 (nome exigido pela hospedagem)
    """Responde `GET /api/dna?usuario=<nome>` e `GET /api/indice`."""

    def do_GET(self) -> None:  # noqa: N802 (nome exigido pela classe base)
        endereco = urlparse(self.path)
        situacao, corpo, origem = resolver(endereco.path, parse_qs(endereco.query))
        bruto = json.dumps(corpo, ensure_ascii=False).encode("utf-8")

        self.send_response(int(situacao))
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(bruto)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Dna-Api", "1")
        if origem:
            self.send_header("X-Dna-Origem", origem)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(bruto)
