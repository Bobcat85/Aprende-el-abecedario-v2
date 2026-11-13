"use strict";
//El objetivo de esta version es adaptar el juego para uso en navegadores web

//Inicio, entrada tactil y bucle

const W = 1280, H = 720;
const canvas = document.getElementById("lienzo");
const ctx = canvas.getContext("2d");
canvas.width = W;
canvas.height = H;

function ajustarLienzo() {
  const esc = Math.min(innerWidth / W, innerHeight / H);
  canvas.style.width = W * esc + "px";
  canvas.style.height = H * esc + "px";
}
addEventListener("resize", ajustarLienzo);
ajustarLienzo();

const ptr = { x: -1, y: -1 };   // última posición del dedo o mouse (para el efecto hover)
let cola = [];                  // eventos pendientes: {t: "down" | "move" | "up" | "esc", x, y}

function posicion(e) {
  const r = canvas.getBoundingClientRect();
  return { x: (e.clientX - r.left) * W / r.width, y: (e.clientY - r.top) * H / r.height };
}
function alTocar(tipo) {
  return (e) => {
    const p = posicion(e);
    ptr.x = p.x; ptr.y = p.y;
    if (tipo === "down") { desbloquearAudio(); canvas.setPointerCapture?.(e.pointerId); }
    cola.push({ t: tipo, ...p });
    e.preventDefault();
  };
}
canvas.addEventListener("pointerdown", alTocar("down"));
canvas.addEventListener("pointermove", alTocar("move"));
canvas.addEventListener("pointerup", alTocar("up"));
canvas.addEventListener("pointercancel", alTocar("up"));
addEventListener("keydown", (e) => { if (e.key === "Escape") cola.push({ t: "esc" }); });

const eventos = () => { const c = cola; cola = []; return c; };
const frame = () => new Promise((r) => requestAnimationFrame(() => r()));

//Espera para evitar la congelacion de la pantalla
async function pausa(ms) {
  const fin = performance.now() + ms;
  while (performance.now() < fin) { cola = []; await frame(); }
}

//Espera que termine de interactuar la voz
async function esperarFin(promesa) {
  let listo = false;
  promesa.then(() => { listo = true; });
  while (!listo) { cola = []; await frame(); }
}

//Funciones de utilidad
// Devuelve un elemento aleatorio de la lista
const azar = (lista) => lista[Math.floor(Math.random() * lista.length)];
function barajar(lista) {
  for (let i = lista.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [lista[i], lista[j]] = [lista[j], lista[i]];
  }
  return lista;
}
const muestra = (lista, n) => barajar([...lista]).slice(0, n);
const dentro = (r, p) => p.x >= r.x && p.x <= r.x + r.w && p.y >= r.y && p.y <= r.y + r.h;
const choca = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
const inflar = (r, dx, dy) => ({ x: r.x - dx / 2, y: r.y - dy / 2, w: r.w + dx, h: r.h + dy });
const centro = (r) => ({ x: r.x + r.w / 2, y: r.y + r.h / 2 });

// Estado global del juego
let palabraMostrada = "";   // la palabra se muestra solo cuando se acierta
let modoLibre = false;      // sin vidas y con todos los niveles abiertos (práctica sin presión)
let audioActivado = true;   // interruptor maestro: música, efectos y voz
let vidas = 5, indice = 0, datosNivel = [];   // nivel en curso (los lee mostrarPantalla)
let rondaActual = null;     // ronda en pantalla (también la usan las pruebas automáticas)


// Paleta de colores  
const rgb = (r, g, b) => `rgb(${r},${g},${b})`;
const PALETA = {
  verde_activo: rgb(108, 189, 134), verde_activo_hover: rgb(128, 206, 153),
  azul_principal: rgb(94, 158, 214), azul_principal_hover: rgb(118, 178, 230),
  rosa_suave: rgb(224, 122, 122), rosa_suave_hover: rgb(235, 146, 146),
  gris_bloqueado: rgb(176, 176, 176), dorado_completado: rgb(232, 192, 90),
  texto_oscuro: rgb(60, 60, 70), texto_claro: "#fff", texto_bloqueado: rgb(90, 90, 90),
  azul_aviso: rgb(0, 102, 204),
};
const COLORES_LETRAS = [rgb(224, 122, 122), rgb(108, 189, 134), rgb(94, 158, 214),
                        rgb(232, 160, 96), rgb(170, 128, 196), rgb(232, 192, 90)];


// Datos de las letras y palabras
// se asocian imágenes y palabras a cada letra, para que el juego pueda mostrar la letra y decir la palabra
const TABLA_LETRAS = `
Aa | A_abeja.png=abeja, A_avion.png=avión, A_arbol.png=árbol
Bb | B_ballena.png=ballena, B_bicicleta.png=bicicleta, B_botas.png=botas
Cc | C_conejo.png=conejo, C_casa.png=casa, C_carro.png=carro
Dd | D_delfin.png=delfín, D_dado.png=dado, D_dona.png=dona
Ee | E_escalera.png=escalera, E_elefante.png=elefante, E_estrella.png=estrella
Ff | F_foca.png=foca, F_foco.png=foco, F_fresa.png=fresa
Gg | G_gato.png=gato, G_globo.png=globo, G_guitarra.png=guitarra
Hh | H_hilo.png=hilo, H_huevo.png=huevo, H_hoja.png=hoja
Ii | I_iguana.png=iguana, I_isla.png=isla, I_iman.png=imán
Jj | J_jirafa.png=jirafa, J_jaula.png=jaula, J_jarron.png=jarrón
Kk | K_kiosco.png=kiosco, K_koala.png=koala, K_kiwi.png=kiwi
Ll | L_leon.png=león, L_lapiz.png=lápiz, L_lampara.png=lámpara
Mm | M_mesa.png=mesa, M_mariposa.png=mariposa, M_manzana.png=manzana
Nn | N_nube.png=nube, N_nido.png=nido, N_naranja.png=naranja
Ññ | N_nu.png=ñu, N_name.png=ñame, N_nandu.png=ñandú
Oo | O_oveja.png=oveja, O_ojo.png=ojo, O_olla.png=olla
Pp | P_perro.png=perro, P_pera.png=pera, P_peine.png=peine
Qq | Q_querubin.png=querubín, Q_queso.png=queso, Q_quirofano.png=quirófano
Rr | R_rosa.png=rosa, R_raton.png=ratón, R_reloj.png=reloj
Ss | S_sol.png=sol, S_serpiente.png=serpiente, S_silla.png=silla
Tt | T_taco.png=taco, T_tigre.png=tigre, T_tambor.png=tambor
Uu | U_uña.png=uña, U_universo.png=universo, U_uva.png=uva
Vv | V_vaca.png=vaca, V_vela.png=vela, V_ventana.png=ventana
Ww | W_wifi.png=wifi, W_waffle.png=waffle
Xx | X_xilofono.png=xilófono
Yy | Y_yoyo.png=yoyo, Y_yegua.png=yegua, Y_yema.png=yema
Zz | Z_zapato.png=zapato, Z_zorro.png=zorro, Z_zanahoria.png=zanahoria
`;
const datos = TABLA_LETRAS.trim().split("\n").map((linea) => {
  const [letra, resto] = linea.split("|");
  return { letra: letra.trim(),
           correctas: resto.split(",").map((par) => { const [imagen, palabra] = par.trim().split("="); return { imagen, palabra }; }) };
});
