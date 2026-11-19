"""Prueba del micrófono con SpeechRecognition.

Instalar antes:  pip install SpeechRecognition pyaudio
Ejecutar:        python probar_microfono.py
No modifica el juego: solo comprueba que la computadora puede escuchar.
"""
import speech_recognition as sr

IDIOMA = "es-MX"   # también puede ser "es-ES" o "en-US"
INTENTOS = 5


def escuchar(reconocedor, microfono, segundos=4):
    """Escucha una vez y devuelve el texto, '' si no entendió o None si hubo un problema."""
    with microfono as fuente:
        print("Habla ahora...")
        try:
            audio = reconocedor.listen(fuente, timeout=5, phrase_time_limit=segundos)
        except sr.WaitTimeoutError:
            print("No se escuchó nada.")
            return None
    try:
        return reconocedor.recognize_google(audio, language=IDIOMA)
    except sr.UnknownValueError:
        return ""  # se escuchó algo, pero no se entendió
    except sr.RequestError as error:
        print("Sin internet o el servicio no responde:", error)
        return None


def main():
    print("Micrófonos encontrados:")
    for i, nombre in enumerate(sr.Microphone.list_microphone_names()):
        print(f"  {i}: {nombre}")

    reconocedor = sr.Recognizer()
    microfono = sr.Microphone()  # usa el micrófono predeterminado de Windows

    with microfono as fuente:
        print("\nCalibrando el ruido de fondo (1 segundo, no hables)...")
        reconocedor.adjust_for_ambient_noise(fuente, duration=1)

    for n in range(1, INTENTOS + 1):
        print(f"\nIntento {n} de {INTENTOS}")
        texto = escuchar(reconocedor, microfono)
        if texto is None:
            continue
        print("Entendí:", texto if texto else "(no entendí)")


if __name__ == "__main__":
    main()