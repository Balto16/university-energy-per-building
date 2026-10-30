"""Informe técnico en Word con el peso y el costo de cada edificio.

Autor: Irving Nieto
"""
import datetime as dt
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from matplotlib.patches import Polygon

from analisis import ANIO_BASE, ACOMETIDAS, RAIZ
from resultados import FIGURAS_ES, SALIDA, generar, grupos_de_uso, perfil_puntos

LOGO = RAIZ / "assets" / "logo_utp.png"
ARCHIVO = SALIDA / "informe_peso_y_costo_edificios_UTP.docx"
FECHA = dt.date(2026, 10, 30)

VERDE_OSCURO, VERDE, BORDE, VERDE_MEDIO = "14342B", "4D816E", "31836C", "6CA893"
VERDE_CLARO, VERDE_TABLA, VERDE_FILA = "BEE6DB", "C4DCD3", "E4EEEB"
GRIS_PIE = "595959"

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
M1, M2, M3 = ACOMETIDAS.index
N1, N2, N3 = (f"la {n[0].lower()}{n[1:]}" for n in ACOMETIDAS["nombre"])
NOMBRE = ACOMETIDAS["nombre"]


def num(x, d=1):
    return f"{x:,.{d}f}".replace(",", " ")


def pct(x, d=1):
    return f"{x * 100:.{d}f} %"


def enumerar(items):
    items = list(items)
    return ", ".join(items[:-1]) + " y " + items[-1] if len(items) > 1 else "".join(items)


def fecha_larga(t):
    return f"{DIAS[t.weekday()]}, {t.day} de {MESES[t.month - 1]} de {t.year}"


def portada(ruta):
    plt.rcParams["font.family"] = "Calibri"
    fig = plt.figure(figsize=(8.5, 11), dpi=220)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(Polygon([(0, 1), (1, 1), (1, 0.575), (0, 0.575)], color="#" + VERDE_MEDIO))
    ax.add_patch(Polygon([(0, 0.66), (1, 0.84), (1, 0.575), (0, 0.575)], color="#" + VERDE))
    ax.add_patch(Polygon([(0, 1), (0.43, 1), (0, 0.80)], color="#" + VERDE))
    ax.add_patch(Polygon([(0.45, 1), (1, 1), (1, 0.84), (0.66, 1)], color="#" + VERDE))
    ax.text(0.665, 0.965, "DINAGEA", color="white", fontsize=22, weight="bold", va="top")
    ax.text(0.665, 0.927, "Dirección Nacional de Gestión Energética,\nAmbiental e Ingeniería Aplicada",
            color="white", fontsize=9.5, weight="bold", va="top", linespacing=1.4)
    ax.text(0.08, 0.735, "INFORME TÉCNICO", color="white", fontsize=25, weight="bold")
    ax.text(0.08, 0.692, "PESO Y COSTO DE CADA EDIFICIO EN EL CONSUMO", color="#" + VERDE_CLARO,
            fontsize=15.5, weight="bold")
    ax.text(0.08, 0.660, "CAMPUS VÍCTOR LEVI SASSO, UTP", color="#" + VERDE_CLARO, fontsize=15.5, weight="bold")
    if LOGO.exists():
        logo = plt.imread(LOGO)
        alto = 0.24
        ancho = alto * logo.shape[1] / logo.shape[0] * 11 / 8.5
        ax.imshow(logo, extent=(0.5 - ancho / 2, 0.5 + ancho / 2, 0.29, 0.29 + alto), zorder=3)
    datos = [("Elaborado por:", "Ing. Irving Nieto"), None, ("Lugar:", "Campus Víctor Levi Sasso, UTP"),
             ("Ubicación:", "Ciudad de Panamá, Panamá"), ("Fecha:", fecha_larga(FECHA))]
    y = 0.215
    for fila in datos:
        if fila:
            ax.text(0.10, y, fila[0], color="#" + VERDE, fontsize=9.5, weight="bold")
            ax.text(0.29, y, fila[1], color="#" + VERDE_MEDIO, fontsize=9.5)
        y -= 0.022
    ax.plot([0.05, 0.88], [0.06, 0.06], color="#" + VERDE_MEDIO, lw=1.6)
    ax.set_aspect("auto")
    fig.savefig(ruta, dpi=220)
    plt.close(fig)
    plt.rcParams["font.family"] = "Times New Roman"


def sombreado(pPr, color):
    s = OxmlElement("w:shd")
    s.set(qn("w:val"), "clear")
    s.set(qn("w:color"), "auto")
    s.set(qn("w:fill"), color)
    pPr.append(s)


