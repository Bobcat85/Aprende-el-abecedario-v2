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

// Imágenes de distracción: se muestran junto con la correcta para confundir al jugador
const IMAGENES_DISTRACCION = ["arcoiris.png", "barco.png", "cama.png", "disco.png", "escoba.png", "fuego.png",
  "guante.png", "hielo.png", "iglu.png", "jaguar.png", "karate.png", "libro.png", "muñeca.png", "nuez.png",
  "oso.png", "pato.png", "pelota.png", "rana.png", "sandia.png", "telefono.png"];

// Audio 

const VOLUMEN_MUSICA = 0.05, VOLUMEN_EFECTOS = 0.7;
const ruta = (carpeta, nombre) => `assets/${carpeta}/` + encodeURIComponent(nombre.normalize("NFC"));
let ac = null, gMusica = null, gEfectos = null, gVoz = null, elementoMusica = null, musicaIniciada = false;
const buffers = new Map();   // ruta -> AudioBuffer (o null si el archivo no existe)
let vozActual = null;

function prepararAudio() {
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx || ac) return;
  ac = new Ctx();
  gMusica = ac.createGain(); gEfectos = ac.createGain(); gVoz = ac.createGain();
  [gMusica, gEfectos, gVoz].forEach((g) => g.connect(ac.destination));
  elementoMusica = new Audio(ruta("sonidos", "musica_fondo.mp3"));
  elementoMusica.loop = true;
  ac.createMediaElementSource(elementoMusica).connect(gMusica);
  aplicarEstadoAudio();
}
function aplicarEstadoAudio() {
  if (!ac) return;
  const f = audioActivado ? 1 : 0;
  gMusica.gain.value = VOLUMEN_MUSICA * f;
  gEfectos.gain.value = VOLUMEN_EFECTOS * f;
  gVoz.gain.value = f;
}
/** Los navegadores solo permiten sonido después de un toque: se activa en el primer toque. */
function desbloquearAudio() {
  prepararAudio();
  if (!ac) return;
  if (ac.state !== "running") ac.resume();
  if (!musicaIniciada) { musicaIniciada = true; elementoMusica.play().catch(() => { musicaIniciada = false; }); }
}
async function cargarBuffer(url) {
  if (buffers.has(url)) return buffers.get(url);
  let buf = null;
  try {
    const r = await fetch(url);
    if (r.ok) buf = await ac.decodeAudioData(await r.arrayBuffer());
  } catch (e) { /* archivo faltante o formato no soportado: se usa la voz de respaldo */ }
  buffers.set(url, buf);
  return buf;
}
/** Reproduce un mp3 pregrabado. Devuelve true si existe (el llamador usa la voz del navegador si no). */
async function reproducirAudio(url, esperar = true) {
  if (!audioActivado) return true;
  prepararAudio();
  if (!ac) return false;
  const buf = await cargarBuffer(url);
  if (!buf) return false;
  try { vozActual?.stop(); } catch (e) { /* ya había terminado */ }
  const fin = new Promise((res) => {
    const src = ac.createBufferSource();
    src.buffer = buf; src.connect(gVoz); src.onended = res;
    vozActual = src;
    src.start();
  });
  if (esperar) await esperarFin(fin);
  return true;
}
async function efecto(nombre) {
  if (!audioActivado) return;
  prepararAudio();
  const buf = ac && await cargarBuffer(ruta("sonidos", nombre));
  if (!buf) return;
  const src = ac.createBufferSource();
  src.buffer = buf; src.connect(gEfectos); src.start();
}

/** Nombre del mp3 pregrabado que corresponde a la frase, o null si no hay. */
function nombreAudio(texto) {
  const bajo = texto.toLowerCase();
  const inicial = (t) => t.trim()[0].toUpperCase();   // "Bb" -> "B": los audios se llaman pregunta_B.mp3, correcto_B_ballena.mp3
  if (texto.startsWith("¿Cuál imagen empieza con la letra ")) return `pregunta_${inicial(texto.split("letra ")[1].replace("?", ""))}.mp3`;
  if (texto.startsWith("¡Correcto!")) {
    const partes = texto.replace("¡Correcto! ", "").split(" de ");
    return partes.length === 2 ? `correcto_${inicial(partes[0])}_${partes[1].trim()}.mp3` : null;
  }
  if (bajo === "intenta otra vez") return "intenta_otra_vez.mp3";
  if (bajo.includes("se acabaron tus vidas")) return "vidas_terminadas.mp3";
  if (bajo.includes("felicidades")) return "felicidades.mp3";
  return null;
}
/** Voz del navegador, para las frases que no tienen mp3 pregrabado. */
function decir(texto) {
  return new Promise((res) => {
    if (!("speechSynthesis" in window)) return res();
    const u = new SpeechSynthesisUtterance(texto);
    u.lang = "es-MX";
    u.onend = u.onerror = () => res();
    speechSynthesis.cancel();
    speechSynthesis.speak(u);
    setTimeout(res, 7000);   // por si el navegador nunca avisa que terminó
  });
}
async function hablar(texto) {
  if (!audioActivado) return;
  const nombre = nombreAudio(texto);
  if (nombre && await reproducirAudio(ruta("audios", nombre))) return;
  await esperarFin(decir(texto));
}

