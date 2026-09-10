"""O algoritmo que transforma um perfil do GitHub em DNA.

A ideia central: em vez de somar numeros e montar um grafico, o perfil vira um
conjunto de seis tracos que ocupam tres eixos opostos. Sao esses tres eixos
que a cena 3D usa para construir a helice.

    OPEN SOURCE                 (eixo vertical)
         |
    BACKEND --- FRONTEND        (eixo horizontal)
         |
     ATIVIDADE

    CONSISTENCIA --- EXPERIMENTAL   (eixo de profundidade)

Todos os tracos vao de 0 a 100 e sao calculados a partir de tres fontes
publicas: o perfil, a lista de repositorios e os eventos recentes.
"""

from __future__ import annotations

import hashlib
import math
import statistics
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence

from dna import linguagens

NOMES_DOS_TRACOS = (
    "backend",
    "frontend",
    "open_source",
    "atividade",
    "consistencia",
    "experimental",
)

ROTULOS = {
    "backend": "Backend",
    "frontend": "Frontend",
    "open_source": "Open Source",
    "atividade": "Atividade",
    "consistencia": "Consistencia",
    "experimental": "Experimental",
}

# Valores de referencia para as normalizacoes logaritmicas. Atingir a
# referencia equivale a chegar perto de 100 no traco correspondente.
REFERENCIA_ESTRELAS = 200
REFERENCIA_FORKS = 60
REFERENCIA_SEGUIDORES = 300


def limitar(valor: float, minimo: float = 0.0, maximo: float = 100.0) -> float:
    """Mantem o valor dentro da faixa informada."""
    return max(minimo, min(maximo, valor))


def normalizar_log(valor: float, referencia: float) -> float:
    """Converte uma contagem em uma nota de 0 a 100 em escala logaritmica.

    A escala logaritmica evita que um unico repositorio muito popular domine
    o resultado e da peso aos primeiros passos de quem esta comecando.
    """
    if valor <= 0 or referencia <= 0:
        return 0.0
    return limitar(100 * math.log1p(valor) / math.log1p(referencia))


def semente_do_usuario(usuario: str) -> int:
    """Gera uma semente estavel a partir do nome de usuario.

    O mesmo usuario sempre produz a mesma estrutura, mesmo em maquinas
    diferentes, porque a semente vem de um hash e nao do relogio.
    """
    resumo = hashlib.sha256(usuario.strip().lower().encode("utf-8")).hexdigest()
    return int(resumo[:8], 16)


def _data(texto: Optional[str]) -> Optional[datetime]:
    """Converte uma data ISO da API em `datetime`, ou devolve None."""
    if not texto:
        return None
    try:
        return datetime.fromisoformat(str(texto).replace("Z", "+00:00"))
    except ValueError:
        return None


