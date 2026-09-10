/**
 * Montagem da cena e ligacao com a interface.
 *
 * O fluxo e curto: carrega o JSON gerado pelo CLI em Python, constroi a
 * helice procedural a partir dele, preenche o painel e deixa a cena girando.
 */

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

import { construirHelice, descartar } from "./helice.js";
import { construirEixos } from "./eixos.js";
import { atualizarPainel, avisar } from "./painel.js";

const USUARIO_PADRAO = "rafaelacorrea";
const FUNDO = 0x05070d;

const tela = document.getElementById("cena");
const cena = new THREE.Scene();
cena.background = new THREE.Color(FUNDO);
cena.fog = new THREE.FogExp2(FUNDO, 0.026);

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
controles.maxDistance = 55;
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
const bloom = new UnrealBloomPass(
  new THREE.Vector2(window.innerWidth, window.innerHeight),
  0.62,
  0.75,
  0.32,
);
composicao.addPass(bloom);
composicao.addPass(new OutputPass());

let helice = null;
let eixos = null;

/**
 * Remove a helice atual da cena e libera a memoria de GPU.
 */
function limparCena() {
  for (const objeto of [helice, eixos]) {
    if (objeto) {
      cena.remove(objeto);
      descartar(objeto);
    }
  }
  helice = null;
  eixos = null;
}

/**
 * Constroi a estrutura 3D de um DNA e coloca na cena.
 * @param {object} dna
 */
function montar(dna) {
  limparCena();

  const construida = construirHelice(dna);
  helice = construida.grupo;
  cena.add(helice);

  eixos = construirEixos(dna, Math.min(construida.config.altura * 0.45, 10));
  eixos.visible = document.getElementById("mostrar-eixos").checked;
  cena.add(eixos);

  const distancia = construida.config.altura * 1.35;
  camera.position.set(0, construida.config.altura * 0.12, distancia);
  controles.maxDistance = distancia * 2.4;
  controles.update();

  atualizarPainel(dna);
}

/**
 * Busca o JSON de um usuario na pasta `dados` e monta a cena.
 * @param {string} usuario
 */
async function carregar(usuario) {
  const nome = (usuario || "").trim();
  if (!nome) {
    return;
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
    const dna = await resposta.json();
    montar(dna);

    const url = new URL(window.location.href);
    url.searchParams.set("usuario", nome);
    window.history.replaceState({}, "", url);
  } catch (erro) {
    avisar(
      `Nenhum DNA gerado para "${nome}". Rode no terminal: python dna_cli.py ${nome}`,
    );
  } finally {
    document.body.classList.remove("carregando");
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

  controles.update();
  composicao.render();
}

const parametrosDaUrl = new URLSearchParams(window.location.search);
const inicial = parametrosDaUrl.get("usuario") || USUARIO_PADRAO;
document.getElementById("usuario").value = inicial;

animar();
carregar(inicial);