// Imágenes
const imagenes = new Map();   // nombre -> HTMLImageElement
function cargarImg(nombre) {
  return new Promise((res) => {
    const img = new Image();
    img.onload = () => { imagenes.set(nombre, img); res(img); };
    img.onerror = () => { console.warn("No se pudo cargar la imagen", nombre); res(null); };
    img.src = ruta("imagenes", nombre);
  });
}
const img = (nombre) => imagenes.get(nombre) || null;

/** Ajusta una imagen dentro de maxW x maxH conservando su proporción. */
function ajustada(imagen, maxW, maxH) {
  const p = Math.min(maxW / imagen.width, maxH / imagen.height);
  return { w: imagen.width * p, h: imagen.height * p };
}
function lienzoNuevo(w, h) {
  const c = document.createElement("canvas");
  c.width = w; c.height = h;
  return [c, c.getContext("2d")];
}

const avatares = {};          // "feliz" | "triste" | "animo" -> lienzo 250x250
const cacheCirculos = new Map();
function prepararAvatares() {
  for (const estado of ["feliz", "triste", "animo"]) {
    const origen = img(`avatar_${estado}.png`);
    if (!origen) continue;
    const [c, g] = lienzoNuevo(250, 250);
    const { w, h } = ajustada(origen, 250, 250);
    g.drawImage(origen, (250 - w) / 2, (250 - h) / 2, w, h);
    avatares[estado] = c;
  }
}
/** Imagen de una opción dentro de un círculo blanco. Se procesa una sola vez (caché). */
function imagenCircular(nombre, tam = 300) {
  const clave = nombre + "|" + tam;
  if (cacheCirculos.has(clave)) return cacheCirculos.get(clave);
  const origen = img(nombre);
  if (!origen) return null;
  const [c, g] = lienzoNuevo(tam, tam);
  g.fillStyle = "#fff";
  g.beginPath(); g.arc(tam / 2, tam / 2, tam / 2, 0, Math.PI * 2); g.fill();
  g.save();
  g.beginPath(); g.arc(tam / 2, tam / 2, tam / 2, 0, Math.PI * 2); g.clip();
  const { w, h } = ajustada(origen, tam - 50, tam - 50);
  g.drawImage(origen, (tam - w) / 2, (tam - h) / 2, w, h);
  g.restore();
  cacheCirculos.set(clave, c);
  return c;
}

// Dibujo: texto, botones e íconos

const FUENTE = '"Baloo2", "Comic Sans MS", sans-serif';
function texto(str, x, y, { size = 40, color = "#000", align = "left", base = "top", bold = true } = {}) {
  ctx.font = `${bold ? "700" : "400"} ${size}px ${FUENTE}`;
  ctx.textAlign = align;
  ctx.textBaseline = base;
  ctx.fillStyle = color;
  ctx.fillText(str, x, y);
}
const anchoTexto = (str, size, bold = true) => { ctx.font = `${bold ? "700" : "400"} ${size}px ${FUENTE}`; return ctx.measureText(str).width; };

function rectRedondo(r, radio) { ctx.beginPath(); ctx.roundRect(r.x, r.y, r.w, r.h, radio); }

function boton(r, txt, color, { size = 60, colorTexto = PALETA.texto_claro, radio = 25, borde = 0, colorBorde = "#000" } = {}) {
  rectRedondo(r, radio);
  ctx.fillStyle = color; ctx.fill();
  if (borde) { ctx.lineWidth = borde; ctx.strokeStyle = colorBorde; ctx.stroke(); }
  if (txt) texto(txt, r.x + r.w / 2, r.y + r.h / 2, { size, color: colorTexto, align: "center", base: "middle" });
}
/** Color de la paleta, en su versión 'hover' si el dedo o el mouse está sobre el botón. */
const colorHover = (nombre, r) => PALETA[dentro(r, ptr) ? nombre + "_hover" : nombre];

/** Botón de encendido/apagado: ícono + texto centrados juntos dentro del botón. */
function interruptor(r, txt, color, icono, opciones) {
  boton(r, "", color, { borde: 3 });
  const ancho = anchoTexto(txt, 32);
  const x0 = r.x + r.w / 2 - (34 + 14 + ancho) / 2;   // 34 = ancho del ícono, 14 = espacio
  icono(x0 + 17, r.y + r.h / 2, { color: PALETA.texto_claro, ...opciones });
  texto(txt, x0 + 48, r.y + r.h / 2, { size: 32, color: PALETA.texto_claro, base: "middle" });
}

