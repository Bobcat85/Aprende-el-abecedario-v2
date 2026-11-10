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