"""Classificacao das linguagens de programacao.

Cada linguagem principal de um repositorio e colocada em um dos tres grupos:
`backend`, `frontend` ou `outros`. Os dois primeiros formam o eixo horizontal
do DNA; o terceiro entra apenas na conta de diversidade.

A lista nao pretende ser uma verdade universal - ela e uma convencao do
projeto, documentada aqui para que qualquer pessoa possa ajustar.
"""

from __future__ import annotations

import colorsys
import hashlib

BACKEND = {
    "python",
    "java",
    "go",
    "rust",
    "c",
    "c++",
    "c#",
    "php",
    "ruby",
    "kotlin",
    "scala",
    "elixir",
    "erlang",
    "clojure",
    "haskell",
    "perl",
    "lua",
    "zig",
    "ocaml",
    "f#",
    "groovy",
    "shell",
    "powershell",
    "dockerfile",
    "makefile",
    "sql",
    "plpgsql",
    "tsql",
    "hcl",
}

FRONTEND = {
    "javascript",
    "typescript",
    "html",
    "css",
    "scss",
    "sass",
    "less",
    "vue",
    "svelte",
    "astro",
    "elm",
    "coffeescript",
    "handlebars",
    "ejs",
    "pug",
    "stylus",
    "dart",
    "objective-c",
    "swift",
}

# Cores usadas na visualizacao para as linguagens mais comuns. Linguagens sem
# cor definida caem em um tom neutro escolhido pela cena.
CORES = {
    "python": "#4b8bbe",
    "javascript": "#f1e05a",
    "typescript": "#3178c6",
    "java": "#b07219",
    "go": "#00add8",
    "rust": "#dea584",
    "ruby": "#701516",
    "php": "#4f5d95",
    "c": "#555555",
    "c++": "#f34b7d",
    "c#": "#178600",
    "html": "#e34c26",
    "css": "#563d7c",
    "scss": "#c6538c",
    "shell": "#89e051",
    "kotlin": "#a97bff",
    "swift": "#f05138",
    "dart": "#00b4ab",
    "vue": "#41b883",
    "elixir": "#6e4a7e",
    "lua": "#000080",
    "jupyter notebook": "#da5b0b",
}

NEUTRA = "#8b949e"


def _cor_derivada(nome: str) -> str:
    """Inventa uma cor estavel para linguagens fora da tabela.

    O tom vem de um hash do nome, com saturacao e luminosidade fixas para que
    a cor caia sempre na mesma familia visual do resto da cena.
    """
    matiz = int(hashlib.sha256(nome.encode("utf-8")).hexdigest()[:6], 16) % 360
    vermelho, verde, azul = colorsys.hls_to_rgb(matiz / 360, 0.62, 0.55)
    return "#{:02x}{:02x}{:02x}".format(
        round(vermelho * 255), round(verde * 255), round(azul * 255)
    )


def grupo(linguagem: str | None) -> str:
    """Devolve 'backend', 'frontend' ou 'outros' para a linguagem informada."""
    if not linguagem:
        return "outros"
    nome = linguagem.strip().lower()
    if nome in BACKEND:
        return "backend"
    if nome in FRONTEND:
        return "frontend"
    return "outros"


def _clarear(cor_hex: str, luminosidade_minima: float = 0.5) -> str:
    """Levanta a luminosidade de cores escuras demais.

    A cena e preta: tons como o do C (#555555) ou o do Lua (#000080) sumiriam
    completamente. Esta funcao preserva o matiz original e so garante que a
    cor tenha brilho suficiente para aparecer.
    """
    vermelho = int(cor_hex[1:3], 16) / 255
    verde = int(cor_hex[3:5], 16) / 255
    azul = int(cor_hex[5:7], 16) / 255
    matiz, luminosidade, saturacao = colorsys.rgb_to_hls(vermelho, verde, azul)
    if luminosidade >= luminosidade_minima:
        return cor_hex
    # Cinzas continuam cinzas: forcar saturacao neles inventaria um matiz.
    if saturacao > 0.05:
        saturacao = max(saturacao, 0.25)
    vermelho, verde, azul = colorsys.hls_to_rgb(matiz, luminosidade_minima, saturacao)
    return "#{:02x}{:02x}{:02x}".format(
        round(vermelho * 255), round(verde * 255), round(azul * 255)
    )


def cor(linguagem: str | None) -> str:
    """Devolve a cor da linguagem: a oficial, ou uma derivada do nome."""
    if not linguagem:
        return NEUTRA
    nome = linguagem.strip().lower()
    if nome in CORES:
        return _clarear(CORES[nome])
    return _cor_derivada(nome)