function dibujarCandado(x, y, { tamaño = 28, color = "#fff", abierto = false } = {}) {
  const cw = tamaño, ch = Math.trunc(tamaño * 0.75);
  const cx = x - cw / 2, cy = y + Math.trunc(tamaño * 0.28) - ch / 2;
  ctx.fillStyle = color;
  rectRedondo({ x: cx, y: cy, w: cw, h: ch }, 5); ctx.fill();
  const rx = Math.trunc(tamaño * 0.32), ry = Math.trunc(tamaño * 2 * 0.32 * 1.1) / 2;
  ctx.strokeStyle = color; ctx.lineWidth = Math.max(3, Math.trunc(tamaño / 7));
  ctx.beginPath();
  if (abierto) ctx.ellipse(x + Math.trunc(tamaño * 0.22), cy - Math.trunc(rx * 0.15), rx, ry, 0, -4.0, -0.9);
  else ctx.ellipse(x, cy + 2, rx, ry, 0, -Math.PI, 0);
  ctx.stroke();
  ctx.fillStyle = "rgb(90,90,90)";
  ctx.beginPath(); ctx.arc(cx + cw / 2, cy + ch / 2, Math.max(2, Math.trunc(tamaño / 9)), 0, Math.PI * 2); ctx.fill();
}
function dibujarEstrella(x, y, { radio = 18, color = "#fff" } = {}) {
  ctx.fillStyle = color; ctx.beginPath();
  for (let i = 0; i < 10; i++) {
    const r = i % 2 === 0 ? radio : radio * 0.45, ang = Math.PI / 2 + i * Math.PI / 5;
    ctx[i ? "lineTo" : "moveTo"](x + r * Math.cos(ang), y - r * Math.sin(ang));
  }
  ctx.closePath(); ctx.fill();
}
function dibujarAltavoz(x, y, { tamaño = 28, color = "#fff", activo = true } = {}) {
  const w = tamaño * 0.32, h = tamaño * 0.5, rx = x - tamaño * 0.32 - w / 2, ry = y - h / 2;
  ctx.fillStyle = color;
  rectRedondo({ x: rx, y: ry, w, h }, 2); ctx.fill();
  const der = rx + w;
  ctx.beginPath();
  ctx.moveTo(der - 2, ry); ctx.lineTo(der + tamaño * 0.3, ry - tamaño * 0.22);
  ctx.lineTo(der + tamaño * 0.3, ry + h + tamaño * 0.22); ctx.lineTo(der - 2, ry + h);
  ctx.closePath(); ctx.fill();
  ctx.strokeStyle = color; ctx.lineWidth = 3;
  if (activo) {
    for (const i of [1, 2]) {
      const r = tamaño * 0.22 * i + tamaño * 0.18;
      ctx.beginPath(); ctx.arc(Math.trunc(der + tamaño * 0.28), y, r, -0.6, 0.6); ctx.stroke();
    }
  } else {
    const cx = x + tamaño * 0.45, s = tamaño * 0.2;
    ctx.lineWidth = 4; ctx.beginPath();
    ctx.moveTo(cx - s, y - s); ctx.lineTo(cx + s, y + s); ctx.moveTo(cx - s, y + s); ctx.lineTo(cx + s, y - s);
    ctx.stroke();
  }
}
/** Burbuja de diálogo con la punta hacia abajo. */
function dibujarBurbuja(txt, x, y) {
  const pad = 20, tam = 40, b = { x, y, w: anchoTexto(txt, tam) + pad * 2, h: tam * 1.4 + pad * 2 };
  const punta = [[x + 30, b.y + b.h], [x + 50, b.y + b.h + 20], [x + 70, b.y + b.h]];
  ctx.fillStyle = "#fff"; ctx.strokeStyle = "#000"; ctx.lineWidth = 3;
  rectRedondo(b, 15); ctx.fill(); ctx.stroke();
  ctx.beginPath(); punta.forEach(([px, py], i) => ctx[i ? "lineTo" : "moveTo"](px, py)); ctx.closePath(); ctx.fill(); ctx.stroke();
  ctx.fillStyle = "#fff"; ctx.fillRect(x + 32, b.y + b.h - 2, 36, 5);   // une la punta con la burbuja
  texto(txt, x + pad, y + pad, { size: tam });
}

function dibujarFondo() { ctx.drawImage(img("Fondo.png"), 0, 0, W, H); }

/** Botón "Menú": en la tablet no hay tecla Esc, así que siempre se puede volver. */
const BOTON_MENU = { x: 20, y: H - 70, w: 150, h: 50 };
function dibujarBotonMenu() {
  boton(BOTON_MENU, "← Menú", colorHover("azul_principal", BOTON_MENU), { size: 28, radio: 18 });
}

