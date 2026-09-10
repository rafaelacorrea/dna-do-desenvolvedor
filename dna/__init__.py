"""Pacote do DNA do Desenvolvedor.

Expoe os componentes principais para uso programatico:

    from dna import ClienteGitHub, calcular

A coleta de dados usa apenas `urllib`, da biblioteca padrao, e o calculo dos
tracos nao depende de nada alem da propria biblioteca padrao.
"""

from dna.github import (
    ClienteGitHub,
    ErroDeApi,
    LimiteExcedido,
    UsuarioNaoEncontrado,
)
from dna.tracos import NOMES_DOS_TRACOS, ROTULOS, calcular, semente_do_usuario

__all__ = [
    "ClienteGitHub",
    "ErroDeApi",
    "LimiteExcedido",
    "NOMES_DOS_TRACOS",
    "ROTULOS",
    "UsuarioNaoEncontrado",
    "calcular",
    "semente_do_usuario",
]

__version__ = "1.0.0"
