/**
 * Construcao procedural da helice.
 *
 * Cada traco do DNA controla uma propriedade geometrica concreta:
 *
 *   Atividade     -> altura da estrutura e quantidade de pares de bases
 *   Frontend      -> raio da helice (mais frontend, mais aberta)
 *   Backend       -> espessura da fita azul; o frontend engrossa a laranja
 *   Experimental  -> numero de voltas e o ruido aplicado a cada par
 *   Consistencia  -> regularidade do espacamento vertical
 *   Open Source   -> quantidade e alcance das particulas ao redor
 *
 * Nada aqui e aleatorio de verdade: tudo sai da semente calculada a partir do
 * nome de usuario, entao a mesma pessoa gera sempre a mesma estrutura.
 */

import * as THREE from "three";

import { criarAleatorio, entre, sorteadorPonderado } from "./aleatorio.js";

const COR_BACKEND = new THREE.Color("#58a6ff");
const COR_FRONTEND = new THREE.Color("#f0883e");
const COR_NEUTRA = new THREE.Color("#8b949e");

const PARES_MINIMO = 34;
const PARES_EXTRAS = 46;

/**
 * Interpola duas cores sem alterar as originais.
 * @param {THREE.Color} inicio
 * @param {THREE.Color} fim
 * @param {number} fator
 */
function misturar(inicio, fim, fator) {
  return inicio.clone().lerp(fim, THREE.MathUtils.clamp(fator, 0, 1));
}

/**
 * Traduz os tracos do DNA nos parametros geometricos da helice.
 * @param {object} tracos
 */
export function parametros(tracos) {
  const atividade = tracos.atividade / 100;
  const frontend = tracos.frontend / 100;
  const experimental = tracos.experimental / 100;
  const consistencia = tracos.consistencia / 100;

  return {
    pares: Math.round(PARES_MINIMO + atividade * PARES_EXTRAS),
    altura: 15 + atividade * 9,
    raio: 1.35 + frontend * 1.35,
    voltas: 2 + experimental * 4,
    ruido: 0.05 + experimental * 0.35,
    irregularidade: (1 - consistencia) * 0.9,
    particulas: Math.round(220 + (tracos.open_source / 100) * 620),
    espessuraFita: 0.075,
    raioBase: 0.085 + (tracos.open_source / 100) * 0.075,
  };
}

/**
 * Calcula os pontos das duas fitas e dos pares de bases.
 *
 * Exportada porque a galeria do plano de fundo monta versoes reduzidas da
 * helice a partir do mesmo esqueleto.
 *
 * @param {object} config Resultado de `parametros`.
 * @param {() => number} aleatorio
 */
export function esqueleto(config, aleatorio) {
  // O espacamento vertical nasce de incrementos sorteados: quanto menor a
  // consistencia, mais os degraus se afastam de um ritmo regular.
  const incrementos = [];
  for (let i = 0; i < config.pares; i += 1) {
    incrementos.push(1 + (aleatorio() - 0.5) * config.irregularidade);
  }
  const soma = incrementos.reduce((total, valor) => total + valor, 0);

  const degraus = [];
  let percorrido = 0;
  for (let i = 0; i < config.pares; i += 1) {
    const u = percorrido / soma;
    percorrido += incrementos[i];

    const y = -config.altura / 2 + u * config.altura;
    const angulo = u * config.voltas * Math.PI * 2 + (aleatorio() - 0.5) * config.ruido;
    const raio = config.raio * (1 + (aleatorio() - 0.5) * config.ruido * 0.6);

    degraus.push({
      u,
      esquerda: new THREE.Vector3(Math.cos(angulo) * raio, y, Math.sin(angulo) * raio),
      direita: new THREE.Vector3(
        Math.cos(angulo + Math.PI) * raio,
        y,
        Math.sin(angulo + Math.PI) * raio,
      ),
    });
  }
  return degraus;
}

/**
 * Cria um cilindro ligando dois pontos do espaco.
 */
function ligar(inicio, fim, raio, material) {
  const direcao = new THREE.Vector3().subVectors(fim, inicio);
  const comprimento = direcao.length();
  const geometria = new THREE.CylinderGeometry(raio, raio, comprimento, 8, 1, true);
  const malha = new THREE.Mesh(geometria, material);
  malha.position.copy(inicio).addScaledVector(direcao, 0.5);
  malha.quaternion.setFromUnitVectors(
    new THREE.Vector3(0, 1, 0),
    direcao.clone().normalize(),
  );
  return malha;
}

/**
 * Constroi a fita (tubo) que passa por uma sequencia de pontos.
 */