// Pantallas de menú
async function pantallaInicio() {
  const bJugar = { x: W / 2 - 150, y: H / 2 + 120, w: 300, h: 80 };
  const bLibre = { x: W - 420, y: 40, w: 380, h: 70 };    // interruptores arriba a la derecha
  const bAudio = { x: W - 420, y: 130, w: 380, h: 70 };
  const logo = img("Logo.png");

  while (true) {
    dibujarFondo();
    if (logo) ctx.drawImage(logo, W / 2 - 250, 50, 500, 350);
    texto("Aprende el abecedario", W / 2, logo ? 365 : 380, { size: 60, align: "center" });
    interruptor(bLibre, `Modo libre: ${modoLibre ? "SÍ" : "NO"}`, PALETA[modoLibre ? "verde_activo" : "gris_bloqueado"],
                dibujarCandado, { tamaño: 26, abierto: modoLibre });
    interruptor(bAudio, `Sonido: ${audioActivado ? "SÍ" : "NO"}`, PALETA[audioActivado ? "azul_principal" : "gris_bloqueado"],
                dibujarAltavoz, { tamaño: 28, activo: audioActivado });
    boton(bJugar, "Jugar", colorHover("azul_principal", bJugar));

    for (const e of eventos()) {
      if (e.t !== "down") continue;
      if (dentro(bJugar, e)) return;
      if (dentro(bLibre, e)) modoLibre = !modoLibre;
      if (dentro(bAudio, e)) { audioActivado = !audioActivado; aplicarEstadoAudio(); }
    }
    await frame();
  }
}


/** Divide el texto en líneas que caben en el ancho dado. */
function envolver(txt, size, maxAncho, bold) {
  const lineas = []; let actual = "";
  for (const palabra of txt.split(" ")) {
    const prueba = (actual + " " + palabra).trim();
    if (anchoTexto(prueba, size, bold) <= maxAncho) actual = prueba;
    else { if (actual) lineas.push(actual); actual = palabra; }
  }
  if (actual) lineas.push(actual);
  return lineas;
}

async function pantallaInstrucciones() {
  const panel = { x: (W - 1000) / 2, y: 170, w: 1000, h: 360 };
  const bIniciar = { x: W / 2 - 210, y: panel.y + panel.h + 20, w: 420, h: 100 };
  const instrucciones = [
    "1. Mira la letra que aparece arriba.",
    "2. Toca la imagen que EMPIECE con esa letra.",
    "3. Si aciertas, escucharás la palabra y sigues avanzando.",
    "4. Si fallas, perderás un corazón (en Modo libre no pasa nada).",
    "¡Diviértete aprendiendo!",
  ];
  const lineas = instrucciones.flatMap((l) => envolver(l, 40, panel.w - 48, false));

  while (true) {
    dibujarFondo();
    texto("Instrucciones", W / 2, 95, { size: 100, align: "center", base: "middle" });
    ctx.globalAlpha = 240 / 255;
    rectRedondo(panel, 30); ctx.fillStyle = "#fff"; ctx.fill();
    ctx.globalAlpha = 1;
    ctx.lineWidth = 4; ctx.strokeStyle = "#000"; rectRedondo(panel, 30); ctx.stroke();
    lineas.forEach((l, i) => texto(l, panel.x + 24, panel.y + 20 + i * 54, { size: 40, bold: false }));
    boton(bIniciar, "¡Iniciar!", colorHover("azul_principal", bIniciar));

    for (const e of eventos()) if (e.t === "down" && dentro(bIniciar, e)) return;
    await frame();
  }
}

/** Se muestra al perder todas las vidas. Devuelve "reintentar" o "menu". */
async function pantallaFinJuego() {
  const x = W / 2 - 210;
  const botones = [{ r: { x, y: H / 2 + 20, w: 420, h: 100 }, txt: "Reintentar", color: "verde_activo", accion: "reintentar" },
                   { r: { x, y: H / 2 + 150, w: 420, h: 100 }, txt: "Menú principal", color: "azul_principal", accion: "menu" }];
  const avatar = avatares.triste;
  while (true) {
    dibujarFondo();
    let yTitulo = 30;
    if (avatar) { ctx.drawImage(avatar, W / 2 - 125, 30); yTitulo += 250; }
    texto("¡Se acabaron tus vidas!", W / 2, yTitulo, { size: 80, color: rgb(200, 0, 0), align: "center" });
    for (const b of botones) boton(b.r, b.txt, colorHover(b.color, b.r), { size: 55 });
    for (const e of eventos()) {
      if (e.t === "down") for (const b of botones) if (dentro(b.r, e)) return b.accion;
      if (e.t === "esc") return "menu";
    }
    await frame();
  }
}

// ============================
// Niveles
// ============================
// Niveles 1-6: las 27 letras por grupos (cada nivel se desbloquea al completar el anterior).
// Niveles 7-8: rompecabezas con 6 letras cada uno (siempre disponibles).
const GRUPOS_LETRAS = [["A - E", 0, 5], ["F - J", 5, 10], ["K - Ñ", 10, 15], ["O - S", 15, 20], ["T - W", 20, 24], ["X - Z", 24, 27]];
const LETRAS_ROMPECABEZAS = [[0, 5, 10, 15, 20, 24], [2, 7, 12, 17, 22, 25]];   // posiciones dentro de 'datos'
const NIVELES = GRUPOS_LETRAS.map(([rango, a, b], n) => ({ nombre: `Nivel ${n + 1}: ${rango}`, datos: datos.slice(a, b) }));
LETRAS_ROMPECABEZAS.forEach((letras, k) => NIVELES.push({ nombre: `Nivel ${7 + k}: Rompecabezas ${k + 1}`, tipo: "rompecabezas", datos: letras.map((i) => datos[i]) }));