def _proprios(repositorios: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filtra os repositorios que nao sao forks de outras pessoas."""
    return [repo for repo in repositorios if not repo.get("fork")]


def peso_do_repositorio(repositorio: Dict[str, Any]) -> float:
    """Peso de um repositorio na conta de linguagens.

    Usa uma escala logaritmica do tamanho para que projetos grandes contem
    mais, sem que um monorepo apague todo o resto.
    """
    tamanho = repositorio.get("size") or 0
    return 1.0 + math.log10(1 + max(0, int(tamanho)))


def pesos_por_linguagem(repositorios: Sequence[Dict[str, Any]]) -> Dict[str, float]:
    """Soma o peso de cada linguagem principal entre os repositorios proprios."""
    pesos: Dict[str, float] = {}
    for repositorio in _proprios(repositorios):
        linguagem = repositorio.get("language")
        if not linguagem:
            continue
        pesos[linguagem] = pesos.get(linguagem, 0.0) + peso_do_repositorio(repositorio)
    return pesos


def ranking_de_linguagens(
    repositorios: Sequence[Dict[str, Any]], quantidade: int = 6
) -> List[Dict[str, Any]]:
    """Devolve as linguagens mais usadas, com percentual e cor."""
    pesos = pesos_por_linguagem(repositorios)
    total = sum(pesos.values())
    if not total:
        return []
    ordenadas = sorted(pesos.items(), key=lambda item: item[1], reverse=True)
    return [
        {
            "nome": nome,
            "percentual": round(100 * peso / total, 1),
            "grupo": linguagens.grupo(nome),
            "cor": linguagens.cor(nome),
        }
        for nome, peso in ordenadas[:quantidade]
    ]


def eixo_backend_frontend(repositorios: Sequence[Dict[str, Any]]) -> Dict[str, float]:
    """Distribui 100 pontos entre backend e frontend.

    Linguagens que nao pertencem a nenhum dos dois grupos ficam de fora desta
    conta; elas entram apenas no traco experimental. Sem nenhuma linguagem
    classificada, o eixo fica equilibrado em 50 para cada lado.
    """
    pesos = pesos_por_linguagem(repositorios)
    soma = {"backend": 0.0, "frontend": 0.0}
    for nome, peso in pesos.items():
        grupo = linguagens.grupo(nome)
        if grupo in soma:
            soma[grupo] += peso

    total = soma["backend"] + soma["frontend"]
    if total <= 0:
        return {"backend": 50.0, "frontend": 50.0}

    backend = 100 * soma["backend"] / total
    return {"backend": backend, "frontend": 100 - backend}


def traco_open_source(
    perfil: Dict[str, Any],
    repositorios: Sequence[Dict[str, Any]],
    eventos: Sequence[Dict[str, Any]],
    usuario: str,
) -> float:
    """Mede o alcance do trabalho publico e a participacao em projetos alheios."""
    proprios = _proprios(repositorios)
    estrelas = sum(int(repo.get("stargazers_count") or 0) for repo in proprios)
    forks = sum(int(repo.get("forks_count") or 0) for repo in proprios)
    seguidores = int(perfil.get("followers") or 0)

    prefixo = f"{usuario.strip().lower()}/"
    externos = [
        evento
        for evento in eventos
        if not str((evento.get("repo") or {}).get("name", "")).lower().startswith(prefixo)
    ]
    participacao = 100 * len(externos) / len(eventos) if eventos else 0.0

    return limitar(
        0.35 * normalizar_log(estrelas, REFERENCIA_ESTRELAS)
        + 0.25 * normalizar_log(forks, REFERENCIA_FORKS)
        + 0.20 * normalizar_log(seguidores, REFERENCIA_SEGUIDORES)
        + 0.20 * participacao
    )


def traco_atividade(
    repositorios: Sequence[Dict[str, Any]],
    eventos: Sequence[Dict[str, Any]],
    agora: Optional[datetime] = None,
) -> float:
    """Mede o volume de trabalho recente.

    Combina a quantidade de eventos publicos (a API entrega no maximo os 100
    mais recentes) com a quantidade de repositorios tocados nos ultimos meses.
    """
    referencia = agora or datetime.now(timezone.utc)
    volume = normalizar_log(len(eventos), 100)

    recentes = 0
    for repositorio in repositorios:
        empurrado = _data(repositorio.get("pushed_at"))
        if empurrado and (referencia - empurrado).days <= 90:
            recentes += 1
    frentes = normalizar_log(recentes, 15)

    return limitar(0.6 * volume + 0.4 * frentes)


def traco_consistencia(eventos: Sequence[Dict[str, Any]]) -> float:
    """Mede a regularidade do ritmo, nao o volume.

    Duas coisas contam: quantos dias do periodo observado tiveram atividade e
    o quanto os intervalos entre um dia ativo e outro se parecem entre si.
    """
    datas = sorted({d.date() for d in (_data(e.get("created_at")) for e in eventos) if d})
    if len(datas) < 2:
        return 0.0 if not datas else 20.0

    periodo = (datas[-1] - datas[0]).days + 1
    cobertura = 100 * len(datas) / periodo

    intervalos = [(b - a).days for a, b in zip(datas, datas[1:])]
    if len(intervalos) < 2:
        # Com um unico intervalo nao da para falar em ritmo: dois dias ativos
        # separados por dois meses seriam "perfeitamente regulares". Nesse caso
        # so a cobertura conta.
        return limitar(cobertura)

    media = statistics.fmean(intervalos)
    if media <= 0:
        regularidade = 100.0
    else:
        desvio = statistics.pstdev(intervalos)
        regularidade = limitar(100 * (1 - desvio / media))

    return limitar(0.6 * cobertura + 0.4 * regularidade)


def traco_experimental(
    repositorios: Sequence[Dict[str, Any]], agora: Optional[datetime] = None
) -> float:
    """Mede a vontade de comecar coisas novas e variar de linguagem.

    Tres sinais: a diversidade de linguagens (entropia de Shannon), a fatia de
    repositorios criados no ultimo ano e a fatia de repositorios pequenos, que
    costumam ser testes e provas de conceito.
    """
    proprios = _proprios(repositorios)
    if not proprios:
        return 0.0

    pesos = pesos_por_linguagem(repositorios)
    total = sum(pesos.values())
    if total > 0 and len(pesos) > 1:
        entropia = -sum(
            (peso / total) * math.log(peso / total) for peso in pesos.values() if peso > 0
        )
        diversidade = 100 * entropia / math.log(len(pesos))
    else:
        diversidade = 0.0

    referencia = agora or datetime.now(timezone.utc)
    novos = sum(
        1
        for repo in proprios
        if (criado := _data(repo.get("created_at"))) and (referencia - criado).days <= 365
    )
    fatia_novos = 100 * novos / len(proprios)

    pequenos = sum(1 for repo in proprios if (repo.get("size") or 0) < 500)
    fatia_pequenos = 100 * pequenos / len(proprios)

    return limitar(0.5 * diversidade + 0.3 * fatia_novos + 0.2 * fatia_pequenos)


def calcular(
    usuario: str,
    perfil: Dict[str, Any],
    repositorios: Sequence[Dict[str, Any]],
    eventos: Sequence[Dict[str, Any]],
    agora: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Monta o DNA completo, pronto para virar JSON e alimentar a cena 3D."""
    referencia = agora or datetime.now(timezone.utc)
    eixo = eixo_backend_frontend(repositorios)

    tracos = {
        "backend": eixo["backend"],
        "frontend": eixo["frontend"],
        "open_source": traco_open_source(perfil, repositorios, eventos, usuario),
        "atividade": traco_atividade(repositorios, eventos, referencia),
        "consistencia": traco_consistencia(eventos),
        "experimental": traco_experimental(repositorios, referencia),
    }
    arredondados = {nome: round(valor) for nome, valor in tracos.items()}

    proprios = _proprios(repositorios)
    datas_ativas = {d.date() for d in (_data(e.get("created_at")) for e in eventos) if d}

    return {
        "usuario": usuario,
        "nome": perfil.get("name") or usuario,
        "avatar": perfil.get("avatar_url"),
        "gerado_em": referencia.isoformat(timespec="seconds"),
        "semente": semente_do_usuario(usuario),
        "tracos": arredondados,
        "rotulos": ROTULOS,
        "linguagens": ranking_de_linguagens(repositorios),
        "estatisticas": {
            "repositorios_publicos": int(perfil.get("public_repos") or len(repositorios)),
            "repositorios_proprios": len(proprios),
            "forks": len(repositorios) - len(proprios),
            "estrelas_recebidas": sum(
                int(repo.get("stargazers_count") or 0) for repo in proprios
            ),
            "seguidores": int(perfil.get("followers") or 0),
            "eventos_analisados": len(eventos),
            "dias_ativos": len(datas_ativas),
        },
    }
