"""Prueba de voz.py SIN el juego.

  python probar_voz.py             escucha el micrófono de verdad
  python probar_voz.py simulado    tú escribes lo que "diría" el niño

Mientras espera, muestra un contador: eso demuestra que el programa NO se congela.
"""
import sys
import time

import voz

SIMULADO = len(sys.argv) > 1 and sys.argv[1].lower().startswith("sim")
INTENTOS = 5


def main():
    voz.iniciar(simulado=SIMULADO)
    print("Preparando el micrófono (calibrando el ruido)...")
    while not voz.listo():
        time.sleep(0.1)
    if voz.error_inicio():
        print("Problema con el micrófono:", voz.error_inicio())
        return

    for n in range(1, INTENTOS + 1):
        print(f"\n--- Intento {n} de {INTENTOS} ---")
        voz.empezar_a_escuchar()
        inicio = time.time()

        if SIMULADO:
            voz.simular(input("Escribe lo que diría el niño: "))

        r = None
        while r is None:
            r = voz.resultado()
            if r is None:
                print(f"\rHabla ahora... ({time.time() - inicio:0.1f} s)", end="", flush=True)
                time.sleep(0.1)  # aquí iría el dibujo de pygame: el programa sigue vivo
        print()

        if r.estado == "texto":
            print(f"Entendí: '{r.texto}'   (normalizado: '{voz.normalizar(r.texto)}')")
        else:
            print("Resultado:", r.estado, r.texto)

    voz.cerrar()
    print("\nListo.")


if __name__ == "__main__":
    main()