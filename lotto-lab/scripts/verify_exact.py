#!/usr/bin/env python3
"""Verificador independiente de la matemática de LOTTO LAB.

Lee JSON desde stdin con vectores generados por JavaScript/BigInt.
Calcula resultados con fractions.Fraction y math.comb: otros tipos,
otro lenguaje, ninguna dependencia pagada o API de terceros.
"""
from fractions import Fraction
from math import comb
import json
import sys


def calculate(game, r=None, special=None):
    n, k = game["n"], game["k"]
    b = game.get("bonus", 0)
    digits = game.get("kind") == "digits"
    if digits:
        total = 10 ** game["width"]
        if total != n or k != 1 or b:
            raise AssertionError("Matriz de dígitos inválida")
        exact = Fraction(1, total)
        return total, exact
    if n < k or k < 1:
        raise AssertionError("Matriz inválida")
    total = comb(n, k) * (b or 1)
    if r is None:
        return total, Fraction(1, total)
    if not 0 <= r <= k:
        raise AssertionError("Aciertos fuera de rango")
    matches = comb(k, r) * comb(n-k, k-r) if 0 <= k-r <= n-k else 0
    if b:
        count = matches * (1 if special else b-1)
    else:
        count = matches
    return total, Fraction(count, total)


def audit(vectors):
    if len(vectors) < 50:
        raise AssertionError("Insuficientes vectores de verificación")
    for index, item in enumerate(vectors):
        total, expected = calculate(item["game"], item.get("r"), item.get("special"))
        supplied = Fraction(int(item["numerator"]), int(item["denominator"]))
        assert total == int(item["total"]), (index, "total", total, item["total"])
        assert expected == supplied, (index, "fraction", expected, supplied)
    return len(vectors)


if __name__ == "__main__":
    rows = json.load(sys.stdin)
    try:
        n = audit(rows)
    except Exception as exc:
        print(f"FALLO DE PRECISIÓN: {exc}", file=sys.stderr)
        raise SystemExit(1)
    print(f"VALIDACIÓN CRUZADA: {n} probabilidades idénticas entre JavaScript BigInt y Python Fraction")
