"""Comparación exacta del catálogo canónico, independiente de la pantalla."""
import hmac

def buscar_usuario(frame,user,password):
    if not isinstance(user,str) or not isinstance(password,str) or not user or not password:return None
    if not {'Usuario','Password'}.issubset(frame.columns):raise ValueError('El catálogo de acceso no contiene los campos requeridos.')
    matches=[]
    for _,row in frame.iterrows():
        # UTF-8 permite ñ y acentos; no se recorta ni transforma la clave.
        if hmac.compare_digest(str(row.get('Usuario','')).encode('utf-8'),user.encode('utf-8')):
            matches.append(row)
    if len(matches)!=1:return None
    row=matches[0]
    if not hmac.compare_digest(str(row.get('Password','')).encode('utf-8'),password.encode('utf-8')):return None
    if not str(row.get('Nombre','')).strip() or not str(row.get('Rol','')).strip():return None
    return row
