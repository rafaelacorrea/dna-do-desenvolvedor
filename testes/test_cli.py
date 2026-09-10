"""Testes da linha de comando, com a API simulada."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from dna.cli import ARQUIVO_DE_INDICE, barra, main, gravar_indice, montar_indice
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


class TesteIndice(unittest.TestCase):
    """O indice e reconstruido a partir dos arquivos que existem na pasta."""

    def setUp(self) -> None:
        self.diretorio = tempfile.TemporaryDirectory()
        self.pasta = Path(self.diretorio.name)

    def tearDown(self) -> None:
        self.diretorio.cleanup()

    def escrever(self, usuario: str, gerado_em: str = "2026-09-09T00:00:00+00:00") -> None:
        """Grava um JSON de DNA minimo na pasta de dados."""
        dados = {
            "usuario": usuario,
            "nome": usuario.title(),
            "semente": 123,
            "gerado_em": gerado_em,
            "tracos": {"backend": 60, "frontend": 40},
            "linguagens": [{"nome": "Python", "percentual": 100.0, "cor": "#4b8bbe"}],
        }
        (self.pasta / f"{usuario}.json").write_text(
            json.dumps(dados), encoding="utf-8"
        )

    def test_pasta_vazia_gera_indice_vazio(self) -> None:
        self.assertEqual(montar_indice(self.pasta), [])

    def test_lista_os_perfis_do_mais_recente_para_o_mais_antigo(self) -> None:
        self.escrever("antiga", "2026-01-01T00:00:00+00:00")
        self.escrever("recente", "2026-09-09T00:00:00+00:00")
        usuarios = [entrada["usuario"] for entrada in montar_indice(self.pasta)]
        self.assertEqual(usuarios, ["recente", "antiga"])

    def test_entrada_leva_o_necessario_para_a_cena(self) -> None:
        self.escrever("rafaelacorrea")
        entrada = montar_indice(self.pasta)[0]
        self.assertEqual(entrada["nome"], "Rafaelacorrea")
        self.assertEqual(entrada["semente"], 123)
        self.assertEqual(entrada["cor"], "#4b8bbe")
        self.assertEqual(entrada["tracos"]["backend"], 60)

    def test_o_proprio_indice_nao_entra_no_indice(self) -> None:
        self.escrever("rafaelacorrea")
        gravar_indice(self.pasta)
        gravar_indice(self.pasta)
        self.assertEqual(len(montar_indice(self.pasta)), 1)

    def test_arquivo_invalido_e_ignorado(self) -> None:
        self.escrever("rafaelacorrea")
        (self.pasta / "quebrado.json").write_text("{ isso nao e json", encoding="utf-8")
        (self.pasta / "outro.json").write_text('{"sem": "tracos"}', encoding="utf-8")
        self.assertEqual(len(montar_indice(self.pasta)), 1)

    def test_perfil_apagado_some_do_indice(self) -> None:
        self.escrever("um")
        self.escrever("dois")
        gravar_indice(self.pasta)
        (self.pasta / "dois.json").unlink()
        caminho = gravar_indice(self.pasta)

        indice = json.loads(caminho.read_text(encoding="utf-8"))
        self.assertEqual([entrada["usuario"] for entrada in indice], ["um"])

    def test_gravar_indice_usa_o_nome_esperado(self) -> None:
        self.assertEqual(gravar_indice(self.pasta).name, ARQUIVO_DE_INDICE)


if __name__ == "__main__":
    unittest.main()
