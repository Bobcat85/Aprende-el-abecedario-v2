"""respuestas.py: decide si lo que dijo el niño corresponde a una de las imágenes.

No depende de pygame ni del micrófono: recibe texto y devuelve un veredicto.

    from respuestas import evaluar
    v = evaluar("la abeja", correcta="abeja", opciones=["abeja", "ballena", "casa"])
    v.estado   -> "correcta" | "incorrecta" | "no_claro"
    v.opcion   -> la palabra a la que se parece lo que dijo (o None)

Regla de oro para niños: ante la duda es "no_claro" (se pide intentar otra vez);
nunca se marca un error si no se está seguro.
"""
import difflib
from dataclasses import dataclass

from voz import normalizar

# Mismas palabras que usa generar_audios.py
PALABRAS = {
    "A": ["abeja", "avión", "árbol"], "B": ["ballena", "bicicleta", "botas"],
    "C": ["conejo", "casa", "carro"], "D": ["delfín", "dado", "dona"],
    "E": ["escalera", "elefante", "estrella"], "F": ["foca", "foco", "fresa"],
    "G": ["gato", "globo", "guitarra"], "H": ["hilo", "huevo", "hoja"],
    "I": ["iguana", "isla", "imán"], "J": ["jirafa", "jaula", "jarrón"],
    "K": ["kiosco", "koala", "kiwi"], "L": ["león", "lápiz", "lámpara"],
    "M": ["mesa", "mariposa", "manzana"], "N": ["nube", "nido", "naranja"],
    "Ñ": ["ñu", "ñame", "ñandú"], "O": ["oveja", "ojo", "olla"],
    "P": ["perro", "pera", "peine"], "Q": ["querubín", "queso", "quirófano"],
    "R": ["rosa", "ratón", "reloj"], "S": ["sol", "serpiente", "silla"],
    "T": ["taco", "tigre", "tambor"], "U": ["uña", "universo", "uva"],
    "V": ["vaca", "vela", "ventana"], "W": ["wifi", "waffle"],
    "X": ["xilófono"], "Y": ["yoyo", "yegua", "yema"],
    "Z": ["zapato", "zorro", "zanahoria"],
}

# Cómo se dice (y cómo suele transcribir Google) el nombre de cada letra.
# B y V se pronuncian igual en México, así que cada una acepta los dos nombres.
NOMBRES_LETRA = {
    "A": ["a"], "B": ["be", "b", "ve", "be grande", "be larga"],
    "C": ["ce", "c", "se"], "D": ["de", "d"], "E": ["e"],
    "F": ["efe", "f"], "G": ["ge", "g", "je"], "H": ["hache", "h", "ache"],
    "I": ["i"], "J": ["jota", "j"], "K": ["ka", "k", "ca"],
    "L": ["ele", "l"], "M": ["eme", "m"], "N": ["ene", "n"],
    "Ñ": ["eñe", "ñ"], "O": ["o"], "P": ["pe", "p"],
    "Q": ["cu", "q", "ku"], "R": ["erre", "r", "ere"], "S": ["ese", "s"],
    "T": ["te", "t"], "U": ["u"],
    "V": ["uve", "ve", "v", "be", "ve chica", "be chica", "ve corta", "be corta"],
    "W": ["doble ve", "doble u", "uve doble", "w", "doble be"],
    "X": ["equis", "x"], "Y": ["ye", "y", "i griega"], "Z": ["zeta", "z", "seta"],
}

UMBRAL_ACEPTAR = 0.80   # qué tanto debe parecerse para darlo por entendido
MARGEN = 0.10           # diferencia mínima con la segunda mejor opción


@dataclass
class Veredicto:
    estado: str            # "correcta", "incorrecta" o "no_claro"
    opcion: str = None     # palabra o letra a la que se parece
    puntaje: float = 0.0


def _parecido(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def _puntaje_palabra(escuchado, palabra):
    """De 0 a 1: qué tanto lo escuchado contiene o se parece a la palabra."""
    if not escuchado or not palabra:
        return 0.0
    tokens = escuchado.split()
    if palabra in tokens:                                   # "es una abeja"
        return 1.0
    if palabra + "s" in tokens or palabra + "es" in tokens:  # plural sencillo
        return 0.97
    mejor = _parecido(escuchado, palabra)
    for t in tokens:
        mejor = max(mejor, _parecido(t, palabra))
    mejor = max(mejor, _parecido("".join(tokens), palabra))  # "ma ripo sa" -> "maripos a"
    return mejor


def evaluar(texto, correcta, opciones):
    """Compara lo que dijo el niño con las imágenes que hay en pantalla."""
    escuchado = normalizar(texto)
    palabras = {o: normalizar(o) for o in opciones}
    puntajes = {o: _puntaje_palabra(escuchado, p) for o, p in palabras.items()}
    if not puntajes:
        return Veredicto("no_claro")

    ordenados = sorted(puntajes.items(), key=lambda x: x[1], reverse=True)
    mejor, p = ordenados[0]
    segundo = ordenados[1][1] if len(ordenados) > 1 else 0.0

    if p < UMBRAL_ACEPTAR or (p - segundo) < MARGEN:
        return Veredicto("no_claro", mejor, p)
    estado = "correcta" if palabras[mejor] == normalizar(correcta) else "incorrecta"
    return Veredicto(estado, mejor, p)


def _limpiar_letra(texto):
    tokens = [t for t in normalizar(texto).split() if t not in {"la", "el", "letra", "es", "una", "un"}]
    return " ".join(tokens)


def evaluar_letra(texto, letra):
    """Para cuando el niño dice el NOMBRE de la letra ('be', 'jota')."""
    dicho = _limpiar_letra(texto)
    if not dicho:
        return Veredicto("no_claro")
    esperadas = {normalizar(n) for n in NOMBRES_LETRA[letra]}
    if dicho in esperadas:
        return Veredicto("correcta", letra, 1.0)
    for otra, nombres in NOMBRES_LETRA.items():
        if otra != letra and dicho in {normalizar(n) for n in nombres}:
            return Veredicto("incorrecta", otra, 1.0)
    cercano = max((_parecido(dicho, n) for n in esperadas), default=0.0)
    return Veredicto("no_claro", None, cercano)
