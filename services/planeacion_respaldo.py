"""Continuidad local: reutiliza el prellenado canónico, nunca llama a un motor."""
from services.planeacion import autorizar
from services.planeacion_generacion import prellenar


def autollenar(doc):
    """Completa antecedentes/referentes sin sustituir decisiones profesionales.

    La identidad, tablas oficiales y redacción manual quedan intactas. El filtro
    de fuentes y las marcas de autorrelleno son los del servicio existente.
    No consulta fuentes nuevas, no escribe y no genera propuestas pedagógicas.
    """
    autorizar(doc, True)
    return prellenar(doc)
