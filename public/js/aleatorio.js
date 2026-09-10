/**
 * Gerador de numeros pseudoaleatorios com semente (mulberry32).
 *
 * A cena precisa ser procedural mas nao pode mudar a cada recarga: o mesmo
 * usuario tem que produzir exatamente a mesma helice. Por isso a semente vem
 * do JSON, calculada em Python a partir do nome de usuario, e nunca do relogio.
 */

/**
 * Cria uma funcao que devolve numeros entre 0 (inclusive) e 1 (exclusive).
 * @param {number} semente Semente inteira vinda do JSON do DNA.
 * @returns {() => number}
 */
export function criarAleatorio(semente) {
  let estado = (semente >>> 0) || 1;
  return function aleatorio() {
    estado |= 0;
    estado = (estado + 0x6d2b79f5) | 0;
    let t = Math.imul(estado ^ (estado >>> 15), 1 | estado);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Sorteia um numero dentro de uma faixa.
 * @param {() => number} aleatorio
 * @param {number} minimo
 * @param {number} maximo
 */
export function entre(aleatorio, minimo, maximo) {
  return minimo + aleatorio() * (maximo - minimo);
}

/**
 * Monta um sorteador ponderado a partir de uma lista de itens com peso.
 * Usado para que cada par de bases da helice receba uma linguagem seguindo a
 * mesma proporcao que ela tem no perfil.
 *
 * @param {() => number} aleatorio
 * @param {Array<{peso: number}>} itens
 * @returns {() => any}
 */
export function sorteadorPonderado(aleatorio, itens) {
  const validos = itens.filter((item) => item && item.peso > 0);
  if (validos.length === 0) {
    return () => null;
  }

  const total = validos.reduce((soma, item) => soma + item.peso, 0);
  const acumulados = [];
  let acumulado = 0;
  for (const item of validos) {
    acumulado += item.peso / total;
    acumulados.push({ item, ate: acumulado });
  }

  return function sortear() {
    const alvo = aleatorio();
    for (const faixa of acumulados) {
      if (alvo <= faixa.ate) {
        return faixa.item;
      }
    }
    return acumulados[acumulados.length - 1].item;
  };
}
