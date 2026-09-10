/**
 * Painel de texto sobreposto a cena.
 *
 * Mostra os seis tracos, a mistura de linguagens e a base de calculo. E o
 * complemento textual da helice, nao um grafico: as barras finas servem so
 * para dar escala aos numeros.
 */

const ORDEM = [
  "backend",
  "frontend",
  "open_source",
  "atividade",
  "consistencia",
  "experimental",
];

const CORES_DOS_TRACOS = {
  backend: "#58a6ff",
  frontend: "#f0883e",
  open_source: "#7ee787",
  atividade: "#d2a8ff",
  consistencia: "#79c0ff",
  experimental: "#ffa198",
};

const NOMES_DAS_ESTATISTICAS = {
  repositorios_proprios: "repositorios proprios",
  forks: "forks",
  estrelas_recebidas: "estrelas recebidas",
  seguidores: "seguidores",
  eventos_analisados: "eventos analisados",
  dias_ativos: "dias com atividade",
};

/**
 * Preenche a lista de tracos com barras animadas.
 * @param {HTMLElement} alvo
 * @param {object} dna
 */
function desenharTracos(alvo, dna) {
  alvo.replaceChildren();
  const rotulos = dna.rotulos || {};

  for (const nome of ORDEM) {
    const valor = dna.tracos[nome];
    if (valor === undefined) {
      continue;
    }

    const item = document.createElement("li");

    const topo = document.createElement("div");
    topo.className = "traco-topo";

    const titulo = document.createElement("span");
    titulo.className = "traco-nome";
    titulo.textContent = rotulos[nome] || nome;

    const numero = document.createElement("span");
    numero.className = "traco-valor";
    numero.textContent = `${valor}%`;

    topo.append(titulo, numero);

    const trilho = document.createElement("div");
    trilho.className = "traco-trilho";

    const preenchimento = document.createElement("div");
    preenchimento.className = "traco-preenchimento";
    preenchimento.style.background = CORES_DOS_TRACOS[nome] || "#8b949e";
    preenchimento.style.transform = "scaleX(0)";
    trilho.append(preenchimento);

    item.append(topo, trilho);
    alvo.append(item);

    // A animacao so comeca depois que o elemento entra na pagina.
    requestAnimationFrame(() => {
      preenchimento.style.transform = `scaleX(${valor / 100})`;
    });
  }
}

/**
 * Preenche a legenda de linguagens com as cores usadas na helice.
 * @param {HTMLElement} alvo
 * @param {object} dna
 */
function desenharLinguagens(alvo, dna) {
  alvo.replaceChildren();
  const idiomas = dna.linguagens || [];
  if (idiomas.length === 0) {
    alvo.hidden = true;
    return;
  }
  alvo.hidden = false;

  for (const idioma of idiomas) {
    const item = document.createElement("span");
    item.className = "linguagem";

    const ponto = document.createElement("span");
    ponto.className = "ponto";
    ponto.style.background = idioma.cor;

    const texto = document.createElement("span");
    texto.textContent = `${idioma.nome} ${idioma.percentual}%`;

    item.append(ponto, texto);
    alvo.append(item);
  }
}

/**
 * Preenche a lista com os numeros que originaram os tracos.
 * @param {HTMLElement} alvo
 * @param {object} dna
 */
function desenharEstatisticas(alvo, dna) {
  alvo.replaceChildren();
  const estatisticas = dna.estatisticas || {};

  for (const [chave, rotulo] of Object.entries(NOMES_DAS_ESTATISTICAS)) {
    if (estatisticas[chave] === undefined) {
      continue;
    }
    const termo = document.createElement("dt");
    termo.textContent = rotulo;
    const valor = document.createElement("dd");
    valor.textContent = estatisticas[chave];
    alvo.append(termo, valor);
  }
}

/**
 * Atualiza todo o painel com um novo DNA.
 * @param {object} dna
 */
export function atualizarPainel(dna) {
  document.getElementById("titulo").textContent = dna.nome || dna.usuario;
  document.title = `DNA do Desenvolvedor - ${dna.usuario}`;
  desenharTracos(document.getElementById("tracos"), dna);
  desenharLinguagens(document.getElementById("linguagens"), dna);
  desenharEstatisticas(document.getElementById("estatisticas"), dna);
}

/**
 * Mostra ou esconde a faixa de aviso.
 *
 * @param {string} mensagem Texto do aviso; vazio esconde a faixa.
 * @param {"erro" | "espera"} tipo Muda a cor: vermelho para falha, neutro
 *   para o aviso de que a coleta esta em andamento.
 */
export function avisar(mensagem, tipo = "erro") {
  const aviso = document.getElementById("aviso");
  aviso.textContent = mensagem;
  aviso.dataset.tipo = tipo;
  aviso.hidden = !mensagem;
}
