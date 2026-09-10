"""Testes da linha de comando, com a API simulada."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from dna.cli import barra, main
from dna.github import UsuarioNaoEncontrado

PERFIL = {"name": "Rafaela Correa", "followers": 32, "public_repos": 2}

REPOSITORIOS = [
    {
        "name": "um",
        "language": "Python",
        "size": 800,
        "stargazers_count": 4,
        "forks_count": 1,
        "fork": False,
        "created_at": "2026-02-01T00:00:00Z",
        "pushed_at": "2026-09-01T00:00:00Z",
    },
    {
        "name": "dois",
        "language": "CSS",
        "size": 120,
        "stargazers_count": 0,
        "forks_count": 0,
        "fork": False,
        "created_at": "2026-03-01T00:00:00Z",
        "pushed_at": "2026-08-20T00:00:00Z",
    },
]

EVENTOS = [
    {
        "type": "PushEvent",
        "repo": {"name": "rafaelacorrea/um"},
        "created_at": "2026-09-08T10:00:00Z",
    },
    {
        "type": "WatchEvent",
        "repo": {"name": "outra/projeto"},
        "created_at": "2026-09-07T10:00:00Z",
    },
]


class TesteBarra(unittest.TestCase):
    """A barra de texto precisa ter sempre a mesma largura."""

    def test_extremos(self) -> None:
        self.assertEqual(barra(0, 10), "[..........]")
        self.assertEqual(barra(100, 10), "[##########]")

    def test_meio(self) -> None:
        self.assertEqual(barra(50, 10), "[#####.....]")

    def test_valor_fora_da_faixa_nao_estoura(self) -> None:
        self.assertEqual(len(barra(500, 10)), 12)
        self.assertEqual(len(barra(-20, 10)), 12)


class TesteCli(unittest.TestCase):
    """Executa o `main` como o terminal faria e inspeciona a saida."""

    def setUp(self) -> None:
        self.diretorio = tempfile.TemporaryDirectory()
        self.saida = Path(self.diretorio.name) / "dna.json"

    def tearDown(self) -> None:
        self.diretorio.cleanup()

    def rodar(self, *argumentos: str, erro=None):
        """Roda um comando com a API simulada e devolve (codigo, saida, erro)."""
        perfil = {"side_effect": erro} if erro else {"return_value": PERFIL}
        texto, texto_erro = io.StringIO(), io.StringIO()

        with patch("dna.cli.ClienteGitHub.buscar_perfil", **perfil), patch(
            "dna.cli.ClienteGitHub.buscar_repositorios", return_value=REPOSITORIOS
        ), patch("dna.cli.ClienteGitHub.buscar_eventos", return_value=EVENTOS):
            with redirect_stdout(texto), redirect_stderr(texto_erro):
                codigo = main(list(argumentos))

        return codigo, texto.getvalue(), texto_erro.getvalue()

    def test_resumo_em_texto(self) -> None:
        codigo, saida, _ = self.rodar("rafaelacorrea", "--so-texto")
        self.assertEqual(codigo, 0)
        self.assertIn("DNA do desenvolvedor: rafaelacorrea", saida)
        self.assertIn("Backend", saida)
        self.assertIn("Open Source", saida)
        self.assertIn("Semente da estrutura:", saida)
        self.assertIn("Linguagens: Python", saida)

    def test_so_texto_nao_grava_arquivo(self) -> None:
        self.rodar("rafaelacorrea", "--so-texto", "--saida", str(self.saida))
        self.assertFalse(self.saida.exists())

    def test_grava_o_json_no_caminho_indicado(self) -> None:
        codigo, saida, _ = self.rodar("rafaelacorrea", "--saida", str(self.saida))
        self.assertEqual(codigo, 0)
        self.assertIn("Arquivo gravado em", saida)

        dna = json.loads(self.saida.read_text(encoding="utf-8"))
        self.assertEqual(dna["usuario"], "rafaelacorrea")
        self.assertEqual(len(dna["tracos"]), 6)
        self.assertIn("semente", dna)
        self.assertIn("linguagens", dna)

    def test_usuario_inexistente_retorna_codigo_de_erro(self) -> None:
        falha = UsuarioNaoEncontrado("usuario fantasma nao encontrado no GitHub")
        codigo, _, erro = self.rodar("fantasma", "--so-texto", erro=falha)
        self.assertEqual(codigo, 1)
        self.assertIn("nao encontrado no GitHub", erro)


if __name__ == "__main__":
    unittest.main()
