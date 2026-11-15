import io

import pytest

from core.ingesta import extraer_paginas, fragmentar
from core.ingesta.extractores import FormatoNoSoportado


def test_txt_separa_paginas_por_salto():
    paginas = extraer_paginas("a.txt", "uno\fdos\f\ftres".encode())
    assert paginas == [(1, "uno"), (2, "dos"), (4, "tres")]  # la página vacía se omite sin correr la numeración


def test_docx_se_lee_como_pagina_unica():
    from docx import Document

    doc = Document()
    doc.add_paragraph("Primera línea del protocolo.")
    doc.add_paragraph("Segunda línea.")
    buf = io.BytesIO()
    doc.save(buf)
    assert extraer_paginas("p.docx", buf.getvalue()) == [(1, "Primera línea del protocolo.\nSegunda línea.")]


def test_pdf_conserva_numero_de_pagina():
    from pypdf import PdfWriter

    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    w.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    w.write(buf)
    assert extraer_paginas("vacio.pdf", buf.getvalue()) == []  # páginas sin texto no generan fragmentos


def test_formato_desconocido_se_rechaza():
    with pytest.raises(FormatoNoSoportado):
        extraer_paginas("planilla.xlsx", b"x")


def test_fragmentos_no_cruzan_paginas_y_se_traslapan():
    paginas = [(1, " ".join(f"a{i}" for i in range(25))), (2, "b0 b1 b2")]
    frags = fragmentar(paginas, palabras=10, traslape=2)
    assert [p for p, _ in frags] == [1, 1, 1, 2]
    assert frags[0][1].split()[-2:] == frags[1][1].split()[:2]
    assert frags[2][1].split()[-1] == "a24"
    assert all("b" not in t for p, t in frags if p == 1)


def test_traslape_invalido():
    with pytest.raises(ValueError):
        fragmentar([(1, "x")], palabras=5, traslape=5)
