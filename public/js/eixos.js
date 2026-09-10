/**
 * Os tres eixos do DNA, desenhados por cima da helice.
 *
 *        OPEN SOURCE
 *             |
 *   BACKEND --+-- FRONTEND
 *             |
 *         ATIVIDADE
 *
 * mais o eixo de profundidade CONSISTENCIA -- EXPERIMENTAL.
 *
 * Cada eixo tem um marcador que desliza entre os dois polos conforme os
 * valores do perfil. E um recurso opcional, ligado pelo interruptor da
 * interface: a leitura principal continua sendo a propria helice.
 */

import * as THREE from "three";

const COR_EIXO = "#30363d";
const COR_ROTULO = "#7d8590";

const EIXOS = [
  {
    direcao: new THREE.Vector3(1, 0, 0),
    polos: ["frontend", "backend"],
    cor: "#f0883e",
  },
  {
    direcao: new THREE.Vector3(0, 1, 0),
    polos: ["open_source", "atividade"],
    cor: "#58a6ff",
  },
  {
    direcao: new THREE.Vector3(0, 0, 1),
    polos: ["experimental", "consistencia"],
    cor: "#7ee787",
  },
];

/**
 * Desenha um texto em um canvas e devolve um sprite pronto para a cena.
 * @param {string} texto
 * @param {string} cor
 */
function criarRotulo(texto, cor) {
  const escala = 4;
  const fonte = 32;
  const canvas = document.createElement("canvas");
  const contexto = canvas.getContext("2d");

  contexto.font = `600 ${fonte}px Inter, Segoe UI, system-ui, sans-serif`;
  const largura = Math.ceil(contexto.measureText(texto).width) + 24;
  canvas.width = largura * escala;
  canvas.height = (fonte + 20) * escala;

  contexto.scale(escala, escala);
  contexto.font = `600 ${fonte}px Inter, Segoe UI, system-ui, sans-serif`;
  contexto.fillStyle = cor;
  contexto.textAlign = "center";
  contexto.textBaseline = "middle";
  contexto.fillText(texto, largura / 2, (fonte + 20) / 2);

  const textura = new THREE.CanvasTexture(canvas);
  textura.anisotropy = 4;
  // `sizeAttenuation: false` mantem o rotulo do mesmo tamanho na tela em
  // qualquer distancia: sem isso o eixo de profundidade cresce enormemente
  // quando a sua ponta se aproxima da camera.
  const material = new THREE.SpriteMaterial({
    map: textura,
    transparent: true,
    depthWrite: false,
    depthTest: false,
    sizeAttenuation: false,
    opacity: 0.7,
  });

  const sprite = new THREE.Sprite(material);
  const proporcao = canvas.width / canvas.height;
  sprite.scale.set(proporcao * 0.03, 0.03, 1);
  sprite.renderOrder = 2;
  return sprite;
}

/**
 * Monta o grupo com as tres linhas, os rotulos dos polos e os marcadores.
 *
 * @param {object} dna Conteudo do JSON gerado pelo CLI.
 * @param {number} alcance Metade do comprimento de cada eixo.
 * @returns {THREE.Group}
 */
export function construirEixos(dna, alcance) {
  const grupo = new THREE.Group();
  const rotulos = dna.rotulos || {};

  for (const eixo of EIXOS) {
    const ponta = eixo.direcao.clone().multiplyScalar(alcance);
    const geometria = new THREE.BufferGeometry().setFromPoints([
      ponta.clone().negate(),
      ponta,
    ]);
    grupo.add(
      new THREE.Line(
        geometria,
        new THREE.LineBasicMaterial({ color: COR_EIXO, transparent: true, opacity: 0.85 }),
      ),
    );

    const [positivo, negativo] = eixo.polos;
    const rotuloPositivo = criarRotulo(
      (rotulos[positivo] || positivo).toUpperCase(),
      COR_ROTULO,
    );
    rotuloPositivo.position.copy(ponta).addScaledVector(eixo.direcao, 1.1);
    grupo.add(rotuloPositivo);

    const rotuloNegativo = criarRotulo(
      (rotulos[negativo] || negativo).toUpperCase(),
      COR_ROTULO,
    );
    rotuloNegativo.position.copy(ponta.clone().negate()).addScaledVector(eixo.direcao, -1.1);
    grupo.add(rotuloNegativo);

    // O marcador fica na posicao relativa entre os dois polos: 50/50 no
    // centro, 100/0 encostado na ponta positiva.
    const valorPositivo = dna.tracos[positivo] ?? 50;
    const valorNegativo = dna.tracos[negativo] ?? 50;
    const total = valorPositivo + valorNegativo || 1;
    const posicao = (valorPositivo / total) * 2 - 1;

    const marcador = new THREE.Mesh(
      new THREE.SphereGeometry(0.16, 16, 12),
      new THREE.MeshBasicMaterial({ color: eixo.cor }),
    );
    marcador.position.copy(eixo.direcao).multiplyScalar(posicao * alcance);
    grupo.add(marcador);
  }

  return grupo;
}
