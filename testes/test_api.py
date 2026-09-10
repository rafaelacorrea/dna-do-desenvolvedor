"""Testes da API HTTP, com o servidor de verdade no ar e o GitHub simulado.

O servidor sobe em uma porta livre dentro do proprio teste e as requisicoes
saem por `urllib`, entao o que esta sendo verificado e o comportamento real das
rotas: codigos de situacao, cabecalhos e o que fica gravado em disco.
"""

import json
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory

from dna.api import ServicoDeDna, criar_servidor, responder
from dna.github import ErroDeApi, LimiteExcedido, UsuarioNaoEncontrado

PERFIL = {"login": "rafaelacorrea", "name": "Rafaela Correa", "followers": 32, "public_repos": 2}

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
    }
]

EVENTOS = [
    {
        "type": "PushEvent",
        "repo": {"name": "rafaelacorrea/um"},
        "created_at": "2026-09-08T10:00:00Z",
    }
]


class ClienteFalso:
    """Imita o `ClienteGitHub` contando chamadas e podendo falhar de proposito."""

    def __init__(self, erro=None, login="rafaelacorrea") -> None:
        self.erro = erro
        self.login = login
        self.chamadas = 0

    def _conferir(self) -> None:
        if self.erro:
            raise self.erro

    def buscar_perfil(self, usuario):
        self.chamadas += 1
        self._conferir()
        return {**PERFIL, "login": self.login}

    def buscar_repositorios(self, usuario, paginas=3):
        self._conferir()
        return REPOSITORIOS

    def buscar_eventos(self, usuario, limite=100):
        self._conferir()
        return EVENTOS


