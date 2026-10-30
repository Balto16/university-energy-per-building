"""Convierte los registros originales de los analizadores a potencia horaria.

Uso:
    python scripts/preparar_datos.py "ruta/a/los/CSV/originales"

Autor: Irving Nieto
"""
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "data" / "mediciones"


def leer_registro(ruta):
    with open(ruta, encoding="latin-1") as f:
        encabezado = f.readline().rstrip("\n")
    sep = "\t" if "\t" in encabezado else ";"

    # Fluke 1775: columnas Start/Stop y PowerP_Total_avg en W
    if encabezado.startswith("Start"):
        col = encabezado.split(sep).index("PowerP_Total_avg")
        df = pd.read_csv(ruta, sep=sep, encoding="latin-1", usecols=[0, col])
        df.columns = ["fecha", "p"]
        df["fecha"] = pd.to_datetime(df["fecha"])
    # PQ-Box: columnas Fecha/Hora y P_total_[W]
    else:
        df = pd.read_csv(ruta, sep=sep, encoding="latin-1", usecols=["Fecha", "Hora", "P_total_[W]"])
        df["fecha"] = pd.to_datetime(df["Fecha"] + " " + df["Hora"], format="%d.%m.%Y %H:%M:%S.%f")
        df["p"] = df["P_total_[W]"]

    return df.set_index("fecha")["p"].sort_index() / 1000


def a_horario(serie):
    horaria = serie.resample("1h").mean().dropna()
    # la primera y la última hora quedan incompletas
    return horaria.iloc[1:-1].round(3)


def main(carpeta):
    carpeta = Path(carpeta)
    puntos = pd.read_csv(RAIZ / "data" / "puntos.csv")
    SALIDA.mkdir(parents=True, exist_ok=True)

    for p in puntos.itertuples():
        serie = a_horario(leer_registro(carpeta / p.archivo_original))
        serie.rename("p_kw").to_csv(SALIDA / f"{p.id}.csv", index_label="fecha")
        print(f"{p.id:24s} {len(serie):5d} h  {serie.index.min():%Y-%m-%d} a {serie.index.max():%Y-%m-%d}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
