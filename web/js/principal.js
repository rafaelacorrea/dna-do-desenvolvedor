/**
 * Montagem da cena e ligacao com a interface.
 *
 * O fluxo e curto: carrega o indice dos DNAs ja gerados, monta o perfil em
 * foco a partir do JSON dele e espalha os demais em uma galeria ao fundo.
 * Clicar em uma das estruturas de tras traz aquele perfil para o centro.
 */

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

import { construirHelice, descartar } from "./helice.js";
import { construirEixos } from "./eixos.js";
import { animarGaleria, construirGaleria, destacar, miniaturaSob } from "./galeria.js";
import { atualizarPainel, avisar } from "./painel.js";

const USUARIO_PADRAO = "rafaelacorrea";
const FUNDO = 0x05070d;
const TOLERANCIA_DE_CLIQUE = 6;

const tela = document.getElementById("cena");
const cena = new THREE.Scene();
cena.background = new THREE.Color(FUNDO);
cena.fog = new THREE.FogExp2(FUNDO, 0.014);

const camera = new THREE.PerspectiveCamera(
  46,
  window.innerWidth / window.innerHeight,
  0.1,
  200,
);
camera.position.set(0, 3.4, 24);

const renderizador = new THREE.WebGLRenderer({
  canvas: tela,
  antialias: true,
  powerPreference: "high-performance",
});
renderizador.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderizador.setSize(window.innerWidth, window.innerHeight);
renderizador.toneMapping = THREE.ACESFilmicToneMapping;
renderizador.toneMappingExposure = 1.05;

const controles = new OrbitControls(camera, renderizador.domElement);
controles.enableDamping = true;
controles.dampingFactor = 0.06;
controles.minDistance = 9;
controles.maxDistance = 70;
controles.autoRotate = true;
controles.autoRotateSpeed = 0.55;
controles.target.set(0, 0, 0);

// Iluminacao discreta: o brilho vem principalmente do material emissivo e do
// bloom, as luzes servem para dar volume as fitas.
cena.add(new THREE.AmbientLight(0xffffff, 0.55));
const luzFria = new THREE.PointLight(0x58a6ff, 220, 90);
luzFria.position.set(-12, 14, 10);
cena.add(luzFria);
const luzQuente = new THREE.PointLight(0xf0883e, 180, 90);
luzQuente.position.set(14, -12, -8);
cena.add(luzQuente);

const composicao = new EffectComposer(renderizador);
composicao.addPass(new RenderPass(cena, camera));
composicao.addPass(
  new UnrealBloomPass(
    new THREE.Vector2(window.innerWidth, window.innerHeight),
    0.62,
    0.75,
    0.32,
  ),
);
composicao.addPass(new OutputPass());

const raio = new THREE.Raycaster();
const ponteiro = new THREE.Vector2(-2, -2);

let helice = null;
let eixos = null;
let galeria = null;
let indice = [];
let destaque = null;
let transicao = null;
let enquadramentoPadrao = {
  posicao: camera.position.clone(),
  alvo: new THREE.Vector3(),
};

/**
 * Remove a estrutura atual da cena e libera a memoria de GPU.
 */
function limparCena() {
  for (const objeto of [helice, eixos, galeria]) {
    if (objeto) {
      cena.remove(objeto);
      descartar(objeto);
    }
  }
  helice = null;
  eixos = null;
  galeria = null;
  destaque = null;
}

/**
 * Constroi a estrutura 3D de um DNA, a galeria de fundo e o painel.
 *
 * @param {object} dna Conteudo do JSON do perfil.
 * @param {boolean} manterCamera Deixa a camera onde esta, para que a
 *   transicao do clique termine o movimento no lugar de um salto.
 */
function montar(dna, manterCamera = false) {
  limparCena();

  const construida = construirHelice(dna);
  helice = construida.grupo;
  cena.add(helice);

  eixos = construirEixos(dna, Math.min(construida.config.altura * 0.45, 10));
  eixos.visible = document.getElementById("mostrar-eixos").checked;
  cena.add(eixos);

  galeria = construirGaleria(indice, dna.usuario, construida.config.altura * 0.6);
  cena.add(galeria);

  enquadramentoPadrao = {
    posicao: new THREE.Vector3(
      0,
      construida.config.altura * 0.12,
      construida.config.altura * 1.35,
    ),
    alvo: new THREE.Vector3(0, 0, 0),
  };

  if (!manterCamera) {
    camera.position.copy(enquadramentoPadrao.posicao);
    controles.target.copy(enquadramentoPadrao.alvo);
    controles.update();
  }

  atualizarPainel(dna);
}

/**
 * Move a camera suavemente ate uma posicao e um alvo.
 *
 * @param {THREE.Vector3} posicao
 * @param {THREE.Vector3} alvo
 * @param {number} duracao Em milissegundos.
 * @returns {Promise<void>}
 */
function irAte(posicao, alvo, duracao) {
  return new Promise((concluir) => {
    controles.enabled = false;
    transicao = {
      inicio: performance.now(),
      duracao,
      posicaoInicial: camera.position.clone(),
      alvoInicial: controles.target.clone(),
      posicaoFinal: posicao.clone(),
      alvoFinal: alvo.clone(),
      concluir,
    };
  });
}

/**
 * Avanca a transicao de camera em curso, se houver.
 */