class BaseDeApi(unittest.TestCase):
    """Sobe o servidor antes de cada teste e derruba no fim."""

    erro = None
    login = "rafaelacorrea"

    def setUp(self) -> None:
        self.diretorio = TemporaryDirectory()
        self.pasta_web = Path(self.diretorio.name)
        self.pasta_dados = self.pasta_web / "dados"
        self.pasta_dados.mkdir()
        (self.pasta_web / "index.html").write_text("<h1>cena</h1>", encoding="utf-8")

        self.cliente = ClienteFalso(self.erro, self.login)
        servico = ServicoDeDna(self.pasta_dados, self.cliente)
        self.servidor = criar_servidor(0, "127.0.0.1", self.pasta_web, servico)
        self.porta = self.servidor.server_address[1]

        self.thread = threading.Thread(target=self.servidor.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.servidor.shutdown()
        self.servidor.server_close()
        self.thread.join(timeout=5)
        self.diretorio.cleanup()

    def pegar(self, caminho: str):
        """Faz um GET e devolve (situacao, cabecalhos, corpo)."""
        url = f"http://127.0.0.1:{self.porta}{caminho}"
        try:
            with urllib.request.urlopen(url, timeout=10) as resposta:
                return resposta.status, dict(resposta.headers), resposta.read().decode()
        except urllib.error.HTTPError as erro:
            return erro.code, dict(erro.headers), erro.read().decode()


class TesteColeta(BaseDeApi):
    """O caminho feliz: usuario novo, coletado e gravado."""

    def test_usuario_novo_e_coletado_no_github(self) -> None:
        situacao, cabecalhos, corpo = self.pegar("/api/dna/rafaelacorrea")
        self.assertEqual(situacao, 200)
        self.assertEqual(cabecalhos.get("X-Dna-Origem"), "github")
        self.assertEqual(cabecalhos.get("X-Dna-Api"), "1")

        dna = json.loads(corpo)
        self.assertEqual(dna["usuario"], "rafaelacorrea")
        self.assertEqual(len(dna["tracos"]), 6)

    def test_coleta_grava_o_arquivo_e_o_indice(self) -> None:
        self.pegar("/api/dna/rafaelacorrea")
        self.assertTrue((self.pasta_dados / "rafaelacorrea.json").exists())

        indice = json.loads((self.pasta_dados / "index.json").read_text(encoding="utf-8"))
        self.assertEqual([entrada["usuario"] for entrada in indice], ["rafaelacorrea"])

    def test_segunda_chamada_nao_volta_ao_github(self) -> None:
        self.pegar("/api/dna/rafaelacorrea")
        _, cabecalhos, _ = self.pegar("/api/dna/rafaelacorrea")

        # A memoria responde antes do disco: o perfil acabou de ser coletado.
        self.assertEqual(cabecalhos.get("X-Dna-Origem"), "memoria")
        self.assertEqual(self.cliente.chamadas, 1)

    def test_processo_novo_encontra_o_arquivo(self) -> None:
        self.pegar("/api/dna/rafaelacorrea")

        # Um servico recem-criado nao tem memoria, mas o arquivo continua la.
        outro = ServicoDeDna(self.pasta_dados, ClienteFalso())
        dna, origem = outro.obter("rafaelacorrea")

        self.assertEqual(origem, "arquivo")
        self.assertEqual(dna["usuario"], "rafaelacorrea")

    def test_forcar_ignora_o_arquivo(self) -> None:
        self.pegar("/api/dna/rafaelacorrea")
        _, cabecalhos, _ = self.pegar("/api/dna/rafaelacorrea?forcar=1")

        self.assertEqual(cabecalhos.get("X-Dna-Origem"), "github")
        self.assertEqual(self.cliente.chamadas, 2)

    def test_indice_lista_o_que_foi_coletado(self) -> None:
        self.pegar("/api/dna/rafaelacorrea")
        situacao, _, corpo = self.pegar("/api/indice")

        self.assertEqual(situacao, 200)
        self.assertEqual(len(json.loads(corpo)), 1)

    def test_a_cena_continua_sendo_servida(self) -> None:
        situacao, cabecalhos, corpo = self.pegar("/index.html")
        self.assertEqual(situacao, 200)
        self.assertIn("cena", corpo)
        self.assertIsNone(cabecalhos.get("X-Dna-Api"))

    def test_rota_desconhecida_da_api(self) -> None:
        situacao, _, corpo = self.pegar("/api/qualquer-coisa")
        self.assertEqual(situacao, 404)
        self.assertIn("rota desconhecida", json.loads(corpo)["erro"])


class TesteGrafiaDoLogin(BaseDeApi):
    """O nome digitado pode vir em qualquer caixa; o arquivo e um so."""

    login = "RafaelaCorrea"

    def test_arquivo_usa_o_nome_em_minusculas(self) -> None:
        self.pegar("/api/dna/RAFAELACORREA")
        self.assertTrue((self.pasta_dados / "rafaelacorrea.json").exists())

    def test_grafia_diferente_reaproveita_o_resultado(self) -> None:
        self.pegar("/api/dna/RAFAELACORREA")
        _, cabecalhos, _ = self.pegar("/api/dna/rafaelacorrea")

        self.assertEqual(cabecalhos.get("X-Dna-Origem"), "memoria")
        self.assertEqual(self.cliente.chamadas, 1)


class TesteNomeInvalido(BaseDeApi):
    """Nomes fora da regra do GitHub sao recusados antes de qualquer coleta."""

    def test_travessia_de_caminho_e_recusada(self) -> None:
        situacao, _, corpo = self.pegar("/api/dna/..%2F..%2Fetc%2Fpasswd")
        self.assertEqual(situacao, 400)
        self.assertIn("nao e um nome de usuario valido", json.loads(corpo)["erro"])
        self.assertEqual(self.cliente.chamadas, 0)

    def test_nome_com_caracteres_estranhos_e_recusado(self) -> None:
        situacao, _, _ = self.pegar("/api/dna/nome%20com%20espaco")
        self.assertEqual(situacao, 400)
        self.assertEqual(self.cliente.chamadas, 0)


class TesteUsuarioInexistente(BaseDeApi):
    """Falhas do GitHub viram codigos HTTP correspondentes."""

    erro = UsuarioNaoEncontrado("usuario 'fantasma' nao encontrado no GitHub")

    def test_devolve_404_com_a_mensagem(self) -> None:
        situacao, _, corpo = self.pegar("/api/dna/fantasma")
        self.assertEqual(situacao, 404)
        self.assertIn("nao encontrado no GitHub", json.loads(corpo)["erro"])


class TesteLimiteExcedido(BaseDeApi):
    """O limite da API do GitHub precisa chegar legivel na tela."""

    erro = LimiteExcedido("limite de requisicoes da API do GitHub atingido")

    def test_devolve_429(self) -> None:
        situacao, _, corpo = self.pegar("/api/dna/rafaelacorrea")
        self.assertEqual(situacao, 429)
        self.assertIn("limite de requisicoes", json.loads(corpo)["erro"])


class TesteApiIndisponivel(BaseDeApi):
    """Qualquer outra falha da API do GitHub vira 502."""

    erro = ErroDeApi("a API do GitHub esta indisponivel (codigo 503)")

    def test_devolve_502(self) -> None:
        situacao, _, corpo = self.pegar("/api/dna/rafaelacorrea")
        self.assertEqual(situacao, 502)
        self.assertIn("indisponivel", json.loads(corpo)["erro"])


class TesteSomenteLeitura(unittest.TestCase):
    """Modo usado na nuvem, onde o disco nao aceita escrita."""

    def setUp(self) -> None:
        self.diretorio = TemporaryDirectory()
        self.pasta = Path(self.diretorio.name)
        self.cliente = ClienteFalso()
        self.servico = ServicoDeDna(self.pasta, self.cliente, gravar_resultado=False)

    def tearDown(self) -> None:
        self.diretorio.cleanup()

    def test_nao_grava_nada_no_disco(self) -> None:
        self.servico.obter("rafaelacorrea")
        self.assertEqual(list(self.pasta.iterdir()), [])

    def test_memoria_evita_a_segunda_coleta(self) -> None:
        self.servico.obter("rafaelacorrea")
        dna, origem = self.servico.obter("rafaelacorrea")

        self.assertEqual(origem, "memoria")
        self.assertEqual(dna["usuario"], "rafaelacorrea")
        self.assertEqual(self.cliente.chamadas, 1)

    def test_forcar_ignora_a_memoria(self) -> None:
        self.servico.obter("rafaelacorrea")
        _, origem = self.servico.obter("rafaelacorrea", forcar=True)

        self.assertEqual(origem, "github")
        self.assertEqual(self.cliente.chamadas, 2)

    def test_memoria_descarta_os_mais_antigos(self) -> None:
        servico = ServicoDeDna(
            self.pasta, ClienteFalso(), gravar_resultado=False, memoria_maxima=2
        )
        for login in ("um", "dois", "tres"):
            servico.cliente.login = login
            servico.obter(login)

        self.assertIsNone(servico.ler_da_memoria("um"))
        self.assertIsNotNone(servico.ler_da_memoria("tres"))


class TesteResponder(unittest.TestCase):
    """A funcao usada tanto pelo servidor local quanto pela funcao na nuvem."""

    def setUp(self) -> None:
        self.diretorio = TemporaryDirectory()
        self.servico = ServicoDeDna(
            Path(self.diretorio.name), ClienteFalso(), gravar_resultado=False
        )

    def tearDown(self) -> None:
        self.diretorio.cleanup()

    def test_sucesso(self) -> None:
        situacao, corpo, origem = responder(self.servico, "rafaelacorrea")
        self.assertEqual(situacao, 200)
        self.assertEqual(origem, "github")
        self.assertEqual(corpo["usuario"], "rafaelacorrea")

    def test_nome_vazio(self) -> None:
        situacao, corpo, _ = responder(self.servico, "   ")
        self.assertEqual(situacao, 400)
        self.assertIn("nao e um nome de usuario valido", corpo["erro"])

    def test_falha_do_github_vira_codigo(self) -> None:
        servico = ServicoDeDna(
            Path(self.diretorio.name),
            ClienteFalso(UsuarioNaoEncontrado("nao encontrado no GitHub")),
            gravar_resultado=False,
        )
        situacao, corpo, _ = responder(servico, "fantasma")
        self.assertEqual(situacao, 404)
        self.assertIn("nao encontrado", corpo["erro"])


if __name__ == "__main__":
    unittest.main()
