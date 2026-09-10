"""Funcao sem estado que entrega o DNA de um usuario.

E a mesma logica do `servidor.py`, embrulhada no formato que a hospedagem
espera: um `handler` de `BaseHTTPRequestHandler` por arquivo. Quem faz o
trabalho continua sendo o `dna.api.responder`, entao nao existe uma segunda
versao das regras aqui.

Duas diferencas em relacao ao servidor local:

- **Nao grava nada.** O disco da funcao e somente leitura, entao o resultado
  fica so no cache em memoria, que sobrevive enquanto a instancia estiver
  quente. Os perfis versionados em `web/dados` continuam sendo lidos.
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
    RAIZ / "web" / "dados",
    ClienteGitHub(token=os.environ.get("GITHUB_TOKEN")),
    gravar_resultado=False,
)

VERDADEIROS = {"1", "true", "sim"}


class handler(BaseHTTPRequestHandler):  # noqa: N801 (nome exigido pela hospedagem)
    """Responde `GET /api/dna?usuario=<nome>`."""

    def do_GET(self) -> None:  # noqa: N802 (nome exigido pela classe base)
        consulta = parse_qs(urlparse(self.path).query)
        usuario = (consulta.get("usuario") or [""])[0]
        forcar = (consulta.get("forcar") or [""])[0].lower() in VERDADEIROS

        situacao, corpo, origem = responder(SERVICO, usuario, forcar)
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
