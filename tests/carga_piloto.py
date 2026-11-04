"""Ensayo HTTP local, con clientes, cuentas y sesiones independientes."""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import json
import math
import statistics
import threading
import time

import httpx


def ejecutar_carga(base, credenciales, ruta_compartida, observador, *, latencia_ms=0):
    barrera = threading.Barrier(len(credenciales))
    monitor_fin = threading.Event()
    muestras = []
    fallos_muestreo = []

    def monitorear():
        while not monitor_fin.is_set():
            try:
                muestras.append(observador())
            except Exception as exc:
                fallos_muestreo.append(type(exc).__name__)
                return
            monitor_fin.wait(0.2)

    def flujo(datos):
        cuenta, password, alumno, campo = datos
        tiempos = defaultdict(list)
        errores = []
        bytes_http = 0
        conflictos = 0
        intentos = 0
        token = None
        etapa = "inicio"
        aporte_confirmado = False
        with httpx.Client(base_url=str(base), trust_env=False, timeout=35) as cliente:
            def pedir(nombre, metodo, ruta, esperados=(200,), **kw):
                nonlocal bytes_http, intentos, etapa
                etapa = nombre
                inicio = time.perf_counter()
                intentos += 1
                if latencia_ms:
                    time.sleep(latencia_ms / 1000)
                r = cliente.request(metodo, ruta, **kw)
                tiempos[nombre].append((time.perf_counter() - inicio) * 1000)
                bytes_http += len(r.content) + len(r.request.content)
                if r.status_code not in esperados:
                    raise ValueError(f"{nombre}: HTTP {r.status_code}")
                return r

            try:
                barrera.wait(timeout=30)
                login = pedir("inicio_sesion", "POST", "/api/auth/login",
                              json={"usuario": cuenta, "password": password})
                token = login.json()["token"]
                for tramo in login.headers.get("server-timing", "").split(","):
                    nombre, sep, valor = tramo.strip().partition(";dur=")
                    if sep:
                        tiempos["ingreso_" + nombre].append(float(valor))
                cliente.headers["Authorization"] = f"Bearer {token}"
                pedir("navegacion", "GET", "/")
                pedir("navegacion", "GET", "/api/planeaciones")
                pedir("expediente", "GET", "/api/expedientes/" + alumno)
                pedir("epp", "GET", "/api/epp/" + alumno)
                ruta_anexo = f"/api/expedientes/{alumno}/anexos/5"
                pedir("captura", "POST", ruta_anexo, json={"campos": {"evento": "Observación sintética de lectura."}})
                alta = pedir("crear_plan", "POST", "/api/planeaciones/nueva",
                             json={"modalidad": "individual", "alumnos": [alumno]}).json()
                ruta = "/api/planeaciones/" + alta["id"]
                plan = pedir("abrir_plan", "GET", ruta).json()
                plan["textos"]["Evaluación"] = "Seguimiento sintético"
                time.sleep(1.5)  # Cadencia del editor. La métrica de escritura empieza al enviar HTTP.
                acuse = pedir("guardado_confirmado", "POST", "/api/planeaciones", json=plan).json()
                if not acuse.get("revision"):
                    raise ValueError("El guardado no devolvió revisión.")
                pedir("propuesta", "POST", ruta + "/propuesta", json={"enfoque": "Lectura con apoyos visuales"})
                pedir("exportacion", "GET", ruta + "/pdf")
                grupo = pedir("guia_compartida", "GET", ruta_compartida).json()
                revision = grupo["metadatos"]["revisiones_celda"]["filas"][alumno].get(campo, "")
                acuse = pedir("aporte", "PATCH", ruta_compartida + "/celda", (200, 409),
                              json={"tabla": "filas", "alumno": alumno, "campo": campo,
                                    "revision": revision, "texto": f"Aporte sintético de {cuenta} ({latencia_ms} ms)"})
                aporte_confirmado = acuse.status_code == 200
                conflictos += int(not aporte_confirmado)
                pedir("salida", "POST", "/api/auth/logout")
            except (httpx.HTTPError, ValueError, threading.BrokenBarrierError) as exc:
                errores.append({"cuenta": cuenta, "etapa": etapa, "error": str(exc)})
        return tiempos, errores, bytes_http, conflictos, token, intentos, aporte_confirmado

    monitor = threading.Thread(target=monitorear, daemon=True)
    monitor.start()
    inicio = time.perf_counter()
    try:
        with ThreadPoolExecutor(max_workers=len(credenciales)) as pool:
            resultados = list(pool.map(flujo, credenciales))
    finally:
        monitor_fin.set()
        monitor.join(timeout=5)
    por_operacion = defaultdict(list)
    for tiempos, *_ in resultados:
        for nombre, values in tiempos.items():
            por_operacion[nombre].extend(values)
    latencias = {}
    for nombre, values in sorted(por_operacion.items()):
        orden = sorted(values)
        latencias[nombre] = {"n": len(orden), "mediana_ms": round(statistics.median(orden), 1),
                             "p95_ms": round(orden[math.ceil(len(orden) * 0.95) - 1], 1)}
    tokens = {r[4] for r in resultados if r[4]}
    return {"latencia_cliente_ms": latencia_ms, "cuentas": len(credenciales), "sesiones_distintas": len(tokens),
            "duracion_s": round(time.perf_counter() - inicio, 2),
            "solicitudes": sum(r[5] for r in resultados),
            "bytes_cuerpos_http": sum(r[2] for r in resultados),
            "conflictos_409": sum(r[3] for r in resultados),
            "aportes_confirmados": sum(r[6] for r in resultados),
            "muestras_recursos": len(muestras), "fallos_muestreo": fallos_muestreo,
            "tasa_flujos_con_error_pct": round(100 * sum(bool(r[1]) for r in resultados) / len(credenciales), 2),
            "errores": [err for r in resultados for err in r[1]],
            "pico_conexiones_muestreadas": max((m[0] for m in muestras), default=0),
            "pico_rss_api_mib": max((m[1] for m in muestras), default=0),
            "latencias": latencias}


def evidencia(ruta, resultado):
    if ruta:
        from pathlib import Path
        Path(ruta).write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def memoria_mib(pid):
    import os
    if os.name != "nt":
        from pathlib import Path
        return round(int(Path(f"/proc/{pid}/statm").read_text().split()[1]) * os.sysconf("SC_PAGE_SIZE") / 2**20, 1)
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("fallos", wintypes.DWORD)] + [
            (nombre, ctypes.c_size_t) for nombre in (
                "pico", "rss", "quota_peak", "quota", "quota_np_peak", "quota_np", "page", "page_peak")
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    consultar = ctypes.WinDLL("psapi", use_last_error=True).GetProcessMemoryInfo
    consultar.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    proceso = kernel.OpenProcess(0x1000, False, pid)
    if not proceso:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        contadores = Counters(cb=ctypes.sizeof(Counters))
        if not consultar(proceso, ctypes.byref(contadores), contadores.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return round(contadores.rss / 2**20, 1)
    finally:
        kernel.CloseHandle(proceso)
