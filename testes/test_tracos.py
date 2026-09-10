"""Testes do algoritmo que transforma o perfil em tracos."""

import unittest
from datetime import datetime, timedelta, timezone

from dna import tracos

AGORA = datetime(2026, 9, 9, tzinfo=timezone.utc)


def repositorio(
    nome="repo",
    linguagem="Python",
    tamanho=1000,
    estrelas=0,
    forks=0,
    fork=False,
    criado_em="2026-01-01T00:00:00Z",
    empurrado_em="2026-09-01T00:00:00Z",
) -> dict:
    """Monta um repositorio no formato devolvido pela API."""
    return {
        "name": nome,
        "language": linguagem,
        "size": tamanho,
        "stargazers_count": estrelas,
        "forks_count": forks,
        "fork": fork,
        "created_at": criado_em,
        "pushed_at": empurrado_em,
    }


def evento(dias_atras=0, repositorio_nome="rafaela/projeto") -> dict:
    """Monta um evento datado a partir da data de referencia dos testes."""
    data = AGORA - timedelta(days=dias_atras)
    return {
        "type": "PushEvent",
        "repo": {"name": repositorio_nome},
        "created_at": data.isoformat().replace("+00:00", "Z"),
    }


class TesteNormalizacao(unittest.TestCase):
    """As notas precisam ficar sempre entre 0 e 100."""

    def test_zero_vira_zero(self) -> None:
        self.assertEqual(tracos.normalizar_log(0, 100), 0.0)

    def test_valor_na_referencia_chega_a_cem(self) -> None:
        self.assertAlmostEqual(tracos.normalizar_log(100, 100), 100.0)

    def test_valor_acima_da_referencia_nao_passa_de_cem(self) -> None:
        self.assertEqual(tracos.normalizar_log(10_000_000, 100), 100.0)

    def test_escala_e_logaritmica(self) -> None:
        # Metade da referencia vale bem mais do que metade da nota.
        self.assertGreater(tracos.normalizar_log(50, 100), 70)


class TesteSemente(unittest.TestCase):
    """A semente e o que garante que o mesmo perfil gere a mesma helice."""

    def test_mesma_pessoa_gera_a_mesma_semente(self) -> None:
        self.assertEqual(
            tracos.semente_do_usuario("rafaelacorrea"),
            tracos.semente_do_usuario("RafaelaCorrea"),
        )

    def test_pessoas_diferentes_geram_sementes_diferentes(self) -> None:
        self.assertNotEqual(
            tracos.semente_do_usuario("rafaelacorrea"),
            tracos.semente_do_usuario("torvalds"),
        )


class TesteEixoBackendFrontend(unittest.TestCase):
    """O eixo horizontal distribui exatamente 100 pontos entre os dois lados."""

    def test_soma_sempre_cem(self) -> None:
        eixo = tracos.eixo_backend_frontend(
            [repositorio(linguagem="Python"), repositorio(linguagem="CSS")]
        )
        self.assertAlmostEqual(eixo["backend"] + eixo["frontend"], 100.0)

    def test_so_backend_da_cem_por_cento(self) -> None:
        eixo = tracos.eixo_backend_frontend([repositorio(linguagem="Go")])
        self.assertEqual(eixo["backend"], 100.0)
        self.assertEqual(eixo["frontend"], 0.0)

    def test_forks_nao_contam_como_linguagem_propria(self) -> None:
        eixo = tracos.eixo_backend_frontend(
            [repositorio(linguagem="Python"), repositorio(linguagem="CSS", fork=True)]
        )
        self.assertEqual(eixo["backend"], 100.0)

    def test_sem_linguagem_classificada_o_eixo_fica_equilibrado(self) -> None:
        eixo = tracos.eixo_backend_frontend([repositorio(linguagem=None)])
        self.assertEqual(eixo, {"backend": 50.0, "frontend": 50.0})

    def test_repositorio_maior_pesa_mais(self) -> None:
        eixo = tracos.eixo_backend_frontend(
            [
                repositorio(linguagem="Python", tamanho=100_000),
                repositorio(linguagem="CSS", tamanho=1),
            ]
        )
        self.assertGreater(eixo["backend"], eixo["frontend"])


class TesteConsistencia(unittest.TestCase):
    """A consistencia mede ritmo, nao volume."""

    def test_sem_eventos_e_zero(self) -> None:
        self.assertEqual(tracos.traco_consistencia([]), 0.0)

    def test_todo_dia_ativo_da_nota_alta(self) -> None:
        eventos = [evento(dias_atras=dia) for dia in range(20)]
        self.assertGreater(tracos.traco_consistencia(eventos), 90)

    def test_rajada_isolada_da_nota_baixa(self) -> None:
        # Tres eventos no mesmo dia e um ha dois meses: muito volume, pouco ritmo.
        eventos = [evento(0), evento(0), evento(0), evento(60)]
        self.assertLess(tracos.traco_consistencia(eventos), 40)


