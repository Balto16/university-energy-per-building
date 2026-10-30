"""Ejecuta el análisis completo: tablas, figuras, hoja de cálculo e informe.

Autor: Irving Nieto
"""
from informe import construir

if __name__ == "__main__":
    ruta = construir()
    print(f"Listo: {ruta}")
