"""Diagnóstico del micrófono: ¿la computadora capta sonido?

Ejecutar:  python diagnostico_microfono.py
Lista los micrófonos, graba 4 segundos, mide el volumen y guarda 'prueba_micro.wav'
para que puedas escucharlo.
"""
import array
import wave

import pyaudio

SEGUNDOS = 4
BLOQUE = 1024


def listar_entradas(pa):
    try:
        predeterminado = pa.get_default_input_device_info()["index"]
    except OSError:
        predeterminado = None
    print("Dispositivos de ENTRADA (micrófonos):")
    hay = False
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if info["maxInputChannels"] > 0:
            hay = True
            marca = "  <- predeterminado" if i == predeterminado else ""
            print(f"  {i}: {info['name']}{marca}")
    if not hay:
        print("  (no se encontró ningún micrófono)")
    return predeterminado, hay


def main():
    pa = pyaudio.PyAudio()
    predeterminado, hay = listar_entradas(pa)
    if not hay:
        print("\nWindows no muestra ningún micrófono. Revisa que esté conectado y activado en")
        print("Configuración > Sistema > Sonido > Entrada.")
        pa.terminate()
        return

    eleccion = input("\nNúmero del micrófono a probar (Enter = el predeterminado): ").strip()
    indice = int(eleccion) if eleccion.isdigit() else predeterminado
    info = pa.get_device_info_by_index(indice)
    frecuencia = int(info["defaultSampleRate"])
    print(f"\nProbando: {info['name']} ({frecuencia} Hz)")
    print(f"Habla durante {SEGUNDOS} segundos, empezando ahora...")

    try:
        flujo = pa.open(format=pyaudio.paInt16, channels=1, rate=frecuencia,
                        input=True, input_device_index=indice, frames_per_buffer=BLOQUE)
    except OSError as error:
        print("\nNo se pudo abrir el micrófono:", error)
        print("Causas comunes: otro programa lo está usando, o Windows no da permiso a las apps de escritorio.")
        pa.terminate()
        return

    bloques = [flujo.read(BLOQUE, exception_on_overflow=False)
               for _ in range(int(frecuencia / BLOQUE * SEGUNDOS))]
    flujo.stop_stream()
    flujo.close()
    pa.terminate()

    datos = b"".join(bloques)
    muestras = array.array("h", datos)
    pico = max((abs(m) for m in muestras), default=0)
    porcentaje = pico / 32768 * 100
    print(f"\nVolumen máximo captado: {porcentaje:.1f} %")

    if porcentaje < 1:
        print("-> Casi silencio. El micrófono está silenciado, sin permiso, o es el dispositivo equivocado.")
    elif porcentaje < 5:
        print("-> Volumen muy bajo. Sube el volumen de entrada en la configuración de sonido de Windows.")
    else:
        print("-> El micrófono SÍ capta sonido. Si el reconocimiento falla, el problema es internet o el idioma.")

    with wave.open("prueba_micro.wav", "wb") as archivo:
        archivo.setnchannels(1)
        archivo.setsampwidth(2)
        archivo.setframerate(frecuencia)
        archivo.writeframes(datos)
    print("Se guardó 'prueba_micro.wav'. Ábrelo y escucha cómo se oyó tu voz.")


if __name__ == "__main__":
    main()