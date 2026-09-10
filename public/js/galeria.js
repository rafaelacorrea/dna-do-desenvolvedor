/**
 * A galeria: os DNAs ja gerados flutuando atras do principal.
 *
 * Cada perfil do `dados/index.json` vira uma versao reduzida da propria
 * helice - so as duas fitas, sem degraus e sem particulas - alinhada em um
 * plano atras do DNA em foco. Passar o mouse acende a estrutura e o nome;
 * clicar traz aquele perfil para o centro.
 *
 * O plano acompanha a camera: a cada quadro o grupo inteiro gira para
 * continuar atras do que se esta olhando. Assim a galeria nunca passa na
 * frente do DNA principal, mesmo com a cena girando sozinha.
 *
 * A simplificacao nao e enfeite: uma helice completa passa de duzentas malhas,
 * e quinze delas na cena derrubariam a taxa de quadros. Reduzida, cada uma tem
 * duas.
 */

import * as THREE from "three";

import { criarAleatorio } from "./aleatorio.js";
import { esqueleto, parametros } from "./helice.js";

const COR_BACKEND = new THREE.Color("#58a6ff");
const COR_FRONTEND = new THREE.Color("#f0883e");

const ESCALA = 0.34;
const OPACIDADE_PARADA = 0.42;
const OPACIDADE_ACESA = 0.95;

/**
 * Desenha o nome do perfil em um sprite de tamanho fixo na tela.
 * @param {string} texto
 */
function criarNome(texto) {
  const escala = 4;
  const fonte = 30;
  const canvas = document.createElement("canvas");
  const contexto = canvas.getContext("2d");

  contexto.font = `500 ${fonte}px Inter, Segoe UI, system-ui, sans-serif`;
  const largura = Math.ceil(contexto.measureText(texto).width) + 20;
  canvas.width = largura * escala;
  canvas.height = (fonte + 16) * escala;

  contexto.scale(escala, escala);
  contexto.font = `500 ${fonte}px Inter, Segoe UI, system-ui, sans-serif`;
  contexto.fillStyle = "#c9d1d9";
  contexto.textAlign = "center";
  contexto.textBaseline = "middle";
  contexto.fillText(texto, largura / 2, (fonte + 16) / 2);

  const material = new THREE.SpriteMaterial({
    map: new THREE.CanvasTexture(canvas),
    transparent: true,
    depthWrite: false,
    sizeAttenuation: false,
    opacity: OPACIDADE_PARADA,
  });

  const sprite = new THREE.Sprite(material);
  sprite.scale.set((canvas.width / canvas.height) * 0.034, 0.034, 1);
  return sprite;
}

/**
 * Monta a versao reduzida da helice de um perfil do indice.
 * @param {object} entrada Registro do `index.json`.
 */
function construirMiniatura(entrada) {
  const config = parametros(entrada.tracos);
  const aleatorio = criarAleatorio(entrada.semente || 1);
  const degraus = esqueleto(config, aleatorio);

  const grupo = new THREE.Group();
  const lados = [
    { pontos: degraus.map((d) => d.esquerda), cor: COR_BACKEND, peso: entrada.tracos.backend },
    { pontos: degraus.map((d) => d.direita), cor: COR_FRONTEND, peso: entrada.tracos.frontend },
  ];

  for (const lado of lados) {
    const curva = new THREE.CatmullRomCurve3(lado.pontos);
    const geometria = new THREE.TubeGeometry(
      curva,
      56,
      config.espessuraFita * (0.55 + (lado.peso / 100) * 0.9) * 1.6,
      6,
      false,
    );
    const material = new THREE.MeshBasicMaterial({
      color: lado.cor,
      transparent: true,
      opacity: OPACIDADE_PARADA,
      depthWrite: false,
    });
    grupo.add(new THREE.Mesh(geometria, material));
  }

  const nome = criarNome(entrada.usuario);
  nome.position.set(0, -config.altura / 2 - 1.4, 0);
  grupo.add(nome);

  // Cilindro invisivel apenas para o clique: acertar uma fita de poucos pixels
  // seria frustrante, entao a area sensivel envolve a estrutura inteira.
  const area = new THREE.Mesh(
    new THREE.CylinderGeometry(config.raio * 1.6, config.raio * 1.6, config.altura, 8, 1, true),
    new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false }),
  );
  area.userData.area = true;
  grupo.add(area);

  grupo.scale.setScalar(ESCALA);
  grupo.userData = { entrada, nome, fitas: grupo.children.slice(0, 2) };
  return grupo;
}

