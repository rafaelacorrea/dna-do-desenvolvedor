# DNA do Desenvolvedor

O perfil publico de alguem no GitHub transformado em uma helice 3D que da para
girar com o mouse. Nao e um dashboard e nao tem grafico: o algoritmo le os
repositorios e a atividade recente da pessoa, calcula seis tracos e usa esses
tracos para construir uma estrutura procedural unica.

Duas pessoas nunca geram a mesma helice. A mesma pessoa gera sempre a mesma.

Um coletor em Python (evolucao do projeto
[github-user-activity](https://github.com/rafaelacorrea/github-user-activity))
busca os dados e grava um JSON; uma cena em Three.js le esse JSON e monta a
estrutura.

## Sumario

- [Demonstracao](#demonstracao)
- [A ideia](#a-ideia)
- [Como o perfil vira geometria](#como-o-perfil-vira-geometria)
- [Requisitos](#requisitos)
- [Como usar](#como-usar)
- [O algoritmo](#o-algoritmo)
- [Formato do JSON](#formato-do-json)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Arquitetura](#arquitetura)
- [Publicando no GitHub Pages](#publicando-no-github-pages)
- [Testes](#testes)
- [Decisoes de implementacao](#decisoes-de-implementacao)
- [Licenca](#licenca)

## Demonstracao

![DNA do desenvolvedor girando na tela](docs/demonstracao.gif)

A gravacao mostra o DNA de dois perfis reais: primeiro o giro livre da helice,
depois os eixos ligados e, no fim, a troca para outro usuario. Repare como a
estrutura muda por completo entre um perfil e outro.

## A ideia

Seis tracos, organizados em tres eixos de polos opostos:

```
                 OPEN SOURCE
                      |
                      |
       BACKEND -------+------- FRONTEND
                      |
                      |
                  ATIVIDADE

        CONSISTENCIA --+-- EXPERIMENTAL
             (eixo de profundidade)
```

Um perfil como

```
Backend       92%
Open Source   61%
Consistencia  74%
Experimental  88%
```

nao vira uma lista de barras: vira uma fita azul grossa, um halo medio de
particulas, degraus em ritmo regular e uma torcao acentuada. Os numeros
continuam la, no painel lateral, mas quem conta a historia e a forma.

## Como o perfil vira geometria

| Traco            | O que muda na cena                                                |
| ---------------- | ----------------------------------------------------------------- |
| **Atividade**    | Altura da estrutura e quantidade de pares de bases (34 a 80)      |
| **Frontend**     | Raio da helice: quanto mais frontend, mais aberta                 |
| **Backend**      | Espessura da fita azul; o frontend engrossa a fita laranja        |
| **Experimental** | Numero de voltas e o ruido aplicado a cada degrau                 |
| **Consistencia** | Regularidade do espacamento vertical entre os degraus             |
| **Open Source**  | Densidade do halo de particulas e o tamanho das bases             |

Alem disso, cada degrau recebe uma linguagem sorteada com o peso que ela tem no
perfil, usando a cor daquela linguagem. Uma pessoa que so escreve C tem uma
helice cinza uniforme; uma poliglota tem degraus de cores diferentes a cada
volta.

Nada disso e aleatorio de verdade. A semente do gerador vem de um hash do nome
de usuario, calculado em Python e gravado no JSON, entao o resultado e sempre o
mesmo em qualquer maquina.

## Requisitos

- Python 3.10 ou superior para o coletor.
- Um navegador com WebGL para a cena.
- Acesso a internet para falar com `https://api.github.com`.
- Nenhuma dependencia externa em Python: tudo vem da biblioteca padrao
  (`urllib`, `json`, `hashlib`, `math`, `statistics`, `colorsys`).
- No navegador, o Three.js e carregado do CDN jsDelivr, na versao 0.160.0.

## Como usar

Sao dois passos: gerar o JSON e abrir a cena.

### 1. Gerar o DNA

```bash
python dna_cli.py rafaelacorrea
```

```
DNA do desenvolvedor: rafaelacorrea

  Backend       [##########..............]  42%
  Frontend      [##############..........]  58%
  Open Source   [#########...............]  39%
  Atividade     [##################......]  76%
  Consistencia  [##################......]  76%
  Experimental  [###############.........]  64%

Linguagens: Elixir 25.8%, HTML 17.5%, CSS 15.5%, JavaScript 14.0%, Python 11.6%, TypeScript 11.0%

Base de calculo: 40 repositorios proprios, 16 forks, 9 estrelas, 34 eventos recentes em 3 dias distintos.
Semente da estrutura: 2530147054

Arquivo gravado em web\dados\rafaelacorrea.json
```

Opcoes:

| Opcao        | O que faz                                                       |
| ------------ | --------------------------------------------------------------- |
| `--saida`    | Grava o JSON em outro caminho (padrao: `web/dados/<usuario>.json`) |
| `--so-texto` | Apenas mostra o resultado no terminal, sem gravar arquivo        |
| `--token`    | Token do GitHub para aumentar o limite de requisicoes           |

Sem autenticacao, a API do GitHub permite cerca de 60 requisicoes por hora por
IP, e cada execucao gasta de tres a cinco. Com um token o limite sobe para 5000:

```bash
python dna_cli.py rafaelacorrea --token ghp_seu_token_aqui
```

```powershell
$env:GITHUB_TOKEN = "ghp_seu_token_aqui"
python dna_cli.py rafaelacorrea
```

### 2. Abrir a cena

A cena precisa ser servida por HTTP (os modulos JavaScript nao carregam a
partir de `file://`):

```bash
python -m http.server --directory web 8000
```

Depois abra `http://localhost:8000/?usuario=rafaelacorrea`.

Na tela:

- **arrastar** gira a estrutura;
- **rolar** aproxima e afasta;
- o campo **usuario** troca de perfil, contanto que o JSON dele ja tenha sido
  gerado;
- o interruptor **mostrar eixos** revela o diagrama dos tres eixos em 3D, com
  um marcador na posicao exata do perfil em cada um deles.

Ja vem com tres perfis prontos em `web/dados`: `rafaelacorrea`, `franknfjr` e
`torvalds` (util para ver um extremo: 100% backend e 80% open source).

## O algoritmo

Todos os tracos vao de 0 a 100 e saem de tres chamadas a API publica: o perfil,
a lista de repositorios e os eventos recentes.

**Backend e Frontend.** Cada repositorio proprio entra com um peso de
`1 + log10(1 + tamanho)`, o que faz projetos grandes contarem mais sem que um
monorepo apague todo o resto. As linguagens sao classificadas em backend,
frontend ou outros (a lista esta em `dna/linguagens.py`), e os dois lados
dividem 100 pontos entre si. Forks nao contam: eles nao sao codigo da pessoa.

**Open Source.** Media ponderada de estrelas recebidas (35%), forks recebidos
(25%), seguidores (20%) e a fatia dos eventos recentes que aconteceram em
repositorios de outras pessoas (20%). As tres primeiras usam escala
logaritmica, entao sair de 0 para 10 estrelas vale muito mais do que sair de
1000 para 1010.

**Atividade.** Volume de eventos publicos recentes (60%) combinado com a
quantidade de repositorios que receberam push nos ultimos 90 dias (40%).

**Consistencia.** Mede ritmo, nao volume. Sessenta por cento vem da cobertura
(quantos dias do periodo observado tiveram alguma atividade) e quarenta por
cento da regularidade dos intervalos entre um dia ativo e outro. Quem trabalha
um pouco todo dia pontua alto; quem faz vinte commits em um sabado e some por
dois meses pontua baixo.

**Experimental.** Diversidade de linguagens medida pela entropia de Shannon
(50%), fatia de repositorios criados no ultimo ano (30%) e fatia de
repositorios pequenos, que costumam ser testes e provas de conceito (20%).

Vale dizer o que esses numeros nao sao: eles descrevem o que esta publico no
GitHub, nao a qualidade nem o tamanho do trabalho de ninguem. Codigo privado,
trabalho em outra plataforma e contribuicoes sem commit simplesmente nao
aparecem na API.

## Formato do JSON

```json
{
  "usuario": "rafaelacorrea",
  "nome": "Rafaela Correa",
  "gerado_em": "2026-09-09T23:31:00+00:00",
  "semente": 2530147054,
  "tracos": {
    "backend": 42,
    "frontend": 58,
    "open_source": 39,
    "atividade": 76,
    "consistencia": 76,
    "experimental": 64
  },
  "rotulos": { "backend": "Backend", "open_source": "Open Source" },
  "linguagens": [
    { "nome": "Elixir", "percentual": 25.8, "grupo": "backend", "cor": "#8c5ea1" }
  ],
  "estatisticas": {
    "repositorios_proprios": 40,
    "forks": 16,
    "estrelas_recebidas": 9,
    "seguidores": 32,
    "eventos_analisados": 34,
    "dias_ativos": 3
  }
}
```

O front-end nao recalcula nada: ele so desenha o que esta nesse arquivo. Isso
mantem o algoritmo em um lugar so.

## Estrutura do projeto

```
dna-do-desenvolvedor/
  dna_cli.py                 Executavel: chama dna.cli.main
  dna/
    __init__.py              Exporta os componentes publicos do pacote
    github.py                Chamadas a API publica do GitHub
    linguagens.py            Classificacao e cores das linguagens
    tracos.py                O algoritmo: perfil -> seis tracos
    cli.py                   Argumentos, resumo em texto e gravacao do JSON
  web/
    index.html               Pagina da cena
    estilo.css               Interface sobreposta
    js/
      principal.js           Montagem da cena, camera, bloom e interface
      helice.js              Construcao procedural da helice
      eixos.js               Diagrama dos tres eixos em 3D
      aleatorio.js           Gerador pseudoaleatorio com semente
      painel.js              Painel de tracos, linguagens e estatisticas
    dados/                   JSONs gerados pelo CLI
  testes/
    test_tracos.py           Testes do algoritmo
    test_linguagens.py       Testes da classificacao e das cores
    test_github.py           Testes do cliente, com a API simulada
    test_cli.py              Testes da linha de comando
  docs/
    demonstracao.gif         Demonstracao usada no README
  .gitignore
  README.md
```

## Arquitetura

```
dna_cli.py -> dna/cli.py -> dna/github.py -> api.github.com
                   |
              dna/tracos.py -> dna/linguagens.py
                   |
                   v
          web/dados/<usuario>.json
                   |
                   v
  web/js/principal.js -> helice.js -> aleatorio.js
                      -> eixos.js
                      -> painel.js
```

O ponto importante e a fronteira do JSON. Tudo que e decisao (o que conta como
backend, quanto vale uma estrela, o que e ser consistente) fica em Python, com
testes. Tudo que e desenho fica em JavaScript. A cena nunca chama a API do
GitHub e nunca recalcula um traco.

`dna/github.py` nasceu do cliente escrito no projeto `github-user-activity`.
Ele ganhou aqui a busca de perfil e a de repositorios com paginacao, mas manteve
a mesma estrutura: so `urllib`, e cada falha HTTP virando uma excecao com
mensagem em portugues.

## Publicando no GitHub Pages

A pasta `web` e um site estatico comum. Com o Pages ligado na raiz da branch
`main`, a cena fica em:

```
https://<usuario>.github.io/dna-do-desenvolvedor/web/?usuario=rafaelacorrea
```

Como o JSON e um arquivo do repositorio, qualquer perfil que voce quiser deixar
disponivel precisa ser gerado e commitado antes:

```bash
python dna_cli.py alguem
git add web/dados/alguem.json
git commit -m "feat: adiciona o dna de alguem"
```

## Testes

A suite usa `unittest`, da biblioteca padrao. Nenhum teste acessa a internet:
as respostas HTTP sao simuladas com `unittest.mock`.

```bash
python -m unittest discover -s testes -t .
```

Sao 53 testes cobrindo as normalizacoes, cada um dos seis tracos, a
estabilidade da semente, a classificacao e as cores das linguagens, a paginacao
do cliente, todos os caminhos de erro da API e a linha de comando.

## Decisoes de implementacao

- **O algoritmo mora em um lugar so.** Seria facil recalcular tudo em
  JavaScript e deixar a pagina buscar a API sozinha, mas ai existiriam duas
  versoes da mesma regra para manter em sincronia. O JSON e a fronteira.
- **Semente derivada do nome.** Uma estrutura procedural que muda a cada
  recarga seria bonita e inutil: nao daria para reconhecer o proprio DNA. O
  hash do nome de usuario garante o oposto.
- **Escalas logaritmicas.** Sem elas, um unico projeto com dez mil estrelas
  levaria qualquer perfil a 100% em open source e achataria todo mundo em zero.
- **Tres eixos, seis polos.** Backend e frontend sao dois lados da mesma
  medida, entao dividem 100 pontos. Ja consistencia e experimental sao
  independentes: da para ser as duas coisas ao mesmo tempo, e o eixo serve
  apenas como referencia visual.
- **Sem emoji e sem framework.** Nem no codigo, nem na interface, nem nos
  commits. A cena e Three.js puro, sem bundler e sem etapa de build.

## Licenca

Distribuido sob a licenca MIT. Veja o arquivo [LICENSE](LICENSE).
