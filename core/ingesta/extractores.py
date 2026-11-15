"""Convierte archivos en una lista de (número de página, texto)."""
from __future__ import annotations

import io

FORMATOS = (".pdf", ".docx", ".txt", ".md")


class FormatoNoSoportado(ValueError):
    pass


def extraer_paginas(nombre: str, contenido: bytes) -> list[tuple[int, str]]:
    """Devuelve las páginas con texto de un archivo.

    - PDF: una entrada por página real.
    - DOCX: Word no guarda páginas, así que todo el documento queda como página 1.
    - TXT/MD: las páginas se separan con el carácter de salto de página (\\f).
    """
    ext = "." + nombre.lower().rsplit(".", 1)[-1] if "." in nombre else ""
    if ext == ".pdf":
        from pypdf import PdfReader

        lector = PdfReader(io.BytesIO(contenido))
        paginas = [(i, (p.extract_text() or "").strip()) for i, p in enumerate(lector.pages, 1)]
    elif ext == ".docx":
        from docx import Document

        doc = Document(io.BytesIO(contenido))
        paginas = [(1, "\n".join(p.text for p in doc.paragraphs).strip())]
    elif ext in (".txt", ".md"):
        texto = contenido.decode("utf-8", errors="replace")
        paginas = [(i, t.strip()) for i, t in enumerate(texto.split("\f"), 1)]
    else:
        raise FormatoNoSoportado(f"Formato no soportado: {nombre}. Usa {', '.join(FORMATOS)}.")
    return [(n, t) for n, t in paginas if t]
