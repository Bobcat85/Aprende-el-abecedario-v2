
"""voz.py: reconocimiento de voz que NO congela el juego.
 
Escucha el micrófono en un hilo aparte. El juego pide escuchar y, en cada vuelta de su
bucle, pregunta si ya hay un resultado. Así pygame nunca se queda esperando.
 
Uso básico en el juego:
    import voz
    voz.iniciar()                      # una sola vez, al arrancar
    voz.empezar_a_escuchar()           # cuando el niño puede responder
    ...
    r = voz.resultado()                # en cada vuelta del bucle (no bloquea)
    if r is not None:
        if r.estado == "texto":        # r.texto trae lo que se entendió
            ...
        elif r.estado == "no_entendio":
            ...
    voz.cerrar()                       # al salir del juego
 
Estados posibles de un resultado:
    "texto"          se entendió algo (r.texto)
    "no_entendio"    se oyó algo, pero no se pudo convertir en texto
    "silencio"       no se oyó a nadie
    "sin_internet"   el servicio de Google no respondió
    "sin_microfono"  no se pudo abrir el micrófono
 
Modo simulado (sin micrófono): voz.iniciar(simulado=True) y voz.simular("abeja").
"""
import queue
import re
import threading
import unicodedata
from dataclasses import dataclass
 
import speech_recognition as sr
 
IDIOMA = "es-MX"
ESPERA_MAXIMA = 5       # segundos esperando a que alguien empiece a hablar
DURACION_MAXIMA = 4     # segundos máximos de una respuesta
 
 
@dataclass
class Resultado:
    estado: str
    texto: str = ""
 
 
_peticiones = queue.Queue()
_resultados = queue.Queue()
_cerrar_evento = threading.Event()
_listo = threading.Event()
_hilo = None
_simulado = False
_idioma = IDIOMA
_indice = None
_error_inicio = None
_escuchando = False
_generacion = 0      # cambia con cada 'escuchar' o 'detener'; sirve para descartar respuestas viejas
_candado = threading.Lock()
 
 
def normalizar(texto):
    """Minúsculas, sin tildes y sin signos, pero conservando la ñ: '¡Avión!' -> 'avion', 'Ñu' -> 'ñu'."""
    salida = []
    for c in unicodedata.normalize("NFD", texto.lower()):
        if unicodedata.category(c) == "Mn":          # marca de acento separada de su letra
            if c == "\u0303" and salida and salida[-1] == "n":
                salida[-1] = "ñ"                      # n + tilde = ñ: se conserva
            continue
        salida.append(c)
    texto = re.sub(r"[^a-z0-9ñ ]", " ", "".join(salida))
    return re.sub(r"\s+", " ", texto).strip()
 
 
def _poner_resultado(resultado, generacion=None):
    """Entrega un resultado. Si es de una escucha vieja (ya cancelada), se descarta."""
    global _escuchando
    with _candado:
        if generacion is not None and generacion != _generacion:
            return
        _escuchando = False
        _resultados.put(resultado)
 
 
def _trabajo():
    """Hilo que atiende las peticiones de escuchar."""
    global _error_inicio
    reconocedor = sr.Recognizer()
    microfono = None
    try:
        microfono = sr.Microphone(device_index=_indice)
        with microfono as fuente:
            reconocedor.adjust_for_ambient_noise(fuente, duration=1)
    except Exception as error:  # sin micrófono, sin PyAudio, permisos...
        _error_inicio = str(error) or error.__class__.__name__
    _listo.set()
 
    while not _cerrar_evento.is_set():
        try:
            generacion = _peticiones.get(timeout=0.2)
        except queue.Empty:
            continue
        if generacion != _generacion:      # la petición ya fue cancelada con detener()
            continue
 
        if microfono is None:
            _poner_resultado(Resultado("sin_microfono", _error_inicio or ""), generacion)
            continue
 
        try:
            with microfono as fuente:
                audio = reconocedor.listen(fuente, timeout=ESPERA_MAXIMA,
                                           phrase_time_limit=DURACION_MAXIMA)
            texto = reconocedor.recognize_google(audio, language=_idioma)
            resultado = Resultado("texto", texto)
        except sr.WaitTimeoutError:
            resultado = Resultado("silencio")
        except sr.UnknownValueError:
            resultado = Resultado("no_entendio")
        except sr.RequestError:
            resultado = Resultado("sin_internet")
        except Exception as error:
            resultado = Resultado("sin_microfono", str(error))
 
        _poner_resultado(resultado, generacion)   # se descarta solo si se canceló mientras escuchaba
 
 
def iniciar(idioma=IDIOMA, indice_microfono=None, simulado=False):
    """Prepara la voz. Llamar una sola vez. Tarda ~1 segundo en calibrar (en segundo plano)."""
    global _hilo, _simulado, _idioma, _indice
    _simulado, _idioma, _indice = simulado, idioma, indice_microfono
    _cerrar_evento.clear()
    if simulado:
        _listo.set()
        return
    if _hilo is None or not _hilo.is_alive():
        _hilo = threading.Thread(target=_trabajo, daemon=True)
        _hilo.start()
 
 
def listo():
    """True cuando el micrófono ya está calibrado y se puede escuchar."""
    return _listo.is_set()
 
 
def error_inicio():
    """Texto del problema si el micrófono no se pudo preparar; None si todo va bien."""
    return _error_inicio
 
 
def empezar_a_escuchar():
    """Pide escuchar una respuesta. No bloquea. Si ya está escuchando, no hace nada."""
    global _escuchando, _generacion
    with _candado:
        if _escuchando:
            return
        _escuchando = True
        _generacion += 1
        generacion = _generacion
    if not _simulado:
        _peticiones.put(generacion)
 
 
def escuchando():
    """True mientras se espera una respuesta."""
    return _escuchando
 
 
def resultado():
    """Devuelve el siguiente Resultado, o None si todavía no hay. No bloquea."""
    try:
        return _resultados.get_nowait()
    except queue.Empty:
        return None
 
 
def detener():
    """Cancela lo que se esté escuchando y borra resultados pendientes.
    Lo que el micrófono alcance a oír después de cancelar se descarta."""
    global _escuchando, _generacion
    with _candado:
        _escuchando = False
        _generacion += 1
        while not _resultados.empty():
            try:
                _resultados.get_nowait()
            except queue.Empty:
                break
 
 
def simular(texto):
    """Modo simulado: hace como si el niño hubiera dicho 'texto'."""
    _poner_resultado(Resultado("texto", texto))
 
 
def cerrar():
    """Apaga el hilo. Llamar al salir del juego."""
    _cerrar_evento.set()
 