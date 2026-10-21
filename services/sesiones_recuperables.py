"""Recuperación de 12 h por pestaña; el cliente nunca decide identidad/permisos."""
import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import date, datetime
from cryptography.fernet import Fernet, InvalidToken

TTL = 12 * 3600
HOJA = 'Sesiones_Recuperables'
HEADERS = ['Sesion', 'Cuenta', 'Emitida', 'Vence', 'Estado', 'MAC']
CAMPOS = ('evento_descripcion', 'evento_fecha', 'evento_modo',
          'evento_escuela_individual', 'evento_alumno', 'evento_escuela_grupo',
          'evento_grado', 'evento_grupo', 'evento_borradores_json', 'evento_contexto_actual')


class Sesiones:
    def __init__(self, secreto, store, reloj=time.time):
        self.clave = hmac.new(secreto, b'usaer-sesiones-recuperables-v1', hashlib.sha256).digest()
        self.cifrado = Fernet(base64.urlsafe_b64encode(self.clave))
        self.store, self.reloj = store, reloj

    def _firma(self, valores):
        return hmac.new(self.clave, json.dumps(valores, ensure_ascii=False, sort_keys=True).encode(), hashlib.sha256).hexdigest()

    def _binding(self, user):
        return self._firma([str(user.get(k, '')) for k in
            ('ID_Usuario', 'Usuario', 'Password', 'Nombre', 'Rol', 'Escuelas_Permitidas', 'Estatus')])

    def _append(self, row):
        row = {k: str(row.get(k, '')) for k in HEADERS[:-1]}
        row['MAC'] = self._firma([row[k] for k in HEADERS[:-1]])
        self.store.append(row)
        if not any(all(str(r.get(k,''))==row[k] for k in HEADERS) for r in self.store.rows()):
            raise RuntimeError('No se confirmó el registro privado de acceso.')

    def emitir(self, username):
        user = self.store.user(username)
        ahora = int(self.reloj())
        payload = dict(sid=secrets.token_urlsafe(32), user=username, iat=ahora,
                       exp=ahora + TTL, binding=self._binding(user))
        self._append(dict(Sesion=payload['sid'], Cuenta=username, Emitida=ahora,
                          Vence=payload['exp'], Estado='ACTIVA'))
        return self.cifrado.encrypt_at_time(json.dumps(payload).encode(), ahora).decode()

    def _abrir(self, token, vigente=True):
        if not isinstance(token, str) or len(token) > 5000:
            raise ValueError('Acceso recuperable no válido.')
        try:
            raw = self.cifrado.decrypt(token.encode())
            p = json.loads(raw)
            ahora = int(self.reloj())
            if not isinstance(p, dict) or not all(k in p for k in ('sid','user','iat','exp','binding')):
                raise ValueError()
            if p['exp'] - p['iat'] != TTL or (vigente and not p['iat'] <= ahora < p['exp']):
                raise ValueError()
            return p
        except (InvalidToken, ValueError, TypeError, KeyError):
            raise ValueError('Vuelve a ingresar: el acceso recuperable venció o no es válido.') from None

    def recuperar(self, token):
        p = self._abrir(token)
        filas = [r for r in self.store.rows() if r.get('Sesion') == p['sid']]
        for r in filas:
            firma = self._firma([str(r.get(k, '')) for k in HEADERS[:-1]])
            if not hmac.compare_digest(str(r.get('MAC', '')), firma):
                raise ValueError('No se pudo verificar el registro de acceso.')
        if not filas or any(r.get('Estado') == 'CERRADA' for r in filas):
            raise ValueError('Este acceso está cerrado.')
        r = filas[-1]
        if r.get('Estado') != 'ACTIVA' or r.get('Cuenta') != p['user'] or str(r.get('Vence')) != str(p['exp']):
            raise ValueError('Registro de acceso no válido.')
        user = self.store.user(p['user'])
        if not hmac.compare_digest(p['binding'], self._binding(user)):
            raise ValueError('La cuenta cambió. Vuelve a ingresar.')
        return user

    def cerrar(self, token, username):
        p = self._abrir(token, vigente=False)
        if p['user'] != username:
            raise PermissionError('No puedes cerrar el acceso de otra cuenta.')
        self._append(dict(Sesion=p['sid'], Cuenta=username, Emitida=p['iat'],
                          Vence=p['exp'], Estado='CERRADA'))

    def proteger_borrador(self, username, datos):
        valores = {k: v for k, v in datos.items() if k in CAMPOS}
        for k, v in valores.items():
            if isinstance(v, (date, datetime)): valores[k] = {'fecha': v.isoformat()[:10]}
            elif not isinstance(v, str): raise ValueError('Borrador no válido.')
        texto = json.dumps({'user': username, 'datos': valores}, ensure_ascii=False).encode()
        if len(texto) > 50000: raise ValueError('El borrador supera el respaldo de la pestaña.')
        return self.cifrado.encrypt_at_time(texto, int(self.reloj())).decode()

    def recuperar_borrador(self, username, token):
        if not isinstance(token, str) or len(token) > 75000: raise ValueError('Borrador no válido.')
        try:
            p = json.loads(self.cifrado.decrypt_at_time(token.encode(), TTL, int(self.reloj())))
            if p['user'] != username or not isinstance(p['datos'], dict): raise ValueError()
            result = {}
            for k, v in p['datos'].items():
                if k not in CAMPOS: raise ValueError()
                if isinstance(v, dict) and set(v) == {'fecha'}: v = date.fromisoformat(v['fecha'])
                elif not isinstance(v, str): raise ValueError()
                result[k] = v
            return result
        except (InvalidToken, ValueError, TypeError, KeyError):
            raise ValueError('No se pudo recuperar este borrador con tu cuenta.') from None


class GoogleSesiones:
    def user(self, username):
        from data.passkeys import GooglePasskeyStore
        return GooglePasskeyStore().user(username)

    def rows(self):
        from data.google import clear_cache
        from data import repository as repo
        clear_cache(HOJA)
        return repo.read(HOJA).fillna('').to_dict('records')

    def append(self, row):
        from data.google import ensure_headers, clear_cache
        # No reintento ciego de append; fallo de confirmación no habilita acceso.
        ws = ensure_headers(HOJA, HEADERS)
        headers = ws.row_values(1)
        if len(headers)!=len(set(headers)) or not set(HEADERS)<=set(headers):raise RuntimeError('Registro privado de accesos no válido.')
        ws.append_rows([[row.get(k,'') for k in headers]], value_input_option='RAW')
        clear_cache(HOJA)


def servicio():
    from data.google import _secret_dict
    return Sesiones(_secret_dict('credenciales_json')['private_key'].encode(), GoogleSesiones())
