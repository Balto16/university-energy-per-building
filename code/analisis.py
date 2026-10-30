"""Peso de cada edificio en el consumo eléctrico del Campus Víctor Levi Sasso (UTP).

Cada medición (de 1 a 32 días, en meses distintos) se lleva a una semana tipo,
se corrige por estacionalidad con la facturación de la acometida y se compara con lo
facturado. El costo se asigna con el precio medio pagado en cada acometida de ENSA.

Autor: Irving Nieto
"""
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "data"

ANIO_BASE = pd.period_range("2025-10", "2026-09", freq="M")
PERIODO_COSTO = pd.period_range("2025-07", "2026-06", freq="M")

ACOMETIDAS = pd.DataFrame(
    {
        "acometida": ["MT1", "MT2", "BT"],
        "nombre": ["Acometida MT 1", "Acometida MT 2", "Acometida BT"],
        "tarifa": ["MTD", "MTD", "BTD"],
    }
).set_index("acometida")

DIAS_MES = 365.25 / 12
TIPOS_DIA = ["Hábil", "Sábado", "Domingo"]


def cargar_facturacion(acometida):
    df = pd.read_csv(DATOS / "facturacion" / f"acometida_{acometida.lower()}.csv")
    df = df.melt(id_vars="Mes del año", var_name="anio", value_name="mwh").dropna()
    df["periodo"] = [
        pd.Period(year=int(a), month=int(m[:2]), freq="M") for a, m in zip(df["anio"], df["Mes del año"])
    ]
    return df.set_index("periodo")["mwh"].sort_index()


def cargar_importes():
    df = pd.read_csv(DATOS / "facturacion" / "importes.csv", dtype={"acometida": str})
    df["periodo"] = [pd.Period(year=a, month=m, freq="M") for a, m in zip(df["anio"], df["mes"])]
    return df


def cargar_medicion(id_punto):
    df = pd.read_csv(DATOS / "mediciones" / f"{id_punto}.csv", parse_dates=["fecha"])
    return df.set_index("fecha")["p_kw"]


def tipo_dia(indice):
    dia = indice.dayofweek
    return np.select([dia == 5, dia == 6], ["Sábado", "Domingo"], "Hábil")


def perfil_horario(serie):
    df = pd.DataFrame({"p": serie.values, "hora": serie.index.hour, "tipo": tipo_dia(serie.index)})
    tabla = df.pivot_table(index="hora", columns="tipo", values="p", aggfunc="mean")
    return tabla.reindex(index=range(24), columns=TIPOS_DIA)


def relacion_fin_de_semana(perfiles, puntos):
    relaciones = []
    for p in puntos.itertuples():
        perfil = perfiles[p.id]
        if p.uso == "edificio" and perfil.notna().all().all():
            relaciones.append(perfil.sum() / perfil["Hábil"].sum())
    return pd.DataFrame(relaciones).median()


def energia_semanal(perfil, relacion):
    habil = perfil["Hábil"].interpolate(limit_direction="both").sum()
    total = 5 * habil
    notas = []
    for dia in ["Sábado", "Domingo"]:
        if perfil[dia].notna().sum() >= 20:
            total += perfil[dia].interpolate(limit_direction="both").sum()
        else:
            total += habil * relacion[dia]
            notas.append(f"{dia} estimado ({relacion[dia]:.2f} del día hábil)")
    return total / 1000, "; ".join(notas)


def consumo_diario(facturacion, periodo):
    if periodo in facturacion.index:
        return facturacion[periodo] / periodo.days_in_month

    # mes aún sin factura: mismo mes del año anterior ajustado por el crecimiento ene-ago
    anterior = periodo - 12
    meses = range(1, 9)
    crecimiento = (
        sum(facturacion[pd.Period(year=periodo.year, month=m, freq="M")] for m in meses)
        / sum(facturacion[pd.Period(year=anterior.year, month=m, freq="M")] for m in meses)
    )
    return facturacion[anterior] * crecimiento / periodo.days_in_month


def factor_estacional(facturacion, inicio, fin):
    dias_base = sum(p.days_in_month for p in ANIO_BASE)
    diario_base = facturacion[ANIO_BASE].sum() / dias_base
    dias = pd.date_range(inicio.normalize(), fin.normalize(), freq="D")
    diario_medido = np.mean([consumo_diario(facturacion, d.to_period("M")) for d in dias])
    return diario_base / diario_medido


def precio_medio(importes):
    ventana = importes[importes["periodo"].isin(PERIODO_COSTO)]
    tabla = ventana.groupby("acometida").agg(
        importe=("importe_usd", "sum"),
        kwh=("consumo_kwh", "sum"),
        demanda_media=("demanda_kw", "mean"),
        demanda_max=("demanda_kw", "max"),
    )
    tabla["usd_kwh"] = tabla["importe"] / tabla["kwh"]
    return tabla


def desglose_factura(ruta=DATOS / "facturacion" / "factura_2026_09.csv"):
    factura = pd.read_csv(ruta)
    tabla = factura.pivot_table(index="acometida", columns="concepto", values="monto_usd", aggfunc="sum")
    tabla["Total"] = tabla.sum(axis=1)
    tabla["parte_demanda"] = tabla["Demanda"] / tabla["Total"]
    return tabla


