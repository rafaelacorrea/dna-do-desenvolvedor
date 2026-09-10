"""Testes do cliente da API, com as respostas HTTP simuladas."""

import io
import json
import unittest
import urllib.error
from unittest.mock import patch

from dna.github import (
    ClienteGitHub,
    ErroDeApi,
    LimiteExcedido,
    UsuarioNaoEncontrado,
)


class RespostaFalsa(io.BytesIO):
    """Imita o objeto devolvido por `urlopen` dentro de um `with`."""

    def __enter__(self) -> "RespostaFalsa":
        return self

    def __exit__(self, *args) -> None:
        self.close()


def resposta(dados) -> RespostaFalsa:
    """Empacota um objeto Python como corpo JSON de uma resposta."""
    return RespostaFalsa(json.dumps(dados).encode("utf-8"))


def erro_http(codigo: int, cabecalhos=None) -> urllib.error.HTTPError:
    """Monta um erro HTTP com o codigo e os cabecalhos informados."""
    return urllib.error.HTTPError(
        url="https://api.github.com",
        code=codigo,
        msg="erro",
        hdrs=cabecalhos or {},
        fp=None,
    )


class TesteClienteGitHub(unittest.TestCase):
    """Verifica as URLs montadas, a paginacao e a traducao dos erros."""

    def setUp(self) -> None:
        self.cliente = ClienteGitHub()

    def test_perfil(self) -> None:
        with patch("urllib.request.urlopen", return_value=resposta({"login": "rafaela"})):
            perfil = self.cliente.buscar_perfil("rafaela")
        self.assertEqual(perfil["login"], "rafaela")

    def test_perfil_com_resposta_em_lista_e_recusado(self) -> None:
        with patch("urllib.request.urlopen", return_value=resposta([])):
            with self.assertRaises(ErroDeApi):
                self.cliente.buscar_perfil("rafaela")

    def test_repositorios_param_de_uma_pagina_quando_o_lote_e_pequeno(self) -> None:
        with patch("urllib.request.urlopen", return_value=resposta([{"name": "um"}])) as ch:
            repositorios = self.cliente.buscar_repositorios("rafaela")
        self.assertEqual(len(repositorios), 1)
        self.assertEqual(ch.call_count, 1)
        self.assertIn("per_page=100", ch.call_args[0][0].full_url)

    def test_repositorios_seguem_para_a_proxima_pagina_quando_o_lote_enche(self) -> None:
        cheia = resposta([{"name": f"r{i}"} for i in range(100)])
        parcial = resposta([{"name": "ultimo"}])
        with patch("urllib.request.urlopen", side_effect=[cheia, parcial]) as chamada:
            repositorios = self.cliente.buscar_repositorios("rafaela")
        self.assertEqual(len(repositorios), 101)
        self.assertEqual(chamada.call_count, 2)

    def test_eventos_respeitam_o_limite(self) -> None:
        with patch("urllib.request.urlopen", return_value=resposta([])) as chamada:
            self.cliente.buscar_eventos("rafaela", limite=500)
        self.assertIn("per_page=100", chamada.call_args[0][0].full_url)

    def test_nome_de_usuario_e_escapado(self) -> None:
        with patch("urllib.request.urlopen", return_value=resposta({})) as chamada:
            self.cliente.buscar_perfil("nome com espaco")
        self.assertIn("nome%20com%20espaco", chamada.call_args[0][0].full_url)

    def test_token_vira_cabecalho_de_autorizacao(self) -> None:
        cliente = ClienteGitHub(token="secreto")
        with patch("urllib.request.urlopen", return_value=resposta({})) as chamada:
            cliente.buscar_perfil("rafaela")
        self.assertEqual(
            chamada.call_args[0][0].headers.get("Authorization"), "Bearer secreto"
        )

    def test_usuario_vazio_e_recusado(self) -> None:
        with self.assertRaises(ErroDeApi):
            self.cliente.buscar_perfil("   ")

    def test_404_vira_usuario_nao_encontrado(self) -> None:
        with patch("urllib.request.urlopen", side_effect=erro_http(404)):
            with self.assertRaises(UsuarioNaoEncontrado):
                self.cliente.buscar_perfil("nao-existe-mesmo")

    def test_403_com_limite_zerado_vira_limite_excedido(self) -> None:
        with patch(
            "urllib.request.urlopen",
            side_effect=erro_http(403, {"X-RateLimit-Remaining": "0"}),
        ):
            with self.assertRaises(LimiteExcedido) as contexto:
                self.cliente.buscar_perfil("rafaela")
        self.assertIn("limite de requisicoes", str(contexto.exception))

    def test_erro_de_servidor_e_tratado(self) -> None:
        with patch("urllib.request.urlopen", side_effect=erro_http(502)):
            with self.assertRaises(ErroDeApi) as contexto:
                self.cliente.buscar_perfil("rafaela")
        self.assertIn("indisponivel", str(contexto.exception))

    def test_falha_de_rede_e_tratada(self) -> None:
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("sem rede")):
            with self.assertRaises(ErroDeApi) as contexto:
                self.cliente.buscar_perfil("rafaela")
        self.assertIn("nao foi possivel falar com a API", str(contexto.exception))

    def test_json_invalido_e_tratado(self) -> None:
        with patch("urllib.request.urlopen", return_value=RespostaFalsa(b"nao e json")):
            with self.assertRaises(ErroDeApi):
                self.cliente.buscar_perfil("rafaela")


if __name__ == "__main__":
    unittest.main()
