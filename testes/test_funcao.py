"""Testes da funcao sem estado usada pela hospedagem.

A funcao e o unico ponto de entrada Python la, entao ela precisa resolver
sozinha qual rota foi pedida. O que se verifica aqui e esse roteamento; a
coleta em si ja esta coberta em `test_api.py`.
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import api.dna as funcao
from dna.api import ServicoDeDna
from dna.github import UsuarioNaoEncontrado
from testes.test_api import ClienteFalso


class TesteResolver(unittest.TestCase):
    """Cada caminho possivel que a hospedagem pode entregar a funcao."""

    def setUp(self) -> None:
        self.diretorio = TemporaryDirectory()
        self.pasta = Path(self.diretorio.name)
        self.cliente = ClienteFalso()
        self.servico = ServicoDeDna(self.pasta, self.cliente, gravar_resultado=False)

        remendo = patch.object(funcao, "SERVICO", self.servico)
        remendo.start()
        self.addCleanup(remendo.stop)

    def tearDown(self) -> None:
        self.diretorio.cleanup()

    def test_usuario_na_query(self) -> None:
        situacao, corpo, origem = funcao.resolver("/api/dna", {"usuario": ["rafaelacorrea"]})
        self.assertEqual(int(situacao), 200)
        self.assertEqual(corpo["usuario"], "rafaelacorrea")
        self.assertEqual(origem, "github")

    def test_usuario_no_caminho(self) -> None:
        # Se o rewrite nao entrar, o nome ainda chega no proprio caminho.
        situacao, corpo, _ = funcao.resolver("/api/dna/rafaelacorrea", {})
        self.assertEqual(int(situacao), 200)
        self.assertEqual(corpo["usuario"], "rafaelacorrea")

    def test_caminho_sem_usuario(self) -> None:
        situacao, corpo, _ = funcao.resolver("/api/dna", {})
        self.assertEqual(int(situacao), 400)
        self.assertIn("nao e um nome de usuario valido", corpo["erro"])

    def test_forcar_repete_a_coleta(self) -> None:
        funcao.resolver("/api/dna", {"usuario": ["rafaelacorrea"]})
        _, _, origem = funcao.resolver(
            "/api/dna", {"usuario": ["rafaelacorrea"], "forcar": ["1"]}
        )
        self.assertEqual(origem, "github")
        self.assertEqual(self.cliente.chamadas, 2)

    def test_erro_do_github_vira_codigo(self) -> None:
        self.cliente.erro = UsuarioNaoEncontrado("usuario nao encontrado no GitHub")
        situacao, corpo, _ = funcao.resolver("/api/dna", {"usuario": ["fantasma"]})
        self.assertEqual(int(situacao), 404)
        self.assertIn("nao encontrado", corpo["erro"])

    def test_rota_desconhecida(self) -> None:
        situacao, corpo, _ = funcao.resolver("/qualquer/coisa", {})
        self.assertEqual(int(situacao), 404)
        self.assertEqual(corpo["erro"], "rota desconhecida")


class TesteIndiceDaFuncao(unittest.TestCase):
    """A rota do indice le o arquivo versionado no repositorio."""

    def test_devolve_a_colecao_commitada(self) -> None:
        situacao, corpo, _ = funcao.resolver("/api/indice", {})
        self.assertEqual(int(situacao), 200)
        self.assertIsInstance(corpo, list)
        self.assertTrue(all("usuario" in entrada for entrada in corpo))

    def test_indice_ausente_devolve_lista_vazia(self) -> None:
        with TemporaryDirectory() as pasta:
            inexistente = Path(pasta) / "nao-existe.json"
            with patch.object(funcao, "_caminho_do_indice", lambda: inexistente):
                situacao, corpo, _ = funcao.resolver("/api/indice", {})

        self.assertEqual(int(situacao), 200)
        self.assertEqual(corpo, [])


if __name__ == "__main__":
    unittest.main()