def participacion_en_pico(edificios, perfiles):
    """Aporte de cada punto a la hora de mayor demanda de su acometida en un día hábil típico."""
    aporte = {}
    for acometida, grupo in edificios.groupby("acometida"):
        perfil = pd.DataFrame({
            fila.id: perfiles[fila.id]["Hábil"].interpolate(limit_direction="both") * fila.k
            for fila in grupo.itertuples()
        })
        total = perfil.sum(axis=1)
        hora = total.idxmax()
        aporte.update((perfil.loc[hora] / total[hora]).to_dict())
    return pd.Series(aporte)


def ejecutar():
    puntos = pd.read_csv(DATOS / "puntos.csv", dtype={"acometida": str})
    facturacion = {m: cargar_facturacion(m) for m in ACOMETIDAS.index}
    importes = cargar_importes()

    series = {p: cargar_medicion(p) for p in puntos["id"]}
    perfiles = {p: perfil_horario(s) for p, s in series.items()}
    relacion = relacion_fin_de_semana(perfiles, puntos)

    filas = []
    for p in puntos.itertuples():
        serie = series[p.id]
        semana, nota = energia_semanal(perfiles[p.id], relacion)
        k = factor_estacional(facturacion[p.acometida], serie.index.min(), serie.index.max())
        filas.append(
            {
                "id": p.id,
                "edificio": p.edificio,
                "acometida": p.acometida,
                "uso": p.uso,
                "inicio": serie.index.min(),
                "fin": serie.index.max(),
                "horas": len(serie),
                "p_media_kw": serie.mean(),
                "p_max_kw": serie.max(),
                "mwh_semana": semana,
                "k": k,
                "mwh_mes": semana * k * DIAS_MES / 7,
                "nota": nota,
            }
        )
    edificios = pd.DataFrame(filas)

    acometidas = ACOMETIDAS.copy()
    acometidas["facturado_mwh_mes"] = [facturacion[m][ANIO_BASE].mean() for m in acometidas.index]
    acometidas["medido_mwh_mes"] = edificios.groupby("acometida")["mwh_mes"].sum().reindex(acometidas.index).fillna(0)
    acometidas["diferencia_mwh_mes"] = acometidas["facturado_mwh_mes"] - acometidas["medido_mwh_mes"]
    acometidas["cobertura"] = acometidas["medido_mwh_mes"] / acometidas["facturado_mwh_mes"]

    # si lo medido supera lo facturado se escala; si no, la diferencia queda como no medido
    escala = (acometidas["facturado_mwh_mes"] / acometidas["medido_mwh_mes"]).clip(upper=1)
    edificios["mwh_mes_ajustado"] = edificios["mwh_mes"] * edificios["acometida"].map(escala)

    restos = []
    for m, fila in acometidas.iterrows():
        if fila["medido_mwh_mes"] == 0:
            restos.append({"edificio": "Acometida BT (sin desagregar)", "acometida": m, "uso": "bt",
                           "mwh_mes_ajustado": fila["facturado_mwh_mes"]})
        elif fila["diferencia_mwh_mes"] > 0:
            corto = fila["nombre"].replace("Acometida ", "")
            restos.append({"edificio": f"No medido y pérdidas ({corto})", "acometida": m, "uso": "no_medido",
                           "mwh_mes_ajustado": fila["diferencia_mwh_mes"]})
    reparto = pd.concat([edificios, pd.DataFrame(restos)], ignore_index=True)

    total = acometidas["facturado_mwh_mes"].sum()
    reparto["pct_acometida"] = reparto["mwh_mes_ajustado"] / reparto["acometida"].map(acometidas["facturado_mwh_mes"])
    reparto["pct_total"] = reparto["mwh_mes_ajustado"] / total

    precios = precio_medio(importes)
    factura = desglose_factura()
    acometidas = acometidas.join(precios).join(factura["parte_demanda"])
    acometidas["usd_mes"] = acometidas["facturado_mwh_mes"] * 1000 * acometidas["usd_kwh"]

    # la parte de energía se reparte por consumo y la de demanda por el aporte a la hora pico
    pico = participacion_en_pico(edificios, perfiles)
    reparto["pct_pico"] = reparto["id"].map(pico).fillna(0)
    reparto.loc[reparto["uso"] == "bt", "pct_pico"] = 1
    demanda = reparto["acometida"].map(acometidas["parte_demanda"])
    peso = (1 - demanda) * reparto["pct_acometida"] + demanda * reparto["pct_pico"]
    reparto["usd_mes"] = peso * reparto["acometida"].map(acometidas["usd_mes"])
    reparto["usd_anio"] = reparto["usd_mes"] * 12
    reparto["usd_dia"] = reparto["usd_anio"] / 365.25
    reparto["usd_kwh"] = reparto["usd_mes"] / (reparto["mwh_mes_ajustado"] * 1000)

    return {
        "edificios": edificios,
        "reparto": reparto,
        "acometidas": acometidas,
        "facturacion": pd.DataFrame(facturacion),
        "importes": importes,
        "factura": factura,
        "perfiles": perfiles,
        "relacion": relacion,
    }


if __name__ == "__main__":
    r = ejecutar()
    pd.set_option("display.width", 200, "display.max_columns", 20)
    print(r["acometidas"].round(4).to_string())
    print()
    columnas = ["edificio", "acometida", "mwh_mes_ajustado", "pct_acometida", "pct_total", "usd_dia", "usd_mes", "usd_anio"]
    print(r["reparto"][columnas].round(3).to_string())