// El progreso se guarda en la tablet para que no se pierda al cerrar o recargar la página
const completados = new Set();
try { JSON.parse(localStorage.getItem("abecedario_completados") || "[]").forEach((n) => completados.add(n)); } catch (e) { /* sin almacenamiento */ }
function guardarProgreso() { try { localStorage.setItem("abecedario_completados", JSON.stringify([...completados])); } catch (e) { /* sin almacenamiento */ } }

/** Rompecabezas y Modo libre: siempre abiertos. Letras: el primero, y cada uno al completar el anterior. */
const nivelDesbloqueado = (i) => modoLibre || NIVELES[i].tipo === "rompecabezas" || i === 0 || completados.has(i - 1);

/** Cuadrícula de niveles. Devuelve el índice del nivel elegido (o -1 para volver al título). */
async function pantallaSeleccionNiveles() {
  const columnas = 3, ancho = 360, alto = 120, espacio = 40;
  const x0 = W / 2 - (columnas * ancho + (columnas - 1) * espacio) / 2;
  const bInicio = { x: 20, y: 20, w: 150, h: 50 };
  const rects = NIVELES.map((_, i) => ({ x: x0 + (i % columnas) * (ancho + espacio), y: 225 + Math.floor(i / columnas) * (alto + espacio), w: ancho, h: alto }));

  while (true) {
    dibujarFondo();
    texto("Elige un nivel", W / 2, 25, { size: 90, align: "center" });
    boton(bInicio, "← Inicio", colorHover("azul_principal", bInicio), { size: 28, radio: 18 });
    if (modoLibre) texto("Modo libre activado: sin vidas, todos los niveles disponibles", W / 2, 150, { size: 34, color: PALETA.azul_aviso, align: "center" });

    NIVELES.forEach((nivel, i) => {
      const r = rects[i], abierto = nivelDesbloqueado(i), hecho = completados.has(i);
      boton(r, "", abierto ? colorHover("verde_activo", r) : PALETA.gris_bloqueado,
            { radio: 20, borde: hecho ? 6 : 3, colorBorde: hecho ? PALETA.dorado_completado : "#000" });
      const tinta = abierto ? PALETA.texto_claro : PALETA.texto_bloqueado;
      const grande = anchoTexto(nivel.nombre, 40) <= r.w - 20;   // nombres largos: letra más chica
      const estado = abierto && !hecho ? "" : !abierto ? "Bloqueado" : "¡Completado!";
      texto(nivel.nombre, r.x + r.w / 2, r.y + r.h / 2 - (estado ? 14 : 0), { size: grande ? 40 : 28, color: tinta, align: "center", base: "middle" });
      if (estado) texto(estado, r.x + r.w / 2, r.y + r.h / 2 + 28, { size: 26, color: tinta, align: "center", base: "middle" });
      // Un ícono refuerza el estado además del color y el texto
      if (!abierto) dibujarCandado(r.x + r.w - 28, r.y + 26, { tamaño: 26 });
      else if (hecho) dibujarEstrella(r.x + r.w - 28, r.y + 26, { radio: 16, color: PALETA.dorado_completado });
    });

    for (const e of eventos()) {
      if (e.t !== "down") continue;
      if (dentro(bInicio, e)) return -1;   // volver al título (para cambiar Modo libre o Sonido)
      const i = rects.findIndex((r, k) => nivelDesbloqueado(k) && dentro(r, e));
      if (i >= 0) return i;
    }
    await frame();
  }
}

// ============================
// Pantalla de juego
// ============================
const RONDA_VACIA = { opciones: [], imagen: "", color: "#000", posiciones: [] };
const FRASES_ANIMO = [["¡Vamos, tú puedes!", "animo_tu_puedes.mp3"], ["No te rindas", "animo_no_te_rindas.mp3"],
                      ["Inténtalo otra vez", "animo_intentalo_otra_vez.mp3"]];

/**
 * Dibuja la pantalla de una ronda y devuelve sus botones [{r, ok}].
 *  - ronda: la creada por juegoLetra (null = pantalla sin opciones, como la del final)
 *  - marca: {imagen, r} para poner la palomita o la tachita sobre una opción
 *  - estadoAvatar: "feliz", "triste", "animo" o "normal" (sin avatar)
 */
