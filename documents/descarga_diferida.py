"""Captura inmutable para generar archivos solo al descargarlos, sin estado global."""
from copy import deepcopy


def preparar(generar, *args):
    snapshot=deepcopy(args)
    return lambda:generar(*deepcopy(snapshot))