/**
 * Monta a galeria inteira, distribuida em um circulo ao redor do centro.
 *
 * @param {Array<object>} indice Conteudo do `dados/index.json`.
 * @param {string} usuarioAtual Perfil em foco, que fica de fora da galeria.
 * @param {number} raio Distancia do centro da cena.
 * @returns {THREE.Group}
 */
export function construirGaleria(indice, usuarioAtual, distancia) {
  const grupo = new THREE.Group();
  const outros = (indice || []).filter(
    (entrada) => entrada.usuario.toLowerCase() !== (usuarioAtual || "").toLowerCase(),
  );

  const vaoCentral = distancia * 0.72;
  const passo = distancia * 0.62;

  outros.forEach((entrada, posicao) => {
    const miniatura = construirMiniatura(entrada);

    // As miniaturas crescem para os lados a partir de um vao no meio: o
    // centro do plano fica livre, senao uma delas ficaria escondida
    // exatamente atras do DNA em foco.
    const lado = posicao % 2 === 0 ? -1 : 1;
    const nivel = Math.floor(posicao / 2);

    miniatura.position.set(
      lado * (vaoCentral + nivel * passo),
      (nivel % 2 === 0 ? 1 : -1) * lado * distancia * 0.13,
      -distancia - nivel * distancia * 0.3,
    );
    miniatura.userData.alturaBase = miniatura.position.y;
    grupo.add(miniatura);
  });

  return grupo;
}

/**
 * Mantem o plano atras da camera e gira as miniaturas, cada uma no seu ritmo.
 *
 * @param {THREE.Group} galeria
 * @param {number} tempo Segundos desde o inicio da cena.
 * @param {THREE.Camera} camera
 */
export function animarGaleria(galeria, tempo, camera) {
  if (!galeria) {
    return;
  }

  // Girar o grupo pelo azimute da camera faz o eixo -Z local apontar sempre
  // para o lado oposto de quem observa, que e onde a galeria deve ficar.
  galeria.rotation.y = Math.atan2(camera.position.x, camera.position.z);

  galeria.children.forEach((miniatura, posicao) => {
    miniatura.rotation.y = tempo * (0.12 + posicao * 0.015);
    // A altura oscila em torno da base, e nao a partir da posicao anterior:
    // somar a cada quadro faria as miniaturas subirem para sempre.
    miniatura.position.y =
      miniatura.userData.alturaBase + Math.sin(tempo * 0.4 + posicao) * 0.18;
  });
}

/**
 * Acende a miniatura sob o cursor e apaga as demais.
 *
 * @param {THREE.Group} galeria
 * @param {THREE.Object3D | null} alvo Miniatura destacada, ou null.
 */
export function destacar(galeria, alvo) {
  if (!galeria) {
    return;
  }
  for (const miniatura of galeria.children) {
    const aceso = miniatura === alvo;
    const opacidade = aceso ? OPACIDADE_ACESA : OPACIDADE_PARADA;
    for (const fita of miniatura.userData.fitas) {
      fita.material.opacity = opacidade;
    }
    miniatura.userData.nome.material.opacity = aceso ? 1 : OPACIDADE_PARADA;
    miniatura.scale.setScalar(aceso ? ESCALA * 1.12 : ESCALA);
  }
}

/**
 * Descobre qual miniatura esta sob o cursor.
 *
 * @param {THREE.Raycaster} raio
 * @param {THREE.Group} galeria
 * @returns {THREE.Object3D | null}
 */
export function miniaturaSob(raio, galeria) {
  if (!galeria) {
    return null;
  }
  const areas = galeria.children
    .map((miniatura) => miniatura.children.find((filho) => filho.userData.area))
    .filter(Boolean);

  const encontrados = raio.intersectObjects(areas, false);
  return encontrados.length > 0 ? encontrados[0].object.parent : null;
}
