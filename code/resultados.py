"""Figuras y hoja de cálculo con los resultados del análisis.

Autor: Irving Nieto
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from analisis import ANIO_BASE, RAIZ, ejecutar

SALIDA = RAIZ / "resultados"
FIGURAS = RAIZ / "figures"
FIGURAS_ES = SALIDA / "figuras"

VERDE_OSCURO = "#14342B"
VERDE = "#4D816E"
VERDE_MEDIO = "#6CA893"
VERDE_CLARO = "#BEE6DB"
GRIS = "#BFBFBF"
GRIS_OSCURO = "#7F807F"

COLOR_ACOMETIDA = {"MT1": VERDE_OSCURO, "MT2": VERDE_MEDIO, "BT": GRIS_OSCURO}

TEXTOS = {
    "es": {
        "acometidas": {"MT1": "Acometida MT 1 (MTD)", "MT2": "Acometida MT 2 (MTD)", "BT": "Acometida BT (BTD)"},
        "no_medido": "No medido y pérdidas",
        "meses": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
        "participacion": "Participación en el consumo total facturado (%)",
        "costo": "Costo anual estimado (miles de B/.)",
        "energia": "Energía facturada (MWh/mes)",
        "anio_base": "Año base del análisis",
        "hora": "Hora del día",
        "potencia": "Potencia activa (kW)",
        "usos": {"climatizacion": "Climatización centralizada", "edificio": "Edificios",
                 "bt": "Acometida BT (sin desagregar)", "no_medido": "No medido y pérdidas"},
        "capas": ["Climatización MT 1", "Edificios MT 1", "Climatización MT 2", "Edificios MT 2"],
        "edificios": {},
    },
    "en": {
        "acometidas": {"MT1": "MV service 1 (MTD)", "MT2": "MV service 2 (MTD)", "BT": "LV service (BTD)"},
        "no_medido": "Unmetered and losses",
        "meses": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "participacion": "Share of total billed consumption (%)",
        "costo": "Estimated annual cost (thousand USD)",
        "energia": "Billed energy (MWh/month)",
        "anio_base": "Analysis base year",
        "hora": "Hour of day",
        "potencia": "Active power (kW)",
        "usos": {"climatizacion": "Central cooling", "edificio": "Buildings",
                 "bt": "LV service (not disaggregated)", "no_medido": "Unmetered and losses"},
        "capas": ["Cooling MV 1", "Buildings MV 1", "Cooling MV 2", "Buildings MV 2"],
        "edificios": {
            "Rectoría": "Rectorate",
            "Chiller Rectoría": "Rectorate chiller",
            "Casa de máquinas - Chiller Edificio 1": "Chiller plant, Building 1",
            "Edificio 1": "Building 1",
            "DITIC": "DITIC (IT)",
            "Edificio 3": "Building 3",
            "Casa de máquinas - Chiller Edificio 3": "Chiller plant, Building 3",
            "Laboratorio Docentes": "Faculty laboratory",
            "Investigación ELI": "ELI research building",
            "Casa de Máquinas 4": "Chiller plant 4",
            "Aulas (Edificio 4)": "Classrooms (Building 4)",
            "Facilidades": "Facilities",
            "Cafetería Central": "Central cafeteria",
            "VIPE - Edificio administrativo": "VIPE administrative building",
            "VIPE - UMA": "VIPE air handling units",
            "VIPE - Bombas y chiller": "VIPE pumps and chiller",
            "No medido y pérdidas (MT 1)": "Unmetered and losses (MV 1)",
            "No medido y pérdidas (MT 2)": "Unmetered and losses (MV 2)",
            "Acometida BT (sin desagregar)": "LV service (not disaggregated)",
        },
    },
}

plt.rcParams["font.family"] = "Times New Roman"


def ejes_limpios(ax, eje="y"):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis=eje, color="#D8D9D8", lw=0.6)
    ax.set_axisbelow(True)


def color_fila(fila):
    if fila["uso"] == "no_medido":
        return GRIS
    return COLOR_ACOMETIDA[fila["acometida"]]


def leyenda_acometidas(ax, t, **kw):
    marcas = [Patch(color=COLOR_ACOMETIDA[m], label=t["acometidas"][m]) for m in COLOR_ACOMETIDA]
    marcas.append(Patch(color=GRIS, label=t["no_medido"]))
    ax.legend(handles=marcas, frameon=False, fontsize=9, **kw)


def barras_por_edificio(datos, columna, factor, xlabel, separacion, formato, t, ruta):
    etiquetas = datos["edificio"].map(lambda e: t["edificios"].get(e, e))
    valores = datos[columna] * factor
    fig, ax = plt.subplots(figsize=(8.5, 7), dpi=200)
    barras = ax.barh(etiquetas, valores, color=datos.apply(color_fila, axis=1))
    for barra, valor in zip(barras, valores):
        ax.text(valor + separacion, barra.get_y() + barra.get_height() / 2, formato(valor), va="center", fontsize=9)
    ax.set_xlabel(xlabel)
    ax.set_xlim(0, valores.max() * 1.15)
    ejes_limpios(ax, "x")
    leyenda_acometidas(ax, t, loc="lower right")
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)


def figura_peso(reparto, ruta, t):
    barras_por_edificio(reparto.sort_values("pct_total"), "pct_total", 100, t["participacion"], 0.2,
                        lambda v: f"{v:.1f} %", t, ruta)


def figura_costo(reparto, ruta, t):
    barras_por_edificio(reparto.sort_values("usd_anio"), "usd_anio", 1 / 1000, t["costo"], 3,
                        lambda v: f"{v:,.0f}".replace(",", " "), t, ruta)


def figura_facturacion(facturacion, ruta, t):
    df = facturacion.sort_index()
    x = np.arange(len(df))
    fig, ax = plt.subplots(figsize=(9, 4), dpi=200)
    base = np.zeros(len(df))
    for m in ["MT1", "MT2", "BT"]:
        ax.bar(x, df[m].values, bottom=base, width=0.8, color=COLOR_ACOMETIDA[m], label=t["acometidas"][m])
        base += df[m].values
    i0 = df.index.get_loc(ANIO_BASE[0])
    i1 = df.index.get_loc(ANIO_BASE[-1])
    ax.axvspan(i0 - 0.5, i1 + 0.5, color=VERDE_CLARO, alpha=0.45, lw=0, label=t["anio_base"])
    ax.set_xticks(x[::3])
    ax.set_xticklabels([f"{t['meses'][p.month - 1]}\n{p.year}" for p in df.index[::3]], fontsize=8)
    ax.set_xlim(-0.8, len(df) - 0.2)
    ax.set_ylim(0, base.max() * 1.08)
    ax.set_ylabel(t["energia"])
    ejes_limpios(ax)
    ax.legend(frameon=False, fontsize=8.5, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=4)
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)


def grupos_de_uso(reparto, t=TEXTOS["es"]):
    nombres = t["usos"]
    return reparto.groupby("uso")["pct_total"].sum().rename(index=nombres).reindex(nombres.values())


def figura_grupos(reparto, ruta, t):
    grupos = grupos_de_uso(reparto, t)
    colores = [VERDE_OSCURO, VERDE_MEDIO, GRIS_OSCURO, GRIS]
    fig, ax = plt.subplots(figsize=(8, 2.6), dpi=200)
    izquierda = 0
    for (nombre, valor), color in zip(grupos.items(), colores):
        ax.barh([0], [valor * 100], left=izquierda, color=color, height=0.55, label=nombre)
        if valor > 0.04:
            ax.text(izquierda + valor * 50, 0, f"{valor * 100:.1f} %", ha="center", va="center",
                    color="white", fontsize=11, weight="bold")
        izquierda += valor * 100
    ax.set_xlim(0, 100)
    ax.set_yticks([])
    ax.set_xlabel(t["participacion"])
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.45), ncol=4)
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)


def perfil_puntos(edificios, perfiles):
    return pd.DataFrame({
        fila.id: perfiles[fila.id]["Hábil"].interpolate(limit_direction="both") * fila.k
        for fila in edificios.itertuples()
    })


def perfil_campus(edificios, perfiles):
    puntos = perfil_puntos(edificios, perfiles)
    capas = {}
    for (acometida, uso), grupo in edificios.groupby(["acometida", "uso"]):
        capas[(acometida, uso)] = puntos[grupo["id"]].sum(axis=1)
    orden = [("MT1", "climatizacion"), ("MT1", "edificio"), ("MT2", "climatizacion"), ("MT2", "edificio")]
    return pd.DataFrame(capas)[orden]


def figura_perfil(capas, ruta, t):
    fig, ax = plt.subplots(figsize=(8.5, 3.9), dpi=200)
    colores = [VERDE_OSCURO, VERDE, VERDE_MEDIO, VERDE_CLARO]
    ax.stackplot(capas.index, capas.T.values, labels=t["capas"], colors=colores, alpha=0.95)
    total = capas.sum(axis=1)
    ax.plot(capas.index, total, color="black", lw=1)
    ax.set_xticks(range(0, 24, 2))
    ax.set_xlim(0, 23)
    ax.set_ylim(0, total.max() * 1.3)
    ax.set_xlabel(t["hora"])
    ax.set_ylabel(t["potencia"])
    ejes_limpios(ax)
    ax.legend(frameon=False, fontsize=8, loc="upper left", ncol=2)
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)


def escribir_hoja(ws, df, titulo, formatos):
    borde = Border(*(Side(style="thin", color="BFBFBF"),) * 4)
    ws.append([titulo])
    ws["A1"].font = Font(name="Times New Roman", bold=True, size=12, color="FFFFFF")
    ws["A1"].fill = PatternFill("solid", fgColor=VERDE[1:])
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(df.columns))
    ws.append(list(df.columns))
    for celda in ws[2]:
        celda.font = Font(name="Times New Roman", bold=True, size=10, color=VERDE_OSCURO[1:])
        celda.fill = PatternFill("solid", fgColor=VERDE_CLARO[1:])
        celda.border = borde
        celda.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
    for i, fila in enumerate(df.itertuples(index=False)):
        ws.append(list(fila))
        for j, celda in enumerate(ws[ws.max_row]):
            celda.font = Font(name="Times New Roman", size=10)
            celda.border = borde
            if i % 2:
                celda.fill = PatternFill("solid", fgColor="E4EEEB")
            if df.columns[j] in formatos:
                celda.number_format = formatos[df.columns[j]]
    for j, col in enumerate(df.columns, 1):
        ancho = max([len(str(col))] + [len(str(v)) for v in df[col]])
        ws.column_dimensions[get_column_letter(j)].width = min(45, max(10, ancho * 0.9 + 2))
    ws.row_dimensions[2].height = 32
    ws.freeze_panes = "A3"


def guardar_excel(r, ruta):
    nombres = r["acometidas"]["nombre"]
    reparto = r["reparto"].assign(acometida=lambda d: d["acometida"].map(nombres))
    resumen = reparto[["edificio", "acometida", "mwh_mes_ajustado", "pct_acometida", "pct_total",
                       "usd_kwh", "usd_dia", "usd_mes", "usd_anio"]].copy()
    resumen.columns = ["Edificio / sistema", "Acometida", "Energía (MWh/mes)", "% de la acometida",
                       "% de la institución", "Precio medio (B/./kWh)", "Costo (B/./día)",
                       "Costo (B/./mes)", "Costo (B/./año)"]

    acometidas = r["acometidas"].reset_index()[["nombre", "tarifa", "facturado_mwh_mes", "medido_mwh_mes",
                                              "diferencia_mwh_mes", "cobertura", "importe", "kwh",
                                              "demanda_media", "usd_kwh"]]
    acometidas.columns = ["Acometida", "Tarifa", "Facturado (MWh/mes)", "Medido estimado (MWh/mes)",
                         "Diferencia (MWh/mes)", "Cobertura", "Importe jul 2025-jun 2026 (B/.)",
                         "Energía jul 2025-jun 2026 (kWh)", "Demanda media (kW)", "Precio medio (B/./kWh)"]

    mediciones = r["edificios"].assign(acometida=lambda d: d["acometida"].map(nombres))[["edificio", "acometida", "inicio", "fin", "horas", "p_media_kw", "p_max_kw",
                                 "mwh_semana", "k", "mwh_mes", "nota"]].copy()
    mediciones["inicio"] = mediciones["inicio"].dt.strftime("%Y-%m-%d %H:%M")
    mediciones["fin"] = mediciones["fin"].dt.strftime("%Y-%m-%d %H:%M")
    mediciones.columns = ["Edificio / sistema", "Acometida", "Inicio", "Fin", "Horas", "P media (kW)",
                          "P máx. horaria (kW)", "Semana tipo (MWh)", "Factor k", "Energía (MWh/mes)", "Notas"]

    facturacion = r["facturacion"].rename(columns=nombres)
    facturacion.index = facturacion.index.astype(str)
    facturacion["Total"] = facturacion.sum(axis=1)
    facturacion = facturacion.reset_index().rename(columns={"periodo": "Mes", "index": "Mes"})

    perfiles = []
    puntos = r["edificios"].set_index("id")["edificio"]
    for id_punto, perfil in r["perfiles"].items():
        for hora, fila in perfil.iterrows():
            perfiles.append([puntos[id_punto], hora, fila["Hábil"], fila["Sábado"], fila["Domingo"]])
    perfiles = pd.DataFrame(perfiles, columns=["Edificio / sistema", "Hora", "Hábil (kW)", "Sábado (kW)",
                                               "Domingo (kW)"])

    libro = Workbook()
    libro.remove(libro.active)
    porcentaje, entero, decimal, precio = "0.0 %", "#,##0", "0.0", "0.0000"
    escribir_hoja(libro.create_sheet("Resumen"), resumen, "PESO Y COSTO DE CADA EDIFICIO", {
        "Energía (MWh/mes)": decimal, "% de la acometida": porcentaje, "% de la institución": porcentaje,
        "Precio medio (B/./kWh)": precio, "Costo (B/./día)": entero, "Costo (B/./mes)": entero,
        "Costo (B/./año)": entero})
    escribir_hoja(libro.create_sheet("Acometidas"), acometidas, "BALANCE Y PRECIO POR ACOMETIDA", {
        "Facturado (MWh/mes)": decimal, "Medido estimado (MWh/mes)": decimal, "Diferencia (MWh/mes)": decimal,
        "Cobertura": porcentaje, "Importe jul 2025-jun 2026 (B/.)": entero,
        "Energía jul 2025-jun 2026 (kWh)": entero, "Demanda media (kW)": decimal,
        "Precio medio (B/./kWh)": precio})
    escribir_hoja(libro.create_sheet("Mediciones"), mediciones, "MEDICIONES Y SEMANA TIPO", {
        "P media (kW)": decimal, "P máx. horaria (kW)": decimal, "Semana tipo (MWh)": "0.000",
        "Factor k": "0.000", "Energía (MWh/mes)": decimal})
    escribir_hoja(libro.create_sheet("Facturación"), facturacion, "FACTURACIÓN MENSUAL (MWh)",
                  {c: "0.000" for c in facturacion.columns[1:]})
    escribir_hoja(libro.create_sheet("Perfiles"), perfiles, "PERFIL HORARIO MEDIO POR TIPO DE DÍA",
                  {c: decimal for c in perfiles.columns[2:]})
    libro.properties.creator = "Irving Nieto"
    libro.properties.lastModifiedBy = "Irving Nieto"
    libro.properties.title = "Peso y costo de los edificios en el consumo de la UTP"
    libro.save(ruta)


NOMBRES_FIGURAS = {
    "es": ["peso_edificios.png", "costo_anual.png", "facturacion.png", "grupos_uso.png", "perfil_habil.png"],
    "en": ["share_by_building.png", "annual_cost.png", "monthly_billing.png", "end_use_split.png",
           "weekday_profile.png"],
}


def figuras(r, capas, carpeta, idioma):
    carpeta.mkdir(parents=True, exist_ok=True)
    t = TEXTOS[idioma]
    nombres = NOMBRES_FIGURAS[idioma]
    figura_peso(r["reparto"], carpeta / nombres[0], t)
    figura_costo(r["reparto"], carpeta / nombres[1], t)
    figura_facturacion(r["facturacion"], carpeta / nombres[2], t)
    figura_grupos(r["reparto"], carpeta / nombres[3], t)
    figura_perfil(capas, carpeta / nombres[4], t)


def generar(r=None):
    r = r or ejecutar()
    capas = perfil_campus(r["edificios"], r["perfiles"])
    figuras(r, capas, FIGURAS, "en")
    figuras(r, capas, FIGURAS_ES, "es")
    guardar_excel(r, SALIDA / "peso_y_costo_edificios.xlsx")
    return r, capas


if __name__ == "__main__":
    generar()
    print(f"Resultados en {SALIDA}")
