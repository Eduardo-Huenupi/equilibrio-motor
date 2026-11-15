"""Corta cada página en fragmentos con traslape, sin perder el número de página."""
from __future__ import annotations


def fragmentar(
    paginas: list[tuple[int, str]], palabras: int = 180, traslape: int = 30
) -> list[tuple[int, str]]:
    """Ventanas de `palabras` palabras que comparten `traslape` con la anterior.

    Un fragmento nunca cruza de una página a otra: así la cita siempre apunta a una página exacta.
    """
    if traslape >= palabras:
        raise ValueError("El traslape debe ser menor que el tamaño del fragmento.")
    salida: list[tuple[int, str]] = []
    paso = palabras - traslape
    for pagina, texto in paginas:
        lista = texto.split()
        inicio = 0
        while inicio < len(lista):
            salida.append((pagina, " ".join(lista[inicio : inicio + palabras])))
            if inicio + palabras >= len(lista):
                break
            inicio += paso
    return salida