class TesteExperimental(unittest.TestCase):
    """O traco experimental cresce com a variedade de linguagens."""

    def test_sem_repositorios_e_zero(self) -> None:
        self.assertEqual(tracos.traco_experimental([], AGORA), 0.0)

    def test_uma_linguagem_so_pontua_menos_que_varias(self) -> None:
        monolingue = [repositorio(nome=f"r{i}", linguagem="Python") for i in range(6)]
        poliglota = [
            repositorio(nome="a", linguagem="Python"),
            repositorio(nome="b", linguagem="Go"),
            repositorio(nome="c", linguagem="Rust"),
            repositorio(nome="d", linguagem="Elixir"),
            repositorio(nome="e", linguagem="TypeScript"),
            repositorio(nome="f", linguagem="Lua"),
        ]
        self.assertLess(
            tracos.traco_experimental(monolingue, AGORA),
            tracos.traco_experimental(poliglota, AGORA),
        )


class TesteOpenSource(unittest.TestCase):
    """Estrelas, forks, seguidores e trabalho em projetos de terceiros."""

    def test_perfil_sem_alcance_fica_perto_de_zero(self) -> None:
        nota = tracos.traco_open_source({}, [repositorio()], [evento()], "rafaela")
        self.assertLess(nota, 10)

    def test_projeto_popular_pontua_alto(self) -> None:
        nota = tracos.traco_open_source(
            {"followers": 5000},
            [repositorio(estrelas=90_000, forks=30_000)],
            [evento(repositorio_nome="outra-pessoa/projeto")],
            "rafaela",
        )
        self.assertGreater(nota, 90)

    def test_eventos_em_projetos_de_terceiros_contam(self) -> None:
        so_proprios = tracos.traco_open_source(
            {}, [repositorio()], [evento(repositorio_nome="rafaela/projeto")], "rafaela"
        )
        em_terceiros = tracos.traco_open_source(
            {}, [repositorio()], [evento(repositorio_nome="outra/projeto")], "rafaela"
        )
        self.assertGreater(em_terceiros, so_proprios)


class TesteCalcular(unittest.TestCase):
    """O resultado final precisa estar pronto para virar JSON."""

    def setUp(self) -> None:
        self.dna = tracos.calcular(
            "rafaelacorrea",
            {"name": "Rafaela Correa", "followers": 32, "public_repos": 3},
            [
                repositorio(nome="um", linguagem="Python", estrelas=4),
                repositorio(nome="dois", linguagem="CSS"),
                repositorio(nome="tres", linguagem="Ruby", fork=True),
            ],
            [evento(0), evento(1), evento(3)],
            AGORA,
        )

    def test_traz_todos_os_tracos_arredondados(self) -> None:
        self.assertEqual(set(self.dna["tracos"]), set(tracos.NOMES_DOS_TRACOS))
        for valor in self.dna["tracos"].values():
            self.assertIsInstance(valor, int)
            self.assertGreaterEqual(valor, 0)
            self.assertLessEqual(valor, 100)

    def test_traz_a_semente_e_os_rotulos(self) -> None:
        self.assertEqual(self.dna["semente"], tracos.semente_do_usuario("rafaelacorrea"))
        self.assertEqual(self.dna["rotulos"]["open_source"], "Open Source")

    def test_ranking_de_linguagens_ignora_forks(self) -> None:
        nomes = [item["nome"] for item in self.dna["linguagens"]]
        self.assertIn("Python", nomes)
        self.assertNotIn("Ruby", nomes)

    def test_estatisticas_separam_proprios_de_forks(self) -> None:
        estatisticas = self.dna["estatisticas"]
        self.assertEqual(estatisticas["repositorios_proprios"], 2)
        self.assertEqual(estatisticas["forks"], 1)
        self.assertEqual(estatisticas["estrelas_recebidas"], 4)
        self.assertEqual(estatisticas["dias_ativos"], 3)

    def test_mesmo_perfil_gera_o_mesmo_resultado(self) -> None:
        outro = tracos.calcular(
            "rafaelacorrea",
            {"name": "Rafaela Correa", "followers": 32, "public_repos": 3},
            [
                repositorio(nome="um", linguagem="Python", estrelas=4),
                repositorio(nome="dois", linguagem="CSS"),
                repositorio(nome="tres", linguagem="Ruby", fork=True),
            ],
            [evento(0), evento(1), evento(3)],
            AGORA,
        )
        self.assertEqual(self.dna, outro)


if __name__ == "__main__":
    unittest.main()