function mostrarPantalla(letra, ronda = null, marca = null, estadoAvatar = "normal") {
  ronda = ronda || RONDA_VACIA;
  dibujarFondo();
  texto(letra, 55, 55, { size: 200 });                       // sombra
  texto(letra, 50, 50, { size: 200, color: ronda.color });

  // Progreso dentro del nivel: verde = superada, azul = actual, gris = falta
  if (letra && datosNivel.length) {
    const total = datosNivel.length, x0 = W / 2 - ((total - 1) * 38) / 2;
    for (let i = 0; i < total; i++) {
      ctx.fillStyle = PALETA[i < indice ? "verde_activo" : i === indice ? "azul_principal" : "gris_bloqueado"];
      ctx.beginPath(); ctx.arc(x0 + i * 38, 36, 14, 0, Math.PI * 2); ctx.fill();
      if (i === indice) { ctx.lineWidth = 3; ctx.strokeStyle = PALETA.texto_oscuro; ctx.stroke(); }
    }
  }

  if (palabraMostrada) {
    const x = W / 2;
    texto(palabraMostrada, x + 3, 253, { size: 90, align: "center" });
    texto(palabraMostrada, x, 250, { size: 90, color: azar(COLORES_LETRAS), align: "center" });
  }

  const botones = [];
  ronda.opciones.forEach((nombre, i) => {
    const c = imagenCircular(nombre), p = ronda.posiciones[i];
    if (!c) return;
    ctx.drawImage(c, p.x, p.y);
    botones.push({ r: { x: p.x, y: p.y, w: 300, h: 300 }, ok: nombre === ronda.imagen });
  });
  if (marca) { const c = centro(marca.r); ctx.drawImage(marca.imagen, c.x - 125, c.y - 125, 250, 250); }

  const avatar = avatares[estadoAvatar];
  if (avatar) {
    const xa = W / 2 - 125;
    ctx.drawImage(avatar, xa, 20);
    if (estadoAvatar === "animo") {   // burbuja con frase y su audio (sin esperar a que termine)
      const [frase, audio] = azar(FRASES_ANIMO);
      reproducirAudio(ruta("audios", audio), false);
      dibujarBurbuja(frase, xa + 250 + 10, 100);
    }
  }

  if (modoLibre) {   // infinito en vez de corazones
    texto("∞", W - anchoTexto("∞", 50) - 30, 15, { size: 50, color: PALETA.azul_aviso });
  } else {
    for (let i = 0; i < vidas; i++) {
      const cx = W - (i + 1) * 70 + 30;
      ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.arc(cx, 50, 30, 0, Math.PI * 2); ctx.fill();
      ctx.drawImage(img("corazon.png"), cx - 20, 30, 40, 40);
    }
  }
  if (letra && datosNivel.length) dibujarBotonMenu();
  return botones;
}

/** Prepara una ronda (imagen correcta + 2 distractores) y devuelve su objeto 'ronda'. */
async function juegoLetra(info) {
  palabraMostrada = "";
  const correcta = azar(info.correctas);
  const inicial = info.letra[0].toLowerCase();   // los distractores no deben empezar con la misma letra
  const disponibles = IMAGENES_DISTRACCION.filter((i) => i !== correcta.imagen && !i.toLowerCase().startsWith(inicial));
  const opciones = barajar([...muestra(disponibles, 2), correcta.imagen]);
  const y = H / 2 + 30;
  const posiciones = barajar([{ x: W / 4 - 150, y }, { x: W / 2 - 150, y }, { x: (3 * W) / 4 - 150, y }]);
  const ronda = { opciones, imagen: correcta.imagen, palabra: correcta.palabra, color: azar(COLORES_LETRAS), posiciones };
  rondaActual = ronda;
  ronda.botones = mostrarPantalla(info.letra, ronda);
  await hablar(`¿Cuál imagen empieza con la letra ${info.letra}?`);
  return ronda;
}

