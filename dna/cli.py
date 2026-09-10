"""Camada de linha de comando do DNA do Desenvolvedor.

Busca os dados publicos do usuario, calcula os tracos e grava o JSON que a
cena 3D consome. Tambem imprime um resumo em texto, util para conferir o
resultado sem abrir o navegador.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from dna import tracos
from dna.github import ClienteGitHub, ErroDeApi

PROGRAMA = "dna"

DESCRICAO = (
    "Transforma um perfil publico do GitHub em um DNA visual: calcula os seis "
    "tracos e grava o JSON usado pela cena 3D."
)

EXEMPLOS = """\
Exemplos de uso:
  python dna_cli.py rafaelacorrea
  python dna_cli.py rafaelacorrea --saida web/dados/rafaelacorrea.json
  python dna_cli.py rafaelacorrea --so-texto
"""

VARIAVEL_DE_TOKEN = "GITHUB_TOKEN"
PASTA_PADRAO = Path("web") / "dados"
ARQUIVO_DE_INDICE = "index.json"
LARGURA_DA_BARRA = 24


def construir_analisador() -> argparse.ArgumentParser:
    """Monta o analisador de argumentos da aplicacao."""
    analisador = argparse.ArgumentParser(
        prog=PROGRAMA,
        description=DESCRICAO,
        epilog=EXEMPLOS,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    analisador.add_argument("usuario", help="nome de usuario no GitHub")
    analisador.add_argument(
        "--saida",
        metavar="CAMINHO",
        help=f"arquivo JSON de destino (padrao: {PASTA_PADRAO}/<usuario>.json)",
    )
    analisador.add_argument(
        "--so-texto",
        action="store_true",
        help="apenas mostra o resultado no terminal, sem gravar arquivo",
    )
    analisador.add_argument(
        "--token",
        metavar="TOKEN",
        help=(
            "token do GitHub para aumentar o limite de requisicoes; "
            f"por padrao usa a variavel de ambiente {VARIAVEL_DE_TOKEN}"
        ),
    )
    return analisador


def barra(percentual: float, largura: int = LARGURA_DA_BARRA) -> str:
    """Desenha uma barra de progresso em texto puro."""
    cheios = int(round(largura * max(0.0, min(100.0, percentual)) / 100))
    return "[" + "#" * cheios + "." * (largura - cheios) + "]"


def formatar(dna: Dict[str, Any]) -> str:
    """Monta o resumo em texto exibido no terminal."""
    linhas = [f"DNA do desenvolvedor: {dna['usuario']}", ""]

    rotulos = dna["rotulos"]
    largura = max(len(rotulo) for rotulo in rotulos.values())
    for nome in tracos.NOMES_DOS_TRACOS:
        valor = dna["tracos"][nome]
        linhas.append(f"  {rotulos[nome]:<{largura}}  {barra(valor)} {valor:>3}%")

    idiomas = dna.get("linguagens") or []
    if idiomas:
        resumo = ", ".join(f"{item['nome']} {item['percentual']}%" for item in idiomas)
        linhas.extend(["", f"Linguagens: {resumo}"])

    estatisticas = dna["estatisticas"]
    linhas.extend(
        [
            "",
            "Base de calculo: "
            f"{estatisticas['repositorios_proprios']} repositorios proprios, "
            f"{estatisticas['forks']} forks, "
            f"{estatisticas['estrelas_recebidas']} estrelas, "
            f"{estatisticas['eventos_analisados']} eventos recentes em "
            f"{estatisticas['dias_ativos']} dias distintos.",
            f"Semente da estrutura: {dna['semente']}",
        ]
    )
    return "\n".join(linhas)


def gravar(dna: Dict[str, Any], caminho: Path) -> Path:
    """Grava o JSON do DNA, criando as pastas necessarias."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(dna, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return caminho


def montar_indice(pasta: Path) -> List[Dict[str, Any]]:
    """Le a pasta de dados e monta a lista dos DNAs ja gerados.

    O indice e reconstruido do zero a cada execucao, varrendo os arquivos que
    estao la. Assim ele se corrige sozinho quando um JSON e apagado na mao, e
    nenhum estado precisa ser guardado em outro lugar.

    Cada entrada leva so o necessario para a cena montar a versao reduzida da
    helice no plano de fundo: os tracos, a semente e a cor dominante.
    """
    entradas: List[Dict[str, Any]] = []

    for caminho in sorted(pasta.glob("*.json")):
        if caminho.name == ARQUIVO_DE_INDICE:
            continue
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(dados, dict) or "tracos" not in dados:
            continue

        idiomas = dados.get("linguagens") or []
        entradas.append(
            {
                "usuario": dados.get("usuario") or caminho.stem,
                "nome": dados.get("nome") or dados.get("usuario") or caminho.stem,
                "semente": dados.get("semente", 1),
                "tracos": dados["tracos"],
                "cor": idiomas[0]["cor"] if idiomas else "#8b949e",
                "gerado_em": dados.get("gerado_em"),
            }
        )

    entradas.sort(key=lambda entrada: entrada["gerado_em"] or "", reverse=True)
    return entradas


def gravar_indice(pasta: Path) -> Path:
    """Regrava o indice da pasta de dados e devolve o caminho do arquivo."""
    caminho = pasta / ARQUIVO_DE_INDICE
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(montar_indice(pasta), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return caminho


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Ponto de entrada da aplicacao. Devolve o codigo de saida do processo."""
    analisador = construir_analisador()
    argumentos = analisador.parse_args(argv)

    cliente = ClienteGitHub(token=argumentos.token or os.environ.get(VARIAVEL_DE_TOKEN))
    usuario = argumentos.usuario.strip()

    try:
        perfil = cliente.buscar_perfil(usuario)
        repositorios = cliente.buscar_repositorios(usuario)
        eventos = cliente.buscar_eventos(usuario)
    except ErroDeApi as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1

    dna = tracos.calcular(usuario, perfil, repositorios, eventos)
    print(formatar(dna))

    if argumentos.so_texto:
        return 0

    destino = Path(argumentos.saida) if argumentos.saida else PASTA_PADRAO / f"{usuario}.json"
    try:
        gravar(dna, destino)
    except OSError as erro:
        print(f"Erro: nao foi possivel gravar '{destino}': {erro}", file=sys.stderr)
        return 1

    try:
        indice = gravar_indice(destino.parent)
    except OSError as erro:
        print(f"Erro: nao foi possivel gravar o indice: {erro}", file=sys.stderr)
        return 1

    total = len(montar_indice(destino.parent))
    colecao = "1 perfil" if total == 1 else f"{total} perfis"
    print(f"\nArquivo gravado em {destino}")
    print(f"Indice atualizado em {indice} ({colecao} na colecao)")
    print("Abra a cena com: python -m http.server --directory web 8000")
    print(f"e acesse: http://localhost:8000/?usuario={usuario}")
    return 0
