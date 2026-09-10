"""Servidor HTTP que entrega o DNA calculado em Python.

A cena deixa de depender de arquivos gerados a mao: quando alguem digita um
usuario, a pagina chama esta API, que coleta na API do GitHub, calcula os
tracos com o mesmo `dna.tracos` usado pela linha de comando, grava o JSON na
pasta de dados e devolve o resultado. O algoritmo continua existindo em um
lugar so.

Rotas:

    GET /api/dna/<usuario>          o DNA do usuario (usa o arquivo se ja existir)
    GET /api/dna/<usuario>?forcar=1 ignora o arquivo e coleta de novo
    GET /api/indice                 a lista dos DNAs ja gerados

Qualquer outro caminho cai no servidor de arquivos estaticos, entao o mesmo
processo serve a cena e a API. Tudo vem da biblioteca padrao: `http.server`.
"""

from __future__ import annotations

import json
import re
import threading
from collections import OrderedDict
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import unquote, urlparse

from dna import tracos
from dna.cli import caminho_do_usuario, gravar, gravar_indice, montar_indice
from dna.github import ClienteGitHub, ErroDeApi, LimiteExcedido, UsuarioNaoEncontrado

# Regra de nome de usuario do proprio GitHub. Alem de recusar entrada
# invalida cedo, isso impede que um nome com barras ou pontos escape da pasta
# de dados na hora de montar o caminho do arquivo.
NOME_VALIDO = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")

# A pasta se chama `public` por convencao da hospedagem: e o nome que ela
# serve na raiz do dominio sem precisar de configuracao.
PASTA_WEB = Path("public")
PASTA_DADOS = PASTA_WEB / "dados"


class ServicoDeDna:
    """Junta coleta, calculo e gravacao em uma operacao so.

    Tres camadas antes de gastar uma chamada na API do GitHub: memoria,
    arquivo em disco e so entao a coleta. A memoria existe porque nem todo
    lugar deixa gravar - em uma funcao sem estado na nuvem o disco e somente
    leitura, e ali ela e o unico cache que sobra.

    Ha tambem um cadeado por usuario, para o caso de duas abas pedirem o mesmo
    perfil ao mesmo tempo: a segunda espera a primeira terminar e aproveita o
    resultado em vez de repetir a coleta.
    """

    def __init__(
        self,
        pasta: Path = PASTA_DADOS,
        cliente: Optional[ClienteGitHub] = None,
        gravar_resultado: bool = True,
        memoria_maxima: int = 64,
    ) -> None:
        self.pasta = Path(pasta)
        self.cliente = cliente or ClienteGitHub()
        self.gravar_resultado = gravar_resultado
        self.memoria_maxima = memoria_maxima
        self._memoria: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        self._cadeados: Dict[str, threading.Lock] = {}
        self._cadeado_geral = threading.Lock()

    def _cadeado_de(self, usuario: str) -> threading.Lock:
        with self._cadeado_geral:
            return self._cadeados.setdefault(usuario, threading.Lock())

    def _lembrar(self, usuario: str, dna: Dict[str, Any]) -> None:
        """Guarda o resultado em memoria, descartando o mais antigo."""
        chave = usuario.strip().lower()
        with self._cadeado_geral:
            self._memoria[chave] = dna
            self._memoria.move_to_end(chave)
            while len(self._memoria) > self.memoria_maxima:
                self._memoria.popitem(last=False)

    def ler_da_memoria(self, usuario: str) -> Optional[Dict[str, Any]]:
        """Devolve o DNA coletado nesta mesma execucao, se houver."""
        return self._memoria.get(usuario.strip().lower())

    def ler_do_disco(self, usuario: str) -> Optional[Dict[str, Any]]:
        """Devolve o DNA ja gravado, ou None se ainda nao existir."""
        caminho = caminho_do_usuario(self.pasta, usuario)
        if not caminho.exists():
            return None
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return dados if isinstance(dados, dict) else None

    def _guardado(self, usuario: str) -> Optional[Tuple[Dict[str, Any], str]]:
        """Procura o perfil na memoria e depois no disco."""
        lembrado = self.ler_da_memoria(usuario)
        if lembrado is not None:
            return lembrado, "memoria"
        gravado = self.ler_do_disco(usuario)
        if gravado is not None:
            return gravado, "arquivo"
        return None

    def obter(self, usuario: str, forcar: bool = False) -> Tuple[Dict[str, Any], str]:
        """Devolve `(dna, origem)`: 'memoria', 'arquivo' ou 'github'."""
        nome = usuario.strip()

        if not forcar:
            achado = self._guardado(nome)
            if achado is not None:
                return achado

        with self._cadeado_de(nome.lower()):
            # Outra requisicao pode ter resolvido enquanto esta esperava.
            if not forcar:
                achado = self._guardado(nome)
                if achado is not None:
                    return achado

            perfil = self.cliente.buscar_perfil(nome)
            repositorios = self.cliente.buscar_repositorios(nome)
            eventos = self.cliente.buscar_eventos(nome)

            # O login devolvido pela API tem a grafia correta, entao um
            # "TorValds" digitado na tela vira "torvalds" no arquivo.
            login = perfil.get("login") or nome
            dna = tracos.calcular(login, perfil, repositorios, eventos)

            self._lembrar(login, dna)
            if self.gravar_resultado:
                gravar(dna, caminho_do_usuario(self.pasta, login))
                gravar_indice(self.pasta)
            return dna, "github"

    def indice(self) -> Any:
        """Devolve a lista dos DNAs ja gerados."""
        return montar_indice(self.pasta)