function construirFita(pontos, espessura, cor) {
  const curva = new THREE.CatmullRomCurve3(pontos);
  const geometria = new THREE.TubeGeometry(
    curva,
    Math.max(64, pontos.length * 8),
    espessura,
    12,
    false,
  );
  const material = new THREE.MeshStandardMaterial({
    color: cor,
    emissive: cor.clone().multiplyScalar(0.28),
    roughness: 0.4,
    metalness: 0.2,
  });
  return new THREE.Mesh(geometria, material);
}

/**
 * Nuvem de particulas ao redor da helice: quanto mais open source, mais
 * denso e mais espalhado o halo.
 */
function construirHalo(config, aleatorio, cor) {
  const posicoes = new Float32Array(config.particulas * 3);
  for (let i = 0; i < config.particulas; i += 1) {
    const angulo = aleatorio() * Math.PI * 2;
    const raio = config.raio * entre(aleatorio, 1.4, 4.6);
    const altura = entre(aleatorio, -config.altura * 0.62, config.altura * 0.62);
    posicoes[i * 3] = Math.cos(angulo) * raio;
    posicoes[i * 3 + 1] = altura;
    posicoes[i * 3 + 2] = Math.sin(angulo) * raio;
  }

  const geometria = new THREE.BufferGeometry();
  geometria.setAttribute("position", new THREE.BufferAttribute(posicoes, 3));

  const material = new THREE.PointsMaterial({
    color: cor,
    size: 0.055,
    sizeAttenuation: true,
    transparent: true,
    opacity: 0.7,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  return new THREE.Points(geometria, material);
}

/**
 * Monta a helice completa de um DNA.
 *
 * @param {object} dna Conteudo do JSON gerado pelo CLI em Python.
 * @returns {{ grupo: THREE.Group, config: object, cores: object }}
 */
export function construirHelice(dna) {
  const tracos = dna.tracos;
  const config = parametros(tracos);
  const aleatorio = criarAleatorio(dna.semente || 1);

  // Uma fita e o backend, a outra e o frontend. A cor identifica o lado e a
  // espessura mostra o peso que aquele lado tem no perfil.
  const corFitaA = COR_BACKEND.clone();
  const corFitaB = COR_FRONTEND.clone();
  const espessuraA = config.espessuraFita * (0.55 + (tracos.backend / 100) * 0.9);
  const espessuraB = config.espessuraFita * (0.55 + (tracos.frontend / 100) * 0.9);

  const grupo = new THREE.Group();
  const degraus = esqueleto(config, aleatorio);

  grupo.add(
    construirFita(
      degraus.map((degrau) => degrau.esquerda),
      espessuraA,
      corFitaA,
    ),
  );
  grupo.add(
    construirFita(
      degraus.map((degrau) => degrau.direita),
      espessuraB,
      corFitaB,
    ),
  );

  // Cada par de bases recebe uma linguagem sorteada com o peso que ela tem no
  // perfil: a helice passa a mostrar a mistura de linguagens da pessoa.
  const sortearLinguagem = sorteadorPonderado(
    aleatorio,
    (dna.linguagens || []).map((item) => ({ ...item, peso: item.percentual })),
  );

  const materiais = new Map();
  const materialDe = (corHex) => {
    if (!materiais.has(corHex)) {
      const cor = new THREE.Color(corHex);
      materiais.set(
        corHex,
        new THREE.MeshStandardMaterial({
          color: cor,
          emissive: cor.clone().multiplyScalar(0.32),
          roughness: 0.45,
          metalness: 0.1,
        }),
      );
    }
    return materiais.get(corHex);
  };

  const geometriaBase = new THREE.SphereGeometry(config.raioBase, 14, 12);

  for (const degrau of degraus) {
    const linguagem = sortearLinguagem();
    const material = materialDe(linguagem ? linguagem.cor : COR_NEUTRA.getStyle());

    grupo.add(ligar(degrau.esquerda, degrau.direita, 0.034, material));

    for (const ponta of [degrau.esquerda, degrau.direita]) {
      const base = new THREE.Mesh(geometriaBase, material);
      base.position.copy(ponta);
      grupo.add(base);
    }
  }

  grupo.add(construirHalo(config, aleatorio, misturar(corFitaA, corFitaB, 0.5)));

  return {
    grupo,
    config,
    cores: { fitaA: corFitaA, fitaB: corFitaB },
  };
}

/**
 * Libera a memoria de GPU usada por uma helice antes de trocar de usuario.
 * @param {THREE.Object3D} raiz
 */
export function descartar(raiz) {
  raiz.traverse((objeto) => {
    if (objeto.geometry) {
      objeto.geometry.dispose();
    }
    if (objeto.material) {
      const materiais = Array.isArray(objeto.material) ? objeto.material : [objeto.material];
      materiais.forEach((material) => {
        // Os rotulos sao texturas de canvas: sem descartar o mapa, cada troca
        // de perfil deixaria uma textura orfa na memoria de video.
        if (material.map) {
          material.map.dispose();
        }
        material.dispose();
      });
    }
  });
}