// ============================
// Minijuegos
// ============================
/** Repaso: arrastrar la imagen hasta la letra con la que empieza. */
async function minijuegoArrastrar(letrasAprendidas, correcta, imagenCorrecta, palabra) {
  const inicial = correcta[0].toUpperCase();   // "Ññ" -> "Ñ" (así se llaman los audios minijuego_Ñ_ñu.mp3)
  const opciones = muestra(letrasAprendidas, 3);
  if (!opciones.includes(correcta)) opciones[Math.floor(Math.random() * opciones.length)] = correcta;

  const circulo = imagenCircular(imagenCorrecta, 200);
  if (!circulo) return;
  const rectImg = { x: 100, y: H / 2, w: 200, h: 200 };
  const posiciones = barajar([{ x: 600, y: 190 }, { x: 870, y: 360 }, { x: 1090, y: 530 }]);   // en diagonal, sin encimarse
  const letras = opciones.map((letra, i) => {
    const w = anchoTexto(letra, 180), p = posiciones[i];
    return { letra, r: { x: p.x - w / 2, y: p.y - 100, w, h: 200 } };
  });

  const dibujar = () => {
    dibujarFondo();
    for (const l of letras) {
      const caja = inflar(l.r, 30, 30);
      ctx.fillStyle = "#fff"; ctx.fillRect(caja.x, caja.y, caja.w, caja.h);
      ctx.lineWidth = 4; ctx.strokeStyle = "#000"; ctx.strokeRect(caja.x, caja.y, caja.w, caja.h);
      texto(l.letra, l.r.x + l.r.w / 2, l.r.y + l.r.h / 2, { size: 180, align: "center", base: "middle" });
    }
    ctx.drawImage(circulo, rectImg.x, rectImg.y);
  };
  dibujar();
  await pausa(500);
  if (!(await reproducirAudio(ruta("audios", `minijuego_${inicial}_${palabra}.mp3`)))) await hablar(`¿A qué letra corresponde ${palabra}? Arrástrala`);

  let arrastrando = false, terminado = false;
  while (!terminado) {
    for (const e of eventos()) {
      if (e.t === "down" && dentro(rectImg, e)) arrastrando = true;
      else if (e.t === "up") {
        arrastrando = false;
        for (const l of letras) {
          if (!choca(rectImg, l.r)) continue;
          if (l.letra === correcta) {
            if (!(await reproducirAudio(ruta("audios", "muy_bien.mp3")))) await hablar("¡Muy bien!");
            terminado = true;
          } else { rectImg.x = 100; rectImg.y = H / 2; await hablar("Intenta otra vez"); }   // la imagen vuelve a su sitio
          break;
        }
        if (terminado) break;
      } else if (e.t === "move" && arrastrando) { rectImg.x = e.x - rectImg.w / 2; rectImg.y = e.y - rectImg.h / 2; }
    }
    dibujar();
    await frame();
  }
}

/** Rompecabezas: la letra se parte en 2 piezas (arriba y abajo) que el jugador arma. Sin vidas ni tiempo límite. */
async function minijuegoRompecabezas(infoLetra) {
  const letra = infoLetra.letra, objeto = azar(infoLetra.correctas);
  const ancho = 260, alto = 150;   // tamaño de cada pieza; la letra completa mide ancho x (2 * alto)

  // La letra se dibuja en un lienzo aparte para poder partirla en dos
  const [completa, g] = lienzoNuevo(ancho, alto * 2);
  let size = 180;
  ctx.font = `700 ${size}px ${FUENTE}`;
  while (ctx.measureText(letra).width > ancho - 20 && size > 60) { size -= 10; ctx.font = `700 ${size}px ${FUENTE}`; }
  g.font = `700 ${size}px ${FUENTE}`; g.textAlign = "center"; g.textBaseline = "middle";
  g.fillStyle = azar(COLORES_LETRAS);
  g.fillText(letra, ancho / 2, alto);

  const x0 = W / 2 - ancho / 2, y0 = H / 2 - alto;                    // posición final, al centro
  const origenes = [{ x: 150, y: H - 300 }, { x: W - 150 - ancho, y: 150 }];   // piezas revueltas a los lados
  const piezas = [0, 1].map((k) => ({ k, r: { x: origenes[k].x, y: origenes[k].y, w: ancho, h: alto },
                                      objetivo: { x: x0, y: y0 + k * alto, w: ancho, h: alto }, colocada: false }));
  const apoyo = imagenCircular(objeto.imagen, 160);

  const dibujar = () => {
    dibujarFondo();
    texto("Arrastra las piezas para armar la letra", W / 2, 60, { size: 40, align: "center" });
    if (apoyo) ctx.drawImage(apoyo, 40, H / 2 - 80);
    ctx.lineWidth = 4; ctx.strokeStyle = "#fff";
    for (const p of piezas) { rectRedondo(p.objetivo, 10); ctx.stroke(); }
    for (const p of piezas) ctx.drawImage(completa, 0, p.k * alto, ancho, alto, p.r.x, p.r.y, ancho, alto);
    dibujarBotonMenu();
  };
  dibujar();
  await pausa(400);
  await hablar(`Arma la letra ${letra} uniendo las dos piezas`);

  let enMano = null;
  while (!piezas.every((p) => p.colocada)) {
    for (const e of eventos()) {
      if (e.t === "down") {
        if (dentro(BOTON_MENU, e)) return false;
        enMano = piezas.find((p) => !p.colocada && dentro(p.r, e)) || null;
      } else if (e.t === "up" && enMano) {
        if (choca(enMano.r, inflar(enMano.objetivo, 60, 60))) {   // tolerancia de 60 px
          enMano.r.x = enMano.objetivo.x; enMano.r.y = enMano.objetivo.y; enMano.colocada = true;
          efecto("correcto.wav");
        }
        enMano = null;
      } else if (e.t === "move" && enMano) { enMano.r.x = e.x - ancho / 2; enMano.r.y = e.y - alto / 2; }
      else if (e.t === "esc") return false;
    }
    dibujar();
    await frame();
  }
  if (!(await reproducirAudio(ruta("audios", "muy_bien.mp3")))) await hablar(`¡Excelente! Armaste la letra ${letra}`);
  await pausa(1200);
  return true;
}