def responder(
    servico: ServicoDeDna, usuario: str, forcar: bool = False
) -> Tuple[int, Dict[str, Any], str]:
    """Resolve um pedido de DNA sem depender de HTTP.

    Devolve `(codigo, corpo, origem)`. Fica fora do manipulador porque o mesmo
    comportamento serve o servidor local e a funcao hospedada na nuvem, que
    recebem a requisicao em formatos diferentes.
    """
    nome = (usuario or "").strip()
    if not NOME_VALIDO.match(nome):
        return (
            HTTPStatus.BAD_REQUEST,
            {"erro": f"'{nome}' nao e um nome de usuario valido do GitHub"},
            "",
        )

    try:
        dna, origem = servico.obter(nome, forcar)
    except UsuarioNaoEncontrado as erro:
        return HTTPStatus.NOT_FOUND, {"erro": str(erro)}, ""
    except LimiteExcedido as erro:
        return HTTPStatus.TOO_MANY_REQUESTS, {"erro": str(erro)}, ""
    except ErroDeApi as erro:
        return HTTPStatus.BAD_GATEWAY, {"erro": str(erro)}, ""
    except OSError as erro:
        return (
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {"erro": f"nao foi possivel gravar o resultado: {erro}"},
            "",
        )
    return HTTPStatus.OK, dna, origem


def criar_manipulador(servico: ServicoDeDna, pasta_web: Path):
    """Monta a classe de manipulador ligada a um servico e a uma pasta."""

    class Manipulador(SimpleHTTPRequestHandler):
        """Serve a cena e responde as rotas da API."""

        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, directory=str(pasta_web), **kwargs)

        def log_message(self, formato: str, *args: Any) -> None:
            """Mantem o terminal limpo: so erros aparecem."""
            if args and str(args[0]).startswith(("4", "5")):
                super().log_message(formato, *args)

        def do_GET(self) -> None:  # noqa: N802 (nome exigido pela classe base)
            caminho = urlparse(self.path).path
            if caminho.startswith("/api/"):
                self.responder_api(caminho)
                return
            super().do_GET()

        def responder_api(self, caminho: str) -> None:
            """Direciona a requisicao para a rota certa da API."""
            consulta = urlparse(self.path).query

            if caminho == "/api/indice":
                self.enviar_json(HTTPStatus.OK, servico.indice())
                return

            if caminho.startswith("/api/dna/"):
                usuario = unquote(caminho[len("/api/dna/") :]).strip()
                self.responder_dna(usuario, "forcar=1" in consulta)
                return

            self.enviar_json(HTTPStatus.NOT_FOUND, {"erro": "rota desconhecida"})

        def responder_dna(self, usuario: str, forcar: bool) -> None:
            """Coleta (ou recupera) o DNA de um usuario."""
            situacao, corpo, origem = responder(servico, usuario, forcar)
            self.enviar_json(situacao, corpo, origem=origem)

        def enviar_json(self, situacao: HTTPStatus, dados: Any, origem: str = "") -> None:
            """Escreve uma resposta JSON com os cabecalhos necessarios."""
            corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")

            self.send_response(situacao)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            # Marca as respostas da API para que a cena saiba diferenciar
            # "usuario nao existe" de "nao ha API neste endereco".
            self.send_header("X-Dna-Api", "1")
            if origem:
                self.send_header("X-Dna-Origem", origem)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(corpo)

    return Manipulador


def criar_servidor(
    porta: int = 8000,
    endereco: str = "127.0.0.1",
    pasta_web: Path = PASTA_WEB,
    servico: Optional[ServicoDeDna] = None,
) -> ThreadingHTTPServer:
    """Monta o servidor sem iniciar o laco de atendimento.

    Deixar a criacao separada do `serve_forever` e o que permite subir o
    servidor dentro dos testes em uma porta qualquer.
    """
    pasta = Path(pasta_web)
    usado = servico or ServicoDeDna(pasta / "dados")
    return ThreadingHTTPServer((endereco, porta), criar_manipulador(usado, pasta))