function atualizarTransicao() {
  if (!transicao) {
    return;
  }

  const passado = performance.now() - transicao.inicio;
  const bruto = Math.min(passado / transicao.duracao, 1);
  // Suavizacao nas duas pontas: sai devagar, acelera no meio, freia no fim.
  const suave = bruto < 0.5 ? 4 * bruto ** 3 : 1 - (-2 * bruto + 2) ** 3 / 2;

  camera.position.lerpVectors(transicao.posicaoInicial, transicao.posicaoFinal, suave);
  controles.target.lerpVectors(transicao.alvoInicial, transicao.alvoFinal, suave);

  if (bruto >= 1) {
    const concluir = transicao.concluir;
    transicao = null;
    controles.enabled = true;
    concluir();
  }
}

/**
 * Voa ate uma miniatura da galeria e a traz para o centro da cena.
 * @param {THREE.Object3D} miniatura
 */
async function focar(miniatura) {
  const usuario = miniatura.userData.entrada.usuario;
  const destino = new THREE.Vector3();
  miniatura.getWorldPosition(destino);

  const aproximacao = destino
    .clone()
    .add(destino.clone().normalize().multiplyScalar(7));
  aproximacao.y = destino.y + 2;

  const girava = controles.autoRotate;
  controles.autoRotate = false;
  destacar(galeria, null);
  destaque = null;

  await irAte(aproximacao, destino, 750);
  const carregou = await carregar(usuario, true);

  if (carregou) {
    await irAte(enquadramentoPadrao.posicao, enquadramentoPadrao.alvo, 900);
  }
  controles.autoRotate = girava;
}

/**
 * Busca o JSON de um usuario na pasta `dados` e monta a cena.
 *
 * @param {string} usuario
 * @param {boolean} manterCamera
 * @returns {Promise<boolean>} Se o perfil foi carregado.
 */
async function carregar(usuario, manterCamera = false) {
  const nome = (usuario || "").trim();
  if (!nome) {
    return false;
  }

  document.body.classList.add("carregando");
  avisar("");

  try {
    const resposta = await fetch(`dados/${encodeURIComponent(nome)}.json`, {
      cache: "no-store",
    });
    if (!resposta.ok) {
      throw new Error("arquivo nao encontrado");
    }
    montar(await resposta.json(), manterCamera);
    document.getElementById("usuario").value = nome;

    const url = new URL(window.location.href);
    url.searchParams.set("usuario", nome);
    window.history.replaceState({}, "", url);
    return true;
  } catch (erro) {
    avisar(
      `Nenhum DNA gerado para "${nome}". Rode no terminal: python dna_cli.py ${nome}`,
    );
    return false;
  } finally {
    document.body.classList.remove("carregando");
  }
}

/**
 * Le a lista de DNAs ja gerados. A ausencia do indice nao e um erro: a cena
 * continua funcionando, so fica sem a galeria de fundo.
 */
async function carregarIndice() {
  try {
    const resposta = await fetch("dados/index.json", { cache: "no-store" });
    indice = resposta.ok ? await resposta.json() : [];
  } catch (erro) {
    indice = [];
  }
}

document.getElementById("busca").addEventListener("submit", (evento) => {
  evento.preventDefault();
  carregar(document.getElementById("usuario").value);
});

document.getElementById("mostrar-eixos").addEventListener("change", (evento) => {
  if (eixos) {
    eixos.visible = evento.target.checked;
  }
});

tela.addEventListener("pointermove", (evento) => {
  ponteiro.x = (evento.clientX / window.innerWidth) * 2 - 1;
  ponteiro.y = -(evento.clientY / window.innerHeight) * 2 + 1;
});

// Arrastar para girar nao pode virar clique: so conta como clique se o
// ponteiro praticamente nao andou entre apertar e soltar.
let inicioDoPonteiro = null;

tela.addEventListener("pointerdown", (evento) => {
  inicioDoPonteiro = { x: evento.clientX, y: evento.clientY };
});

tela.addEventListener("pointerup", (evento) => {
  const inicio = inicioDoPonteiro;
  inicioDoPonteiro = null;

  if (!inicio || !destaque || transicao) {
    return;
  }
  const andou = Math.hypot(evento.clientX - inicio.x, evento.clientY - inicio.y);
  if (andou <= TOLERANCIA_DE_CLIQUE) {
    focar(destaque);
  }
});

window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderizador.setSize(window.innerWidth, window.innerHeight);
  composicao.setSize(window.innerWidth, window.innerHeight);
});

const relogio = new THREE.Clock();

function animar() {
  requestAnimationFrame(animar);
  const tempo = relogio.getElapsedTime();

  if (helice) {
    // Respiracao lenta: a helice sobe e desce alguns centimetros, o que da
    // vida a cena sem competir com o giro do usuario.
    helice.position.y = Math.sin(tempo * 0.5) * 0.25;
  }
  animarGaleria(galeria, tempo, camera);

  if (!transicao) {
    raio.setFromCamera(ponteiro, camera);
    const sob = miniaturaSob(raio, galeria);
    if (sob !== destaque) {
      destaque = sob;
      destacar(galeria, destaque);
      tela.style.cursor = destaque ? "pointer" : "default";
    }
  }

  atualizarTransicao();
  controles.update();
  composicao.render();
}

const parametrosDaUrl = new URLSearchParams(window.location.search);
const inicial = parametrosDaUrl.get("usuario") || USUARIO_PADRAO;
document.getElementById("usuario").value = inicial;

animar();
carregarIndice().then(() => carregar(inicial));
