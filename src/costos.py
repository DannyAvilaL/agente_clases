"""Utilidades para estimar el costo de tokens y medir ejecuciones."""

import math
import time
from typing import Any, Callable


def calcular_costo_tokens(
    tokens_entrada: int,
    tokens_salida: int = 0,
    precio_entrada_por_millon: float = 0.0,
    precio_salida_por_millon: float = 0.0,
) -> float:
    """Calcula el costo según tarifas por millón de tokens.

    Las tarifas predeterminadas son cero, apropiadas para un modelo local sin
    cobro por uso. Se pueden indicar tarifas para obtener una estimación.
    """
    if tokens_entrada < 0 or tokens_salida < 0:
        raise ValueError("El número de tokens no puede ser negativo.")
    if not math.isfinite(precio_entrada_por_millon) or precio_entrada_por_millon < 0:
        raise ValueError("La tarifa de entrada debe ser un número finito no negativo.")
    if not math.isfinite(precio_salida_por_millon) or precio_salida_por_millon < 0:
        raise ValueError("La tarifa de salida debe ser un número finito no negativo.")

    return (
        tokens_entrada * precio_entrada_por_millon
        + tokens_salida * precio_salida_por_millon
    ) / 1_000_000


def medir_tiempo_ejecucion(funcion: Callable, *args: Any, **kwargs: Any):
    """Ejecuta una función y devuelve su resultado y duración en segundos."""
    inicio = time.perf_counter()
    resultado = funcion(*args, **kwargs)
    duracion = time.perf_counter() - inicio
    return resultado, duracion
