"""Prueba de voz con las 27 letras (día 3).

  python probar_letras.py              micrófono real, 1 palabra por letra (27 palabras)
  python probar_letras.py todas        micrófono real, las ~80 palabras del juego
  python probar_letras.py simulado     tú escribes lo que "diría" el niño

Para cada letra se te pide decir el nombre de una imagen. Al final se muestra una tabla
con lo que entendió el reconocedor y el porcentaje de aciertos.
"""
import random
import sys
import time

import voz
from respuestas import PALABRAS, evaluar

ARGS = [a.lower() for a in sys.argv[1:]]
SIMULADO = any(a.startswith("sim") for a in ARGS)
TODAS = "todas" in ARGS


def escuchar():
    """Escucha una respuesta y devuelve el Resultado (sin congelar el programa)."""
    voz.empezar_a_escuchar()
    if SIMULADO:
        voz.simular(input("   Escribe lo que diría el niño: "))
    inicio = time.time()
    r = None
    while r is None:
        r = voz.resultado()
        if r is None:
            print(f"\r   Habla ahora... ({time.time() - inicio:0.1f} s)", end="", flush=True)
            time.sleep(0.1)
    print("\r" + " " * 40 + "\r", end="")
    return r


def lista_de_pruebas():
    pruebas = []
    for letra, palabras in PALABRAS.items():
        for palabra in (palabras if TODAS else palabras[:1]):
            pruebas.append((letra, palabra))
    return pruebas


def main():
    voz.iniciar(simulado=SIMULADO)
    print("Preparando el micrófono (calibrando el ruido)...")
    while not voz.listo():
        time.sleep(0.1)
    if voz.error_inicio():
        print("Problema con el micrófono:", voz.error_inicio())
        return

    todas_las = [w for ws in PALABRAS.values() for w in ws]
    resultados = []
    pruebas = lista_de_pruebas()

    for n, (letra, palabra) in enumerate(pruebas, 1):
        otras = [w for w in todas_las if w not in PALABRAS[letra]]
        opciones = [palabra] + random.sample(otras, 2)
        random.shuffle(opciones)

        while True:
            print(f"\n[{n}/{len(pruebas)}] Letra {letra}: di  «{palabra}»")
            orden = input("   Enter = empezar, s = saltar, q = terminar: ").strip().lower()
            if orden == "q":
                break
            if orden == "s":
                registro = (letra, palabra, "(saltada)", "saltada")
                break
            r = escuchar()
            if r.estado == "texto":
                v = evaluar(r.texto, palabra, opciones)
                registro = (letra, palabra, r.texto, v.estado)
                print(f"   Entendió: «{r.texto}»  ->  {v.estado}   (opciones en pantalla: {', '.join(opciones)})")
            else:
                registro = (letra, palabra, "(nada)", r.estado)
                print(f"   Resultado: {r.estado} {r.texto}")
            if input("   Enter = siguiente, r = repetir: ").strip().lower() != "r":
                break
        if orden == "q":
            break
        resultados.append(registro)

    voz.cerrar()

    # ---- Resumen ----
    print("\n" + "=" * 66)
    print(f"{'Letra':<6}{'Dije':<14}{'Entendió':<24}{'Resultado'}")
    print("-" * 66)
    for letra, palabra, oido, estado in resultados:
        print(f"{letra:<6}{palabra:<14}{oido[:22]:<24}{estado}")
    print("=" * 66)
    validas = [r for r in resultados if r[3] != "saltada"]
    if validas:
        buenas = sum(1 for r in validas if r[3] == "correcta")
        print(f"Aciertos: {buenas} de {len(validas)}  ({buenas / len(validas) * 100:.0f} %)")
        for estado in ("incorrecta", "no_claro", "no_entendio", "silencio", "sin_internet", "sin_microfono"):
            cuantas = sum(1 for r in validas if r[3] == estado)
            if cuantas:
                print(f"  {estado}: {cuantas}")


if __name__ == "__main__":
    main()