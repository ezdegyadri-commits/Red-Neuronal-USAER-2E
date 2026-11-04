"""Ayuda de captura, sin consultas externas ni asignación de una CURP oficial."""
import re
from datetime import date
from utils.text import normalizar_texto

ENTIDADES={'Aguascalientes':'AS','Baja California':'BC','Baja California Sur':'BS','Campeche':'CC',
 'Coahuila':'CL','Colima':'CM','Chiapas':'CS','Chihuahua':'CH','Ciudad de México':'DF','Durango':'DG',
 'Guanajuato':'GT','Guerrero':'GR','Hidalgo':'HG','Jalisco':'JC','México':'MC','Michoacán':'MN',
 'Morelos':'MS','Nayarit':'NT','Nuevo León':'NL','Oaxaca':'OC','Puebla':'PL','Querétaro':'QT',
 'Quintana Roo':'QR','San Luis Potosí':'SP','Sinaloa':'SL','Sonora':'SR','Tabasco':'TC','Tamaulipas':'TS',
 'Tlaxcala':'TL','Veracruz':'VZ','Yucatán':'YN','Zacatecas':'ZS','Extranjero':'NE'}


def raiz_curp(paterno,materno,nombres,nacimiento,sexo,entidad):
    """Propuesta de 16 posiciones; jamás inventa el diferenciador RENAPO ni el DV."""
    def limpiar(v):
        v=normalizar_texto(str(v).replace('Ñ','~').replace('ñ','~')).replace('~','Ñ')
        tokens=[t for t in re.findall(r'[A-ZÑ]+',v) if t not in {'DE','DEL','LA','LAS','LOS','Y','DA','DAS','VAN','VON'}]
        return tokens
    ap=limpiar(paterno);am=limpiar(materno);ns=limpiar(nombres)
    if not ap or not ns or sexo not in ('H','M') or entidad not in ENTIDADES:raise ValueError('Completa apellido, nombres, sexo y entidad de nacimiento para proponer la raíz.')
    n=ns[1] if len(ns)>1 and ns[0] in ('JOSE','MARIA','J','MA') else ns[0]
    a=ap[0];b=am[0] if am else 'X'
    def inicial(t):return 'X' if t[0]=='Ñ' else t[0]
    def interna(t,pat):
        match=re.search(pat,t[1:]);return match[0].replace('Ñ','X') if match else 'X'
    if not isinstance(nacimiento,date):nacimiento=date.fromisoformat(str(nacimiento))
    prefijo=inicial(a)+interna(a,r'[AEIOU]')+inicial(b)+inicial(n)
    # Los casos especiales siempre se contrastan con la constancia oficial.
    inconvenientes={'BACA','BAKA','BUEI','BUEY','CACA','CACO','CAGA','CAGO','CAKA','CAKO','COGE','COGI','COJA','COJE','COJI','COJO','COLA','CULO','FALO','FETO','GETA','GUEI','GUEY','JETA','JOTO','KACA','KACO','KAGA','KAGO','KAKA','KAKO','KOGE','KOGI','KOJA','KOJE','KOJI','KOJO','KOLA','KULO','LILO','LOCA','LOCO','LOKA','LOKO','MAME','MAMO','MEAR','MEAS','MEON','MIAR','MION','MOCO','MOKO','MULA','MULO','NACA','NACO','PEDA','PEDO','PENE','PIPI','PITO','POPO','PUTA','PUTO','QULO','RATA','ROBA','ROBE','ROBO','RUIN','SENO','TETA','VACA','VAGA','VAGO','VAKA','VUEI','VUEY','WUEI','WUEY'}
    if prefijo in inconvenientes:prefijo=prefijo[0]+'X'+prefijo[2:]
    return prefijo+nacimiento.strftime('%y%m%d')+sexo+ENTIDADES[entidad]+interna(a,r'[B-DF-HJ-NÑP-TV-Z]')+interna(b,r'[B-DF-HJ-NÑP-TV-Z]')+interna(n,r'[B-DF-HJ-NÑP-TV-Z]')


def comprobar_fecha_curp(curp,nacimiento):
    if curp[4:10]!=nacimiento.strftime('%y%m%d'):
        raise ValueError('La fecha de nacimiento no coincide con la CURP. Revisa la constancia antes del alta.')