// ============================
// Flujo de un nivel
// ============================
/** Marca el nivel como completado y lo celebra (con mensaje especial al completar todos). */
async function terminarNivel(idx) {
  completados.add(idx);
  guardarProgreso();
  if (completados.size === NIVELES.length) {
    await hablar("¡Felicidades! Has terminado el abecedario.");
    mostrarPantalla("", null, null, "feliz");
    await pausa(2500);
  } else await hablar("¡Nivel completado!");
}

/** Juega un nivel de letras. Devuelve true si el jugador eligió 'Reintentar' al quedarse sin vidas. */
async function jugarNivel(idx) {
  datosNivel = NIVELES[idx].datos;
  vidas = 5; indice = 0;
  let ronda = await juegoLetra(datosNivel[0]);

  while (true) {
    for (const e of eventos()) {
      if (e.t === "esc") return false;
      if (e.t !== "down") continue;
      if (dentro(BOTON_MENU, e)) return false;
      const clic = ronda.botones.find((b) => dentro(b.r, e));
      if (!clic) continue;
      const letra = datosNivel[indice].letra;

      if (clic.ok) {
        efecto("correcto.wav");
        palabraMostrada = ronda.palabra;
        mostrarPantalla(letra, ronda, { imagen: PALOMITA, r: clic.r }, "feliz");   // se ve al instante
        await hablar(`¡Correcto! ${letra} de ${ronda.palabra}`);
        await pausa(1500);
        indice++;
        if (indice < datosNivel.length) { ronda = await juegoLetra(datosNivel[indice]); break; }
        // Última letra: minijuego de repaso con una imagen del nivel y se termina
        const info = azar(datosNivel), objeto = azar(info.correctas);
        await minijuegoArrastrar(datosNivel.map((d) => d.letra), info.letra, objeto.imagen, objeto.palabra);
        await terminarNivel(idx);
        return false;
      }

      efecto("error.wav");
      if (!modoLibre) vidas--;
      if (vidas <= 0) {
        mostrarPantalla(letra, ronda, null, "triste");
        await hablar("¡Se acabaron tus vidas!");
        await pausa(1500);
        return (await pantallaFinJuego()) === "reintentar";
      }
      mostrarPantalla(letra, ronda, { imagen: TACHITA, r: clic.r }, "triste");   // se ve al instante
      await hablar("Intenta otra vez");
      await pausa(1200);
      ronda.botones = mostrarPantalla(letra, ronda, null, "animo");
      await pausa(1500);
      break;
    }
    await frame();
  }
}

// ============================
// Arranque y bucle principal
// ============================
let PALOMITA = null, TACHITA = null;

async function cargarTodo() {
  const nombres = ["Fondo.png", "Logo.png", "palomita.png", "tachita.png", "corazon.png",
                   "avatar_feliz.png", "avatar_triste.png", "avatar_animo.png",
                   ...IMAGENES_DISTRACCION, ...datos.flatMap((d) => d.correctas.map((c) => c.imagen))];
  let listos = 0;
  ctx.fillStyle = "#a8dcf0"; ctx.fillRect(0, 0, W, H);
  await Promise.all([document.fonts.load('700 40px "Baloo2"'), document.fonts.load('400 40px "Baloo2"'),
    ...nombres.map((n) => cargarImg(n).then(() => {
      listos++;
      ctx.fillStyle = "#a8dcf0"; ctx.fillRect(0, 0, W, H);
      texto("Cargando…", W / 2, H / 2 - 40, { size: 60, color: PALETA.texto_oscuro, align: "center", base: "middle" });
      ctx.fillStyle = "#fff"; ctx.fillRect(W / 2 - 250, H / 2 + 20, 500, 24);
      ctx.fillStyle = PALETA.azul_principal; ctx.fillRect(W / 2 - 250, H / 2 + 20, 500 * listos / nombres.length, 24);
    }))]);
  PALOMITA = img("palomita.png"); TACHITA = img("tachita.png");
  prepararAvatares();
}

async function main() {
  await cargarTodo();
  let reintentar = null;   // si el jugador eligió "Reintentar", índice del nivel a repetir sin pasar por los menús
  await pantallaInicio();
  await pantallaInstrucciones();
  while (true) {
    let idx;
    if (reintentar === null) {
      idx = await pantallaSeleccionNiveles();
      if (idx < 0) { await pantallaInicio(); continue; }
    } else { idx = reintentar; reintentar = null; }

    if (NIVELES[idx].tipo === "rompecabezas") {
      let completo = true;
      for (const info of NIVELES[idx].datos) if (!(await minijuegoRompecabezas(info))) { completo = false; break; }
      if (completo) await terminarNivel(idx);
    } else if (await jugarNivel(idx)) reintentar = idx;
  }
}

if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost")) {
  navigator.serviceWorker.register("sw.js").catch(() => { /* sin modo sin conexión */ });
}
window.__abecedario = { get ronda() { return rondaActual; }, get estado() { return { vidas, indice, modoLibre, audioActivado, completados: [...completados] }; } };
main();
