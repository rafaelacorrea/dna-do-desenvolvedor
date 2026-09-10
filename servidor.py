#!/usr/bin/env python3
"""Sobe a cena e a API do DNA do Desenvolvedor no mesmo endereco.

Uso:
    python servidor.py
    python servidor.py --porta 9000 --token ghp_seu_token

Com o servidor no ar, digitar um usuario na tela passa a coletar de verdade:
a pagina chama a API, que busca no GitHub, calcula os tracos e guarda o
resultado na pasta de dados.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dna.api import PASTA_WEB, ServicoDeDna, criar_servidor
from dna.github import ClienteGitHub

VARIAVEL_DE_TOKEN = "GITHUB_TOKEN"


def main() -> int:
    """Le os argumentos e mantem o servidor no ar ate um Ctrl+C."""
    analisador = argparse.ArgumentParser(
        prog="servidor",
        description="Serve a cena 3D e a API que calcula o DNA de um usuario.",
    )
    analisador.add_argument(
        "--porta", type=int, default=8000, help="porta de escuta (padrao: 8000)"
    )
    analisador.add_argument(
        "--endereco",
        default="127.0.0.1",
        help="endereco de escuta; use 0.0.0.0 para aceitar a rede local",
    )
    analisador.add_argument(
        "--pasta-web",
        default=str(PASTA_WEB),
        help=f"pasta da cena (padrao: {PASTA_WEB})",
    )
    analisador.add_argument(
        "--token",
        help=(
            "token do GitHub para aumentar o limite de requisicoes; "
            f"por padrao usa a variavel de ambiente {VARIAVEL_DE_TOKEN}"
        ),
    )
    argumentos = analisador.parse_args()

    pasta = Path(argumentos.pasta_web)
    if not pasta.is_dir():
        print(f"Erro: pasta '{pasta}' nao encontrada", file=sys.stderr)
        return 1

    token = argumentos.token or os.environ.get(VARIAVEL_DE_TOKEN)
    servico = ServicoDeDna(pasta / "dados", ClienteGitHub(token=token))
    servidor = criar_servidor(argumentos.porta, argumentos.endereco, pasta, servico)

    endereco = f"http://{argumentos.endereco}:{argumentos.porta}"
    print(f"Cena em {endereco}")
    print(f"API  em {endereco}/api/dna/<usuario>")
    print("Sem token: cerca de 60 requisicoes por hora na API do GitHub.")
    print("Ctrl+C para encerrar.")

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando.")
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