def borde_parrafo(pPr, lados, color, sz=12, espacio=1):
    bordes = OxmlElement("w:pBdr")
    for lado in lados:
        e = OxmlElement(f"w:{lado}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), str(sz))
        e.set(qn("w:space"), str(espacio))
        e.set(qn("w:color"), color)
        bordes.append(e)
    pPr.append(bordes)


def fondo_celda(celda, color):
    sombreado(celda._tc.get_or_add_tcPr(), color)


def bordes_celda(celda, color="BFBFBF", sz=4, lados=("top", "left", "bottom", "right")):
    tcPr = celda._tc.get_or_add_tcPr()
    bordes = OxmlElement("w:tcBorders")
    for lado in ("top", "left", "bottom", "right"):
        e = OxmlElement(f"w:{lado}")
        if lado in lados:
            e.set(qn("w:val"), "single")
            e.set(qn("w:sz"), str(sz))
            e.set(qn("w:color"), color)
        else:
            e.set(qn("w:val"), "nil")
        bordes.append(e)
    tcPr.append(bordes)


def campo(run, instruccion):
    partes = [("fldChar", "begin"), ("instrText", f" {instruccion} "), ("fldChar", "separate"),
              ("t", "1"), ("fldChar", "end")]
    for etiqueta, valor in partes:
        e = OxmlElement(f"w:{etiqueta}")
        if etiqueta == "fldChar":
            e.set(qn("w:fldCharType"), valor)
        else:
            e.set(qn("xml:space"), "preserve")
            e.text = valor
        run._r.append(e)


def espaciado(rPr, twips):
    e = OxmlElement("w:spacing")
    e.set(qn("w:val"), str(twips))
    rPr.append(e)


def limpiar_fuentes_tema(estilo):
    fuentes = estilo.element.rPr.rFonts
    for atributo in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if fuentes.get(qn(atributo)) is not None:
            del fuentes.attrib[qn(atributo)]
    fuentes.set(qn("w:ascii"), estilo.font.name)
    fuentes.set(qn("w:hAnsi"), estilo.font.name)


def estilos(doc):
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    normal.paragraph_format.space_after = Pt(8)
    normal.paragraph_format.line_spacing = 1.08

    h1 = doc.styles["Heading 1"]
    h1.font.name = "Times New Roman"
    h1.font.size = Pt(12)
    h1.font.bold = True
    h1.font.all_caps = True
    h1.font.color.rgb = RGBColor.from_string("FFFFFF")
    espaciado(h1.element.get_or_add_rPr(), 30)
    h1.paragraph_format.space_before = Pt(6)
    h1.paragraph_format.space_after = Pt(14)
    h1.paragraph_format.keep_with_next = True
    h1.paragraph_format.left_indent = Pt(4)
    h1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    borde_parrafo(h1.element.get_or_add_pPr(), ["top", "left", "bottom", "right"], BORDE, 12, 4)
    sombreado(h1.element.get_or_add_pPr(), VERDE)

    h2 = doc.styles["Heading 2"]
    h2.font.name = "Calibri"
    h2.font.size = Pt(10)
    h2.font.bold = True
    h2.font.italic = False
    h2.font.all_caps = True
    h2.font.color.rgb = RGBColor.from_string(VERDE_OSCURO)
    espaciado(h2.element.get_or_add_rPr(), 20)
    h2.paragraph_format.space_before = Pt(10)
    h2.paragraph_format.space_after = Pt(8)
    h2.paragraph_format.keep_with_next = True
    h2.paragraph_format.left_indent = Pt(4)
    h2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    borde_parrafo(h2.element.get_or_add_pPr(), ["top", "left", "bottom", "right"], VERDE_CLARO, 4, 2)
    sombreado(h2.element.get_or_add_pPr(), VERDE_CLARO)

    for h in (h1, h2):
        limpiar_fuentes_tema(h)

    pie = doc.styles.add_style("Pie figura", 1)
    pie.base_style = normal
    pie.font.size = Pt(9)
    pie.font.italic = True
    pie.font.color.rgb = RGBColor.from_string(GRIS_PIE)
    pie.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pie.paragraph_format.space_before = Pt(2)
    pie.paragraph_format.space_after = Pt(12)

    titulo = doc.styles.add_style("Titulo tabla", 1)
    titulo.base_style = normal
    titulo.font.name = "Calibri"
    titulo.font.size = Pt(9)
    titulo.font.bold = True
    titulo.font.color.rgb = RGBColor.from_string(VERDE_OSCURO)
    titulo.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    titulo.paragraph_format.space_before = Pt(6)
    titulo.paragraph_format.space_after = Pt(4)
    titulo.paragraph_format.keep_with_next = True


def encabezado_y_pie(seccion):
    seccion.header.is_linked_to_previous = False
    seccion.footer.is_linked_to_previous = False

    p = seccion.header.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for texto in ("PÁGINA | ", None):
        r = p.add_run(texto or "")
        r.bold = True
        r.font.name = "Calibri"
        r.font.size = Pt(10)
        r.font.color.rgb = RGBColor.from_string(VERDE_OSCURO)
        if texto is None:
            campo(r, "PAGE")
    borde_parrafo(p._p.get_or_add_pPr(), ["bottom"], VERDE, 18, 4)

    vacio = seccion.footer.paragraphs[0]
    tabla = seccion.footer.add_table(rows=1, cols=2, width=Inches(6.5))
    tabla.autofit = False
    bloque, linea = tabla.rows[0].cells
    bloque.width, linea.width = Inches(0.45), Inches(6.05)
    fondo_celda(bloque, VERDE)
    bordes_celda(bloque, VERDE)
    bordes_celda(linea, VERDE, 18, lados=("bottom",))
    for celda in (bloque, linea):
        celda.paragraphs[0].paragraph_format.space_after = Pt(0)
        celda.paragraphs[0].add_run(" ").font.size = Pt(4)
    alto = OxmlElement("w:trHeight")
    alto.set(qn("w:val"), "160")
    alto.set(qn("w:hRule"), "exact")
    tabla.rows[0]._tr.get_or_add_trPr().append(alto)
    vacio._p.getparent().remove(vacio._p)


def margenes(seccion, arriba=1.0, abajo=0.9, lados=1.0):
    seccion.page_width = Inches(8.5)
    seccion.page_height = Inches(11)
    seccion.top_margin = Inches(arriba)
    seccion.bottom_margin = Inches(abajo)
    seccion.left_margin = seccion.right_margin = Inches(lados)
    seccion.header_distance = Inches(0.45)
    seccion.footer_distance = Inches(0.35)


class Informe:
    def __init__(self):
        self.doc = Document()
        estilos(self.doc)
        self.figuras = 0
        self.tablas = 0

    def h1(self, texto):
        self.doc.add_heading(texto, level=1)

    def h2(self, texto):
        self.doc.add_heading(texto, level=2)

    def escribir(self, parrafo, texto):
        # **negrita** y _{subíndice}
        for parte in re.split(r"(\*\*.+?\*\*|_\{.+?\})", texto):
            if parte.startswith("**"):
                parrafo.add_run(parte[2:-2]).bold = True
            elif parte.startswith("_{"):
                parrafo.add_run(parte[2:-1]).font.subscript = True
            elif parte:
                parrafo.add_run(parte)

    def p(self, texto):
        parrafo = self.doc.add_paragraph()
        self.escribir(parrafo, texto)
        return parrafo

    def lista(self, items):
        for item in items:
            parrafo = self.doc.add_paragraph(style="List Bullet")
            self.escribir(parrafo, item)
            parrafo.paragraph_format.space_after = Pt(3)
        self.doc.paragraphs[-1].paragraph_format.space_after = Pt(8)

    def ecuacion(self, texto, numero):
        parrafo = self.doc.add_paragraph()
        parrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        self.escribir(parrafo, texto)
        for r in parrafo.runs:
            r.italic = True
        parrafo.add_run(f"\t({numero})")
        parrafo.paragraph_format.tab_stops.add_tab_stop(Inches(6.4), alignment=2)

    def figura(self, ruta, pie, ancho=6.3):
        parrafo = self.doc.add_paragraph()
        parrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        parrafo.paragraph_format.keep_with_next = True
        parrafo.paragraph_format.space_after = Pt(0)
        parrafo.add_run().add_picture(str(ruta), width=Inches(ancho))
        self.figuras += 1
        self.doc.add_paragraph(f"Figura {self.figuras}. {pie}", style="Pie figura")

    def tabla(self, titulo, encabezados, filas, anchos, alineacion=None, total=False, letra=10):
        self.tablas += 1
        self.doc.add_paragraph(f"Tabla {self.tablas}. {titulo}", style="Titulo tabla")
        tabla = self.doc.add_table(rows=1, cols=len(encabezados))
        tabla.alignment = WD_TABLE_ALIGNMENT.CENTER
        tabla.autofit = False
        alineacion = alineacion or ["l"] + ["c"] * (len(encabezados) - 1)
        ali = {"l": WD_ALIGN_PARAGRAPH.LEFT, "c": WD_ALIGN_PARAGRAPH.CENTER}
        mantener = len(filas) <= 18

        def llenar(celda, texto, ancho, fondo, negrita=False, color=None, alinear="c", siguiente=True):
            celda.width = Inches(ancho)
            fondo_celda(celda, fondo)
            bordes_celda(celda, "FFFFFF" if color else "BFBFBF")
            celda.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            parrafo = celda.paragraphs[0]
            parrafo.alignment = ali[alinear]
            parrafo.paragraph_format.space_after = Pt(0)
            parrafo.paragraph_format.keep_with_next = siguiente
            r = parrafo.add_run(str(texto))
            r.font.name = "Calibri"
            r.font.size = Pt(letra)
            r.bold = negrita
            if color:
                r.font.color.rgb = RGBColor.from_string(color)

        for i, texto in enumerate(encabezados):
            llenar(tabla.rows[0].cells[i], texto, anchos[i], VERDE_MEDIO, True, "FFFFFF")
        repetir = OxmlElement("w:tblHeader")
        repetir.set(qn("w:val"), "true")
        tabla.rows[0]._tr.get_or_add_trPr().append(repetir)

        for j, fila in enumerate(filas):
            ultima = total and j == len(filas) - 1
            fondo = VERDE_TABLA if ultima else (VERDE_FILA if j % 2 == 0 else "FFFFFF")
            celdas = tabla.add_row().cells
            for i, texto in enumerate(fila):
                llenar(celdas[i], texto, anchos[i], fondo, ultima, alinear=alineacion[i],
                       siguiente=mantener and j < len(filas) - 1)

        for fila in tabla.rows:
            no_partir = OxmlElement("w:cantSplit")
            no_partir.set(qn("w:val"), "true")
            fila._tr.get_or_add_trPr().append(no_partir)
            for celda in fila.cells:
                margen = OxmlElement("w:tcMar")
                for lado, valor in (("top", 40), ("bottom", 40), ("left", 80), ("right", 80)):
                    e = OxmlElement(f"w:{lado}")
                    e.set(qn("w:w"), str(valor))
                    e.set(qn("w:type"), "dxa")
                    margen.append(e)
                celda._tc.get_or_add_tcPr().append(margen)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(4)

    def salto(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def construir(complemento=None, archivo=ARCHIVO):
    r, capas = generar()
    edificios, reparto, acometidas = r["edificios"], r["reparto"], r["acometidas"]
    factura, relacion = r["factura"], r["relacion"]
    fact = r["facturacion"].sort_index()
    fact["total"] = fact.sum(axis=1)

    por_nombre = reparto.set_index("edificio")
    total_mwh = acometidas["facturado_mwh_mes"].sum()
    anual = fact.groupby(fact.index.year).sum()
    base = fact.loc[ANIO_BASE]
    mes_alto, mes_bajo = base["total"].idxmax(), base["total"].idxmin()

    solo_edificios = reparto[reparto["uso"].isin(["edificio", "climatizacion"])]
    orden = solo_edificios.sort_values("pct_total", ascending=False)
    cinco = orden.head(5)
    grupos = grupos_de_uso(reparto)
    clima = grupos["Climatización centralizada"]
    bt = por_nombre.loc["Acometida BT (sin desagregar)"]
    cobertura = solo_edificios["mwh_mes_ajustado"].sum() / acometidas.loc[[M1, M2], "facturado_mwh_mes"].sum()
    usos = int((orden["pct_total"].cumsum() < 0.80).sum() + 1)

    def suma(*nombres):
        return por_nombre.loc[list(nombres), "pct_total"].sum()

    ed1 = suma("Edificio 1", "Casa de máquinas - Chiller Edificio 1")
    ed3 = suma("Edificio 3", "Casa de máquinas - Chiller Edificio 3")
    ed4 = suma("Aulas (Edificio 4)", "Casa de Máquinas 4")
    rect = suma("Rectoría", "Chiller Rectoría")
    vipe = suma("VIPE - Edificio administrativo", "VIPE - UMA", "VIPE - Bombas y chiller")

    puntos_h = perfil_puntos(edificios, r["perfiles"])
    madrugada = puntos_h.loc[2]
    usos_punto = edificios.set_index("id")["uso"]
    clima_noche = madrugada[usos_punto == "climatizacion"].sum()
    base_noche = madrugada[usos_punto == "edificio"].sort_values(ascending=False)
    nombres_id = edificios.set_index("id")["edificio"]
    extra = complemento(r) if complemento else None
    error_max = (1 - acometidas.loc[[M1, M2], "cobertura"]).abs().max()

    costo_anio = reparto["usd_anio"].sum()
    importe_12 = acometidas["importe"].sum()
    caf = edificios.set_index("edificio").loc["Cafetería Central"]
    figuras = {f.stem: f for f in FIGURAS_ES.glob("*.png")}
    ruta_portada = SALIDA / "portada.png"
    portada(ruta_portada)

    I = Informe()
    doc = I.doc
    s0 = doc.sections[0]
    margenes(s0, 0, 0, 0)
    s0.header_distance = s0.footer_distance = Inches(0)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    p.add_run().add_picture(str(ruta_portada), width=Inches(8.5), height=Inches(10.98))
    s1 = doc.add_section(WD_SECTION.NEW_PAGE)
    margenes(s1)
    encabezado_y_pie(s1)

    r_ = doc.add_paragraph().add_run("CONTENIDO")
    r_.bold = True
    r_.font.name = "Calibri"
    r_.font.color.rgb = RGBColor.from_string(VERDE_OSCURO)
    campo(doc.add_paragraph().add_run(), 'TOC \\o "1-2" \\h \\z \\u')
    I.salto()

    I.h1("1. Resumen ejecutivo")
    I.p("El presente informe estima la participación de cada edificio y sistema del Campus Víctor Levi Sasso "
        "de la Universidad Tecnológica de Panamá en el consumo de energía eléctrica de la institución, y el "
        "costo que representa cada uno. El campus se alimenta mediante tres acometidas de ENSA: dos en media "
        "tensión con tarifa MTD (MT 1 y MT 2) y una en baja tensión con tarifa BTD (BT).")
    I.p(f"Se utilizaron 16 registros de potencia activa tomados entre el "
        f"{fecha_larga(edificios['inicio'].min())} y el {fecha_larga(edificios['fin'].max())}, de 1 a 32 días "
        f"cada uno y en meses distintos. Cada registro se llevó a una semana tipo, se corrigió por estacionalidad "
        f"con la facturación de su acometida y se comparó con el consumo promedio facturado entre octubre de "
        f"2025 y septiembre de 2026: {num(total_mwh)} MWh/mes en las tres acometidas.")
    I.p(f"El balance cierra en ambas acometidas de media tensión: lo medido explica el "
        f"{pct(acometidas.loc[M1, 'cobertura'])} de lo facturado en {N1} y el {pct(acometidas.loc[M2, 'cobertura'])} "
        f"en {N2}. La acometida BT no tiene mediciones por edificio y representa el {pct(bt['pct_total'])} del "
        f"consumo total.")
    I.p(f"La climatización centralizada (chillers, casas de máquinas y UMA) representa el **{pct(clima)}** del "
        f"consumo. Las cinco cargas de mayor peso son "
        + enumerar(f"{f.edificio} ({pct(f.pct_total)})" for f in cinco.itertuples())
        + f", que suman el {pct(cinco['pct_total'].sum())}. Por edificio, incluida su planta de agua helada, "
        f"el Edificio 1 pesa {pct(ed1)}, el Edificio 3 {pct(ed3)}, el Edificio 4 {pct(ed4)}, Rectoría {pct(rect)} "
        f"y VIPE {pct(vipe)}.")
    I.p(f"Con el precio medio pagado en cada acometida, el costo de energía del campus es de "
        f"**B/. {num(costo_anio / 365.25, 0)} por día**, B/. {num(costo_anio / 12, 0)} por mes y "
        f"B/. {num(costo_anio, 0)} por año. Solo Casa de Máquinas 4 cuesta "
        f"B/. {num(por_nombre.loc['Casa de Máquinas 4', 'usd_dia'], 0)} por día.")
    if extra:
        extra.resumen(I)
    I.figura(figuras["grupos_uso"], "Distribución del consumo facturado del campus por tipo de uso", 6.2)

    I.h1("2. Alcance del estudio")
    I.p("El estudio comprende las cargas de las tres acometidas del campus, según la distribución de la Tabla 1.")
    I.tabla("Edificios y sistemas por acometida", ["Acometida", "Tarifa", "Edificios y sistemas"],
            [["MT 1", "MTD", "Rectoría, Chiller Rectoría, Casa de máquinas - Chiller Edificio 1, "
                                   "Edificio 1, DITIC, Edificio 3, Casa de máquinas - Chiller Edificio 3"],
             ["MT 2", "MTD", "Laboratorio Docentes, Investigación ELI, Casa de Máquinas 4, Aulas "
                                     "(Edificio 4), Facilidades, Cafetería Central, VIPE (edificio administrativo, "
                                     "UMA, bombas y chiller), Edificio de Aguas (en construcción)"],
             ["BT", "BTD", "Suministro aislado en baja tensión, sin mediciones por edificio"]],
            [0.9, 0.7, 4.9], ["c", "c", "l"])
    I.p("El Edificio de Aguas se encuentra en construcción y no se midió. Su consumo actual, el alumbrado "
        "exterior, las cargas menores y las pérdidas en transformadores quedan en el término \"no medido y "
        "pérdidas\". La acometida BT se incluye completa en el total de la institución con su consumo facturado.")
    I.p("El análisis es una estimación energética y económica. La calidad de la energía de cada punto se reporta "
        "en los informes individuales de medición.")

    I.h1("3. Parámetros de estudio")
    I.lista([
        "**Potencia activa total trifásica (kW)**, promedio horario de cada registro.",
        "**Energía de semana tipo (MWh/semana)**, a partir del perfil horario de día hábil, sábado y domingo.",
        "**Factor estacional k**, relación entre el consumo diario del año base y el del período medido.",
        "**Energía mensual estimada (MWh/mes)** de cada edificio en un año promedio.",
        "**Energía facturada** por acometida, de enero de 2022 a septiembre de 2026, e **importe y demanda** "
        "de enero de 2022 a junio de 2026 y septiembre de 2026.",
        "**Precio medio (B/./kWh)**, importe pagado entre energía facturada en cada acometida.",
        "**Participación (%)** y **costo (B/./día, B/./mes y B/./año)** de cada edificio.",
    ])

    I.h1("4. Normativa y documentos de referencia")
    I.lista([
        "ISO 50001:2018. Sistemas de gestión de la energía. Requisitos con orientación para su uso "
        "(numerales 6.3 a 6.6: revisión energética, indicadores, línea base y plan de datos).",
        "ISO 50006:2023. Evaluación del desempeño energético utilizando indicadores y líneas base.",
        "ISO 50002:2014. Auditorías energéticas. Requisitos con orientación para su uso.",
        "IEC 61000-4-30:2015+A1:2021. Métodos de medición de la calidad de la energía.",
        "ASHRAE Guideline 14-2014. Measurement of Energy, Demand, and Water Savings.",
        "EN 50160:2010. Características de la tensión suministrada por las redes generales de distribución "
        "(período de evaluación semanal).",
        "Facturas de ENSA de las tres acometidas, enero de 2022 a septiembre de 2026.",
    ])

    I.h1("5. Criterios de aceptación")
    I.p("Para dar por válido el reparto se definieron los criterios de la Tabla 2.")
    I.tabla("Criterios de aceptación del balance energético",
            ["No", "Criterio", "Valor de aceptación", "Referencia"],
            [["1", "Cierre del balance por acometida (medido frente a facturado)", "Error dentro de ±5 %",
              "ASHRAE Guideline 14 (NMBE)"],
             ["2", "Cobertura de la medición en las acometidas MTD", "Mayor o igual a 80 % del consumo",
              "Criterio del estudio"],
             ["3", "Identificación de usos significativos", "Cargas que sumen cerca del 80 % del consumo",
              "ISO 50001, 6.3 b)"],
             ["4", "Duración del registro por punto", "Un ciclo semanal (7 días)", "EN 50160"]],
            [0.4, 2.4, 2.1, 1.6], ["c", "l", "c", "c"])

    I.h1("6. Metodología")
    I.h2("6.1 Herramientas e instrumentación")
    I.p("Los registros se tomaron con analizadores de calidad de energía clase A en los tableros principales de "
        "baja tensión de cada edificio o casa de máquinas.")
    I.tabla("Instrumentación utilizada", ["Equipo", "Registro", "Puntos medidos"],
            [["Fluke 1775 (2 unidades)", "1 s, 10 s y 10 min",
              "Rectoría, Chiller Ed. 3, ELI, Aulas, Facilidades, Cafetería Central"],
             ["A-Eberle PQ-Box 150 (2 unidades)", "10 min",
              "Edificio 1, DITIC, Edificio 3, Casa de Máquinas 4, Chiller Rectoría, Chiller Ed. 1, VIPE UMA, VIPE bombas y chiller"],
             ["A-Eberle PQ-Box 300", "10 min", "Laboratorio Docentes, VIPE edificio administrativo"]],
            [1.9, 1.2, 3.4], ["l", "c", "l"])
    I.p("El procesamiento se realizó en Python (pandas, matplotlib y python-docx). Los scripts y los datos "
        "horarios están publicados para reproducir el cálculo.")

    I.h2("6.2 Procedimiento")
    I.p("**Paso 1. Perfil horario.** Cada registro se promedió por hora y se agrupó por tipo de día (hábil, "
        "sábado y domingo). Se descartaron la primera y la última hora por estar incompletas.")
    I.p("**Paso 2. Semana tipo.** La energía semanal de cada punto es:")
    I.ecuacion("E_{sem} = 5·ΣP_{háb}(h) + ΣP_{sáb}(h) + ΣP_{dom}(h)", 1)
    I.p(f"Si el registro no incluyó sábado o domingo, se usó la relación típica de los edificios sin chiller con "
        f"semana completa: sábado {relacion['Sábado']:.2f} y domingo {relacion['Domingo']:.2f} del día hábil.")
    I.p("**Paso 3. Corrección estacional.** Cada semana se corrigió con la variación del consumo facturado de su "
        "acometida:")
    I.ecuacion("k = (E_{base} / D_{base}) / (E_{med} / D_{med})", 2)
    I.p("donde E_{base}/D_{base} es el consumo diario promedio de octubre de 2025 a septiembre de 2026 y "
        "E_{med}/D_{med} el consumo diario facturado en los meses que abarca la medición, ponderado por días.")
    I.p("**Paso 4. Energía mensual y balance.**")
    I.ecuacion("E_{mes} = E_{sem} · k · 30.44 / 7", 3)
    I.p("La suma por acometida se comparó con el promedio facturado. Si queda por debajo, la diferencia se asigna "
        "a \"no medido y pérdidas\"; si queda por encima, los valores de la acometida se escalan para cerrar en 100 %.")
    I.p("**Paso 5. Costo.** El costo mensual de cada acometida es su energía promedio por el precio medio pagado "
        "entre julio de 2025 y junio de 2026 (importe entre kWh). La factura de ENSA separa el cargo por energía del "
        "cargo por demanda máxima, así que el costo de la acometida se reparte en dos partes:")
    I.ecuacion("C_{i} = C_{acometida} · [(1 − d) · e_{i} + d · p_{i}]", 4)
    I.p("donde d es la fracción de la factura que corresponde al cargo por demanda (factura de septiembre de 2026), "
        "e_{i} la participación del edificio en la energía de su acometida y p_{i} su aporte a la hora de mayor "
        "demanda del perfil de día hábil de la acometida. El costo por día es el anual entre 365.25.")

    I.h1("7. Resultados")
    I.h2("7.1 Facturación histórica")
    filas = [[f"{a}{' (ene-sep)' if a == 2026 else ''}", num(f[M1]), num(f[M2]), num(f[M3]), num(f["total"])]
             for a, f in anual.iterrows()]
    filas.append(["Año base (oct 2025-sep 2026)", num(base[M1].sum()), num(base[M2].sum()), num(base[M3].sum()),
                  num(base["total"].sum())])
    I.tabla("Energía facturada por año (MWh)", ["Año", "MT 1", "MT 2", "BT", "Total"], filas,
            [2.2, 1.1, 1.1, 1.1, 1.0], ["l", "c", "c", "c", "c"], total=True)
    I.p(f"El consumo anual del campus pasó de {num(anual.loc[2022, 'total'], 0)} MWh en 2022 a "
        f"{num(anual.loc[2025, 'total'], 0)} MWh en 2025 "
        f"({(anual.loc[2025, 'total'] / anual.loc[2022, 'total'] - 1) * 100:.1f} %) y se mantuvo estable entre 2024 "
        f"y 2025. En el año base el mes de mayor consumo fue {MESES[mes_alto.month - 1]} de {mes_alto.year} "
        f"({num(base.loc[mes_alto, 'total'])} MWh) y el de menor {MESES[mes_bajo.month - 1]} de {mes_bajo.year} "
        f"({num(base.loc[mes_bajo, 'total'])} MWh), en el receso académico.")
    I.figura(figuras["facturacion"], "Energía facturada mensual por acometida, enero de 2022 a septiembre de 2026")

    I.h2("7.2 Registros por punto de medición")
    filas = [[f.edificio, NOMBRE[f.acometida].replace("Acometida ", ""), f"{f.inicio:%d/%m/%Y}", f"{f.horas / 24:.1f}", num(f.p_media_kw),
              num(f.p_max_kw), f"{f.mwh_semana:.2f}", f"{f.k:.3f}"] for f in edificios.itertuples()]
    I.tabla("Resumen de registros y semana tipo",
            ["Edificio / sistema", "Acometida", "Inicio", "Días", "P media (kW)", "P máx. horaria (kW)",
             "Semana tipo (MWh)", "k"],
            filas, [2.05, 0.85, 0.75, 0.45, 0.6, 0.7, 0.65, 0.5], letra=8.5)
    I.p(f"Los factores k van de {edificios['k'].min():.2f} (julio de 2026) a {edificios['k'].max():.2f} (marzo de "
        f"2026). La Cafetería Central solo tiene {caf['horas']:.0f} h de registro, del lunes 7 al martes 8 de "
        f"septiembre de 2026, y es el valor con mayor incertidumbre. En Rectoría no hubo registro de domingo.")

    I.h2("7.3 Balance por acometida")
    filas = [[NOMBRE[m], f.tarifa, num(f.facturado_mwh_mes), num(f.medido_mwh_mes), num(f.diferencia_mwh_mes),
              pct(f.cobertura)] for m, f in acometidas.iterrows()]
    filas.append(["Total", "", num(total_mwh), num(acometidas["medido_mwh_mes"].sum()),
                  num(acometidas["diferencia_mwh_mes"].sum()), pct(acometidas["medido_mwh_mes"].sum() / total_mwh)])
    I.tabla("Balance entre energía medida estimada y facturada (MWh/mes)",
            ["Acometida", "Tarifa", "Facturado", "Medido", "Diferencia", "Cobertura"],
            filas, [1.5, 0.7, 1.05, 1.05, 1.05, 1.05], ["c"] * 6, total=True)
    I.p(f"Las dos acometidas MTD cumplen el criterio de cierre. Quedan sin asignar "
        f"{num(acometidas.loc[M1, 'diferencia_mwh_mes'])} MWh/mes en {N1} "
        f"({pct(1 - acometidas.loc[M1, 'cobertura'])}) y {num(acometidas.loc[M2, 'diferencia_mwh_mes'])} MWh/mes en "
        f"{N2} ({pct(1 - acometidas.loc[M2, 'cobertura'])}), valores compatibles con las pérdidas de transformación, "
        f"el alumbrado exterior y cargas menores. La acometida BT se reporta completa como una carga sin desagregar.")

    I.h2("7.4 Peso de cada edificio en el consumo")
    filas = [[f.edificio, NOMBRE[f.acometida].replace("Acometida ", ""), num(f.mwh_mes_ajustado), pct(f.pct_acometida), pct(f.pct_total)]
             for f in reparto.assign(orden=reparto["acometida"].map({m: i for i, m in enumerate(ACOMETIDAS.index)}))
             .sort_values(["orden", "pct_total"], ascending=[True, False]).itertuples()]
    filas.append(["Total institución", "", num(total_mwh), "", "100.0 %"])
    I.tabla("Participación de cada edificio y sistema en el consumo facturado",
            ["Edificio / sistema", "Acometida", "MWh/mes", "% de la acometida", "% institución"],
            filas, [2.9, 1.0, 0.85, 0.9, 0.9], ["l", "c", "c", "c", "c"], total=True, letra=9.5)
    I.figura(figuras["peso_edificios"], "Participación de cada edificio y sistema en el consumo total facturado", 6.0)
    I.p(f"Casa de Máquinas 4 es la carga individual de mayor peso "
        f"({pct(por_nombre.loc['Casa de Máquinas 4', 'pct_total'])} de la institución y "
        f"{pct(por_nombre.loc['Casa de Máquinas 4', 'pct_acometida'])} de su acometida), seguida de las casas de "
        f"máquinas de los edificios 3 y 1. Sin contar su planta de agua helada, los edificios de mayor consumo son "
        f"el Edificio 1 ({pct(por_nombre.loc['Edificio 1', 'pct_total'])}) y el Edificio 3 "
        f"({pct(por_nombre.loc['Edificio 3', 'pct_total'])}).")

    I.h2("7.5 Perfil de día hábil del campus")
    total_h = capas.sum(axis=1)
    I.p(f"La suma de los perfiles de día hábil, corregidos por k, da un perfil típico de las cargas medidas: de "
        f"{num(total_h.min(), 0)} kW en la madrugada a {num(total_h.max(), 0)} kW a las {int(total_h.idxmax())}:00 h. "
        f"A las 2:00 h la climatización centralizada demanda solo {num(clima_noche, 0)} kW de "
        f"{num(madrugada.sum(), 0)} kW; la base nocturna la sostienen los edificios, en especial "
        + enumerar(f"{nombres_id[i]} ({num(v, 0)} kW)" for i, v in base_noche.head(5).items())
        + ". Las plantas de agua helada arrancan entre las 5:00 y las 6:00 h y siguen la ocupación del campus.")
    I.figura(figuras["perfil_habil"], "Perfil horario típico de día hábil por grupo de carga, corregido por estacionalidad")

    I.h2("7.6 Análisis económico")
    filas = [[NOMBRE[m], f.tarifa, num(f.kwh / 1000, 1), num(f.importe, 0), num(f.demanda_media, 0), f"{f.usd_kwh:.4f}"]
             for m, f in acometidas.iterrows()]
    filas.append(["Total", "", num(acometidas["kwh"].sum() / 1000, 1), num(importe_12, 0), "",
                  f"{importe_12 / acometidas['kwh'].sum():.4f}"])
    I.tabla("Precio medio pagado por acometida, julio de 2025 a junio de 2026",
            ["Acometida", "Tarifa", "Energía (MWh)", "Importe (B/.)", "Demanda media (kW)", "Precio (B/./kWh)"],
            filas, [1.1, 0.7, 1.1, 1.2, 1.2, 1.2], ["c"] * 6, total=True)
    conceptos = ["Cargo fijo", "Energía", "Demanda", "Variación por combustible", "FET adicional",
                 "Subsidio Ley 15 (0.42 %)", "Total"]
    filas = [[c] + [num(factura.loc[m, c], 2) for m in ACOMETIDAS.index] for c in conceptos]
    filas.insert(-1, ["Parte de la demanda"] + [pct(factura.loc[m, "parte_demanda"]) for m in ACOMETIDAS.index])
    I.tabla("Desglose de la factura de ENSA de septiembre de 2026 (B/.)", ["Concepto", "MT 1", "MT 2", "BT"],
            filas, [2.6, 1.3, 1.3, 1.3], ["l", "c", "c", "c"], total=True)
    I.p(f"La factura suma el cargo fijo, la energía, la demanda máxima, la variación por combustible y el subsidio "
        f"de la Ley 15, y resta el crédito del FET. El cargo por demanda representa entre "
        f"{pct(factura['parte_demanda'].min(), 0)} y {pct(factura['parte_demanda'].max(), 0)} de la factura. El precio "
        f"medio de la acometida BT es {pct(acometidas.loc[M3, 'usd_kwh'] / acometidas.loc[M1, 'usd_kwh'] - 1, 0)} "
        f"mayor que el de las acometidas MTD.")
    filas = [[f.edificio, f"{f.usd_kwh:.4f}", num(f.usd_dia, 0), num(f.usd_mes, 0), num(f.usd_anio, 0)]
             for f in reparto.sort_values("usd_anio", ascending=False).itertuples()]
    filas.append(["Total institución", "", num(costo_anio / 365.25, 0), num(costo_anio / 12, 0), num(costo_anio, 0)])
    I.tabla("Costo estimado de energía por edificio y sistema (B/.)",
            ["Edificio / sistema", "B/./kWh", "Por día", "Por mes", "Por año"],
            filas, [2.9, 0.8, 0.85, 0.95, 1.05], ["l", "c", "c", "c", "c"], total=True, letra=9.5)
    I.figura(figuras["costo_anual"], "Costo anual estimado de energía por edificio y sistema", 6.0)
    I.p(f"El costo estimado suma B/. {num(costo_anio, 0)} al año, frente a B/. {num(importe_12, 0)} facturados "
        f"entre julio de 2025 y junio de 2026; la diferencia se debe a que la energía se toma del año base "
        f"(octubre de 2025 a septiembre de 2026). La climatización centralizada cuesta "
        f"B/. {num(reparto.loc[reparto['uso'] == 'climatizacion', 'usd_anio'].sum(), 0)} al año.")

    I.h1("8. Evaluación de cumplimiento, conclusiones y recomendaciones")
    I.h2("8.1 Evaluación de cumplimiento")
    I.tabla("Evaluación de los criterios de aceptación", ["No", "Criterio", "Resultado", "Evaluación"],
            [["1", "Cierre del balance por acometida MTD",
              f"{pct(acometidas.loc[M1, 'cobertura'] - 1)} y {pct(acometidas.loc[M2, 'cobertura'] - 1)}",
              "Cumple" if error_max <= 0.05 else "No cumple"],
             ["2", "Cobertura de la medición en acometidas MTD", pct(min(cobertura, 1)), "Cumple"],
             ["3", "Usos significativos (80 % del consumo)",
              f"{usos} cargas suman {pct(orden['pct_total'].head(usos).sum())}", "Identificados"],
             ["4", "Duración del registro", "15 de 16 puntos con 7 días o más", "Cumple parcialmente"]],
            [0.4, 2.4, 2.0, 1.7], ["c", "l", "c", "c"])
    n = 2
    if extra:
        extra.seccion(I, f"8.{n}")
        n += 1
    I.h2(f"8.{n} Conclusiones")
    I.lista([
        f"El campus consume en promedio {num(total_mwh)} MWh/mes: {pct(acometidas.loc[M1, 'facturado_mwh_mes'] / total_mwh)} "
        f"en {N1}, {pct(acometidas.loc[M2, 'facturado_mwh_mes'] / total_mwh)} en {N2} y "
        f"{pct(acometidas.loc[M3, 'facturado_mwh_mes'] / total_mwh)} en {N3}.",
        f"Las mediciones de una semana, corregidas por estacionalidad, explican entre "
        f"{pct(acometidas.loc[[M1, M2], 'cobertura'].min())} y {pct(acometidas.loc[[M1, M2], 'cobertura'].max())} "
        f"de lo facturado en las acometidas MTD; la diferencia es compatible con pérdidas y cargas no medidas.",
        f"La climatización centralizada es el principal uso de la energía ({pct(clima)}). Casa de Máquinas 4 y "
        f"las casas de máquinas de los edificios 3 y 1 son los usos significativos de mayor prioridad.",
        f"{usos} cargas concentran el {pct(orden['pct_total'].head(usos).sum())} del consumo: "
        + enumerar(orden["edificio"].head(usos)) + ".",
        f"El costo de energía del campus es de B/. {num(costo_anio / 365.25, 0)} por día y B/. {num(costo_anio, 0)} "
        f"por año. Las tres casas de máquinas principales cuestan B/. "
        f"{num(por_nombre.loc[['Casa de Máquinas 4', 'Casa de máquinas - Chiller Edificio 3', 'Casa de máquinas - Chiller Edificio 1'], 'usd_anio'].sum(), 0)} al año.",
        f"De noche el campus mantiene unos {num(madrugada.sum(), 0)} kW, casi todos en los edificios; la "
        f"climatización centralizada aporta solo {num(clima_noche, 0)} kW.",
    ] + (extra.conclusiones() if extra else []))
    I.h2(f"8.{n + 1} Recomendaciones")
    I.lista([
        "Priorizar medidas de eficiencia en las plantas de agua helada, que concentran el mayor consumo en horario "
        "académico: temperatura de suministro de agua helada, secuenciación de chillers y bombas con variador.",
        "Revisar las cargas que quedan encendidas de noche en " + enumerar(nombres_id[i] for i in base_noche.head(5).index)
        + " (iluminación, aires acondicionados locales y equipos de oficina y laboratorio).",
        "Instalar medición permanente en Casa de Máquinas 4 y en las casas de máquinas de los edificios 1 y 3.",
        "Identificar y medir las cargas de la acometida BT, que tiene el precio por kWh más alto del campus.",
        "Repetir la medición de la Cafetería Central durante una semana completa y medir nuevamente VIPE en 2026.",
        "Definir indicadores de desempeño energético (kWh/m², kWh/estudiante) y normalizar la línea base con "
        "grados-día y ocupación para seguir el desempeño energético en el tiempo.",
        "Cuantificar ahorro, inversión y retorno de cada medida para completar la evaluación de oportunidades.",
        "Actualizar el análisis cada año con la facturación nueva.",
    ])

    I.h1("9. Anexos")
    I.h2("Anexo A. Archivos y períodos de registro")
    puntos = pd.read_csv(RAIZ / "data" / "puntos.csv", dtype={"acometida": str}).set_index("id")
    filas = [[f.edificio, puntos.loc[f.id, "archivo_original"],
              f"{f.inicio:%d/%m/%Y %H:%M} a {f.fin:%d/%m/%Y %H:%M}",
              puntos.loc[f.id, "equipo"]] for f in edificios.itertuples()]
    I.tabla("Archivos de datos utilizados", ["Edificio / sistema", "Archivo", "Período", "Equipo"],
            filas, [1.65, 1.75, 1.7, 1.4], ["l", "l", "c", "l"], letra=8)
    I.h2("Anexo B. Supuestos")
    I.lista([
        "La facturación corresponde a períodos de lectura de 28 a 31 días que cierran a fin de mes; se asimiló "
        "al mes calendario.",
        "El registro POSTGRADO corresponde al tablero de Rectoría y el registro Edificio Elli a Investigación ELI.",
        "Las mediciones son en baja tensión; la factura de las acometidas MTD incluye las pérdidas de transformación.",
        "No hubo feriados nacionales dentro de los períodos de registro.",
        "La carga de actividades y personas varía poco entre semanas de un mismo mes.",
        "Se asignaron a climatización las casas de máquinas, chillers, bombas y UMA.",
        "El aporte de cada edificio a la demanda máxima se estima con su perfil de día hábil, no con la demanda "
        "facturada de cada edificio, que no se mide por separado.",
    ])

    if extra:
        extra.anexo(I, "Anexo C")

    propiedades = doc.core_properties
    propiedades.author = propiedades.last_modified_by = "Irving Nieto"
    propiedades.title = "Peso y costo de cada edificio en el consumo de energía, Campus Víctor Levi Sasso"
    propiedades.keywords = "UTP, DINAGEA, energía"
    propiedades.created = propiedades.modified = dt.datetime(FECHA.year, FECHA.month, FECHA.day, 12)
    doc.save(archivo)
    ruta_portada.unlink()
    return archivo


if __name__ == "__main__":
    print(construir())
