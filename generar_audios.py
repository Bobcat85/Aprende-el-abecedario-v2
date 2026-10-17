# generar_abecedario_local.py

from gtts import gTTS
import os

# Asegúrate de instalar 'gTTS' con: pip install gTTS

os.makedirs("assets/audios", exist_ok=True)

# Todas las letras con sus palabras
datos = {
    "A": ["abeja", "avión", "árbol"],
    "B": ["ballena", "bicicleta", "botas"],
    "C": ["conejo", "casa", "carro"],
    "D": ["delfín", "dado", "dona"],
    "E": ["escalera", "elefante", "estrella"],
    "F": ["foca", "foco", "fresa"],
    "G": ["gato", "globo", "guitarra"],
    "H": ["hilo", "huevo", "hoja"],
    "I": ["iguana", "isla", "imán"],
    "J": ["jirafa", "jaula", "jarrón"],
    "K": ["kiosco", "koala", "kiwi"],
    "L": ["león", "lápiz", "lámpara"],
    "M": ["mesa", "mariposa", "manzana"],
    "N": ["nube", "nido", "naranja"],
    "Ñ": ["ñu", "ñame", "ñandú"],
    "O": ["oveja", "ojo", "olla"],
    "P": ["perro", "pera", "peine"],
    "Q": ["querubín", "queso", "quirófano"],
    "R": ["rosa", "ratón", "reloj"],
    "S": ["sol", "serpiente", "silla"],
    "T": ["taco", "tigre", "tambor"],
    "U": ["uña", "universo", "uva"],
    "V": ["vaca", "vela", "ventana"],
    "W": ["wifi", "waffle"],
    "X": ["xilófono"],
    "Y": ["yoyo", "yegua", "yema"],
    "Z": ["zapato", "zorro", "zanahoria"]
}

# Frases del juego
extras = {
    "intenta_otra_vez": "Intenta otra vez.",
    "vidas_terminadas": "¡Se acabaron tus vidas!",
    "felicidades": "¡Felicidades! Has terminado el abecedario.",
    "animo_tu_puedes": "¡Vamos, tú puedes!",
    "animo_no_te_rindas": "No te rindas.",
    "animo_intentalo_otra_vez": "Inténtalo otra vez.",
    "muy_bien": "¡Muy bien!"
}

for letra, palabras in datos.items():
    # pregunta
    txt = f"¿Cuál imagen empieza con la letra {letra}?"
    tts = gTTS(text=txt, lang="es", slow=False)
    tts.save(f"assets/audios/pregunta_{letra}.mp3")
    # palabras y correctos
    for palabra in palabras:
        # palabra sola
        tts = gTTS(text=palabra, lang="es", slow=False)
        tts.save(f"assets/audios/{letra}_{palabra}.mp3")
        # correcto
        txt2 = f"¡Correcto! {letra} de {palabra}"
        tts = gTTS(text=txt2, lang="es", slow=False)
        tts.save(f"assets/audios/correcto_{letra}_{palabra}.mp3")
         # minijuego arrastrar
        texto_mini = f"¿A qué letra corresponde {palabra}? Arrástrala."
        tts = gTTS(text=texto_mini, lang="es", slow=False)
        tts.save(f"assets/audios/minijuego_{letra}_{palabra}.mp3")

# extras
for name, text in extras.items():
    tts = gTTS(text=text, lang="es", slow=False)
    tts.save(f"assets/audios/{name}.mp3")

print("✅ Se generaron todos los audios en assets/audios/")
