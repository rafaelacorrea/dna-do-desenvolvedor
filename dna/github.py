"""Acesso a API publica do GitHub.

Este modulo e uma evolucao direta do cliente escrito no projeto
`github-user-activity`: alem dos eventos publicos, ele tambem busca a lista de
repositorios, necessaria para descobrir as linguagens e o alcance do trabalho
do usuario.

Continua usando apenas `urllib`, da biblioteca padrao, e traduz as falhas de
rede e os codigos HTTP em excecoes com mensagens em portugues.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

URL_BASE = "https://api.github.com"
TEMPO_LIMITE = 20
POR_PAGINA_MAXIMO = 100

CABECALHOS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "dna-do-desenvolvedor",
    "X-GitHub-Api-Version": "2022-11-28",
}


class ErroDeApi(Exception):
    """Falha ao consultar a API do GitHub."""


class UsuarioNaoEncontrado(ErroDeApi):
    """O usuario informado nao existe no GitHub."""


class LimiteExcedido(ErroDeApi):
    """O limite de requisicoes da API foi atingido."""


class ClienteGitHub:
    """Busca perfil, repositorios e eventos publicos de um usuario."""

    def __init__(
        self,
        url_base: str = URL_BASE,
        token: Optional[str] = None,
        tempo_limite: int = TEMPO_LIMITE,
    ) -> None:
        self.url_base = url_base.rstrip("/")
        self.token = token
        self.tempo_limite = tempo_limite

    def _cabecalhos(self) -> Dict[str, str]:
        cabecalhos = dict(CABECALHOS)
        if self.token:
            cabecalhos["Authorization"] = f"Bearer {self.token}"
        return cabecalhos

    def _pegar(self, caminho: str, usuario: str) -> Any:
        """Executa um GET na API e devolve o JSON ja convertido."""
        requisicao = urllib.request.Request(
            f"{self.url_base}{caminho}", headers=self._cabecalhos()
        )
        try:
            with urllib.request.urlopen(requisicao, timeout=self.tempo_limite) as resposta:
                return json.loads(resposta.read().decode("utf-8"))
        except urllib.error.HTTPError as erro:
            raise self._traduzir_http(erro, usuario) from erro
        except urllib.error.URLError as erro:
            raise ErroDeApi(
                f"nao foi possivel falar com a API do GitHub: {erro.reason}"
            ) from erro
        except TimeoutError as erro:
            raise ErroDeApi("a API do GitHub demorou demais para responder") from erro
        except json.JSONDecodeError as erro:
            raise ErroDeApi("a API do GitHub devolveu uma resposta invalida") from erro

    @staticmethod
    def _validar_usuario(usuario: str) -> str:
        nome = (usuario or "").strip()
        if not nome:
            raise ErroDeApi("informe o nome de usuario do GitHub")
        return nome

    def buscar_perfil(self, usuario: str) -> Dict[str, Any]:
        """Devolve os dados publicos do perfil do usuario."""
        nome = self._validar_usuario(usuario)
        dados = self._pegar(f"/users/{urllib.parse.quote(nome)}", nome)
        if not isinstance(dados, dict):
            raise ErroDeApi("a API do GitHub devolveu um perfil inesperado")
        return dados

    def buscar_repositorios(self, usuario: str, paginas: int = 3) -> List[Dict[str, Any]]:
        """Devolve os repositorios publicos, do mais recente para o mais antigo."""
        nome = self._validar_usuario(usuario)
        caminho = f"/users/{urllib.parse.quote(nome)}/repos"
        repositorios: List[Dict[str, Any]] = []
        for pagina in range(1, max(1, paginas) + 1):
            consulta = f"?per_page={POR_PAGINA_MAXIMO}&sort=pushed&page={pagina}"
            lote = self._pegar(caminho + consulta, nome)
            if not isinstance(lote, list):
                raise ErroDeApi("a API do GitHub devolveu uma lista inesperada")
            repositorios.extend(lote)
            if len(lote) < POR_PAGINA_MAXIMO:
                break
        return repositorios

    def buscar_eventos(self, usuario: str, limite: int = 100) -> List[Dict[str, Any]]:
        """Devolve os eventos publicos recentes do usuario."""
        nome = self._validar_usuario(usuario)
        quantidade = max(1, min(limite, POR_PAGINA_MAXIMO))
        caminho = f"/users/{urllib.parse.quote(nome)}/events?per_page={quantidade}"
        eventos = self._pegar(caminho, nome)
        if not isinstance(eventos, list):
            raise ErroDeApi("a API do GitHub devolveu uma lista inesperada")
        return eventos

    @staticmethod
    def _traduzir_http(erro: urllib.error.HTTPError, usuario: str) -> ErroDeApi:
        """Converte um codigo HTTP em uma excecao com mensagem em portugues."""
        if erro.code == 404:
            return UsuarioNaoEncontrado(f"usuario '{usuario}' nao encontrado no GitHub")
        if erro.code in (403, 429):
            restantes = erro.headers.get("X-RateLimit-Remaining") if erro.headers else None
            if restantes == "0":
                return LimiteExcedido(
                    "limite de requisicoes da API do GitHub atingido; tente de novo "
                    "mais tarde ou use um token (--token no CLI, ou a variavel de "
                    "ambiente GITHUB_TOKEN)"
                )
            return LimiteExcedido("acesso negado pela API do GitHub")
        if erro.code >= 500:
            return ErroDeApi(f"a API do GitHub esta indisponivel (codigo {erro.code})")
        return ErroDeApi(f"a API do GitHub respondeu com o codigo {erro.code}")
