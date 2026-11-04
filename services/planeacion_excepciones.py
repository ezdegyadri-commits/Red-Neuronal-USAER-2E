"""La excepción individual es nominal, confirmada y exclusiva de una hoja."""


def autorizadas(doc):
    return {str(aid) for aid,info in doc.get('metadatos',{}).get('excepciones_individuales_grupal',{}).items()
            if isinstance(info,dict) and info.get('confirmada') is True
            and info.get('documento')==doc.get('id') and info.get('cuenta')==doc.get('cuenta')}
