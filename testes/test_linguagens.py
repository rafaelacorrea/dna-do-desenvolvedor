"""Testes da classificacao e das cores das linguagens."""

import colorsys
import unittest

from dna import linguagens


def luminosidade(cor_hex: str) -> float:
    """Devolve a luminosidade HLS de uma cor em formato hexadecimal."""
    vermelho = int(cor_hex[1:3], 16) / 255
    verde = int(cor_hex[3:5], 16) / 255
    azul = int(cor_hex[5:7], 16) / 255
    return colorsys.rgb_to_hls(vermelho, verde, azul)[1]


class TesteGrupo(unittest.TestCase):
    """Cada linguagem cai em backend, frontend ou outros."""

    def test_backend(self) -> None:
        for nome in ("Python", "go", "  Rust  ", "C#"):
            self.assertEqual(linguagens.grupo(nome), "backend", nome)

    def test_frontend(self) -> None:
        for nome in ("JavaScript", "typescript", "CSS", "Vue"):
            self.assertEqual(linguagens.grupo(nome), "frontend", nome)

    def test_outros(self) -> None:
        for nome in (None, "", "Jupyter Notebook", "TeX"):
            self.assertEqual(linguagens.grupo(nome), "outros", nome)


class TesteCor(unittest.TestCase):
    """As cores precisam existir sempre e aparecer no fundo escuro."""

    def test_linguagem_conhecida_usa_a_cor_oficial(self) -> None:
        self.assertEqual(linguagens.cor("Python"), "#4b8bbe")

    def test_cor_escura_e_clareada(self) -> None:
        # O tom oficial do C (#555555) sumiria no fundo preto da cena.
        self.assertGreaterEqual(luminosidade(linguagens.cor("C")), 0.49)

    def test_cinza_continua_cinza(self) -> None:
        clara = linguagens.cor("C")
        self.assertEqual(clara[1:3], clara[3:5])
        self.assertEqual(clara[3:5], clara[5:7])

    def test_linguagem_desconhecida_ganha_cor_estavel(self) -> None:
        primeira = linguagens.cor("OpenSCAD")
        self.assertTrue(primeira.startswith("#"))
        self.assertEqual(len(primeira), 7)
        self.assertEqual(primeira, linguagens.cor("openscad"))

    def test_linguagens_desconhecidas_diferentes_ganham_cores_diferentes(self) -> None:
        self.assertNotEqual(linguagens.cor("OpenSCAD"), linguagens.cor("Nim"))

    def test_sem_linguagem_usa_a_cor_neutra(self) -> None:
        self.assertEqual(linguagens.cor(None), linguagens.NEUTRA)


if __name__ == "__main__":
    unittest.main()
