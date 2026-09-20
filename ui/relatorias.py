import glob
import os
import shutil
import subprocess
import tempfile
from datetime import date

import streamlit as st

from ai.engine import client as gemini_client
from config.settings import GEMINI_MODEL
from documents.relatorias import generar_pdf_oficial


def _prompt(sesion, tema, notas):
    return f"""Actúa como secretario técnico de la USAER 02-E y redacta una relatoría institucional
de la sesión de Consejo Técnico Escolar indicada. No inventes hechos, acuerdos,
responsables ni fechas; omite lo que no aparezca en la grabación o notas.
Estructura el cuerpo en:
1. Contexto y desarrollo: síntesis fiel del diálogo colegiado.
2. Reflexiones y retos pedagógicos.
3. Acuerdos y compromisos: conserva responsables y plazos solo cuando se mencionen.
Redacta formal y claro; no incluyas fecha ni título principal.
Sesión: {sesion}
Tema central: {tema or "No especificado"}
Notas de Dirección: {notas or "Sin notas adicionales"}"""


def _procesar_gemini(ruta, prompt):
    cliente = gemini_client()
    if cliente is None:
        raise RuntimeError("Falta GEMINI_API_KEY en los secretos de Streamlit.")
    archivo = None
    try:
        archivo = cliente.files.upload(file=ruta)
        resultado = cliente.models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt, archivo],
        )
        texto = (getattr(resultado, "text", "") or "").strip()
        if not texto:
            raise RuntimeError("Gemini no devolvió texto.")
        return texto
    finally:
        if archivo is not None:
            try:
                cliente.files.delete(name=archivo.name)
            except Exception:
                pass


def _procesar_openai(ruta, prompt, progreso):
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        api_key = ""
    if not api_key:
        raise RuntimeError("Falta OPENAI_API_KEY en los secretos de Streamlit.")
    from openai import OpenAI

    cliente = OpenAI(api_key=api_key, timeout=900.0, max_retries=2)
    limite = 24_000_000
    directorio = None
    try:
        if os.path.getsize(ruta) <= limite:
            partes = [ruta]
        else:
            ffmpeg = shutil.which("ffmpeg")
            if not ffmpeg:
                raise RuntimeError("Para audios grandes se requiere ffmpeg; usa Gemini o instala packages.txt.")
            directorio = tempfile.TemporaryDirectory(prefix="usaer_relatoria_")
            patron = os.path.join(directorio.name, "parte_%03d.mp3")
            proceso = subprocess.run(
                [
                    ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                    "-i", ruta, "-vn", "-ac", "1", "-ar", "16000",
                    "-b:a", "48k", "-f", "segment", "-segment_time", "480",
                    "-reset_timestamps", "1", patron,
                ],
                capture_output=True, text=True, timeout=3600, check=False,
            )
            if proceso.returncode:
                raise RuntimeError("No se pudo dividir el audio: " + (proceso.stderr or "")[-600:])
            partes = sorted(glob.glob(os.path.join(directorio.name, "parte_*.mp3")))
            if not partes or any(os.path.getsize(p) > limite for p in partes):
                raise RuntimeError("No fue posible preparar segmentos menores de 25 MB.")

        textos = []
        for indice, parte in enumerate(partes, start=1):
            with open(parte, "rb") as archivo:
                texto = cliente.audio.transcriptions.create(
                    model="whisper-1", file=archivo, language="es"
                ).text
            textos.append(f"[Fragmento {indice}/{len(partes)}]\n{texto.strip()}")
            progreso(indice / len(partes), f"Transcripción {indice}/{len(partes)}")

        transcripcion = "\n\n".join(textos)
        if len(transcripcion) <= 85000:
            respuesta = cliente.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Eres secretario técnico y redactor institucional de educación especial."},
                    {"role": "user", "content": f"{prompt}\n\nTranscripción íntegra:\n{transcripcion}"},
                ],
            )
            return (respuesta.choices[0].message.content or "").strip()

        lotes = [transcripcion[i:i + 35000] for i in range(0, len(transcripcion), 35000)]
        resumenes = []
        for indice, lote in enumerate(lotes, start=1):
            resumen = cliente.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Resume fielmente una parte de una reunión escolar. No inventes acuerdos."},
                    {"role": "user", "content": f"{prompt}\nFragmento {indice}/{len(lotes)}:\n{lote}"},
                ],
            )
            resumenes.append((resumen.choices[0].message.content or "").strip())
            progreso(0.7 + 0.2 * indice / len(lotes), f"Síntesis {indice}/{len(lotes)}")
        final = cliente.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Redacta la relatoría oficial a partir de estas síntesis, sin inventar."},
                {"role": "user", "content": f"{prompt}\n\nSíntesis de toda la sesión:\n" + "\n\n".join(resumenes)},
            ],
        )
        return (final.choices[0].message.content or "").strip()
    finally:
        if directorio is not None:
            directorio.cleanup()


def generador_relatorias_director():
    st.divider()
    st.markdown("### Generador de relatorías del CTE")
    st.caption("Genera, revisa y descarga la relatoría en PDF carta con membrete, sello y hoja de firmas.")
    st.warning("El audio se enviará al proveedor de IA seleccionado. Evita incluir datos sensibles de alumnos y confirma que tienes autorización.")
    with st.expander("Abrir generador", expanded=False):
        motor = st.radio("Motor de IA", ["ChatGPT (OpenAI)", "Gemini (Google)"], horizontal=True, key="relatoria_motor")
        modo = st.radio("Captura", ["Subir archivo", "Grabar en el navegador"], horizontal=True, key="relatoria_modo")
        if modo == "Subir archivo":
            audio = st.file_uploader(
                "Audio (MP3, WAV, M4A, MP4 o WebM), máximo 400 MB",
                type=["mp3", "wav", "m4a", "mp4", "webm"],
                max_upload_size=400,
                key="relatoria_archivo",
                help="Gemini admite archivos mayores; OpenAI los divide automáticamente en partes.",
            )
        else:
            audio = st.audio_input("Grabar la sesión", key="relatoria_grabacion")
        if audio is not None:
            st.caption(f"{audio.name} · {audio.size / (1024 * 1024):.1f} MB")

        sesiones = [
            "Fase Intensiva", "Primera Sesión", "Segunda Sesión", "Tercera Sesión",
            "Cuarta Sesión", "Quinta Sesión", "Sexta Sesión", "Séptima Sesión", "Octava Sesión",
        ]
        col1, col2 = st.columns(2)
        with col1:
            sesion = st.selectbox("Sesión de CTE", sesiones, key="relatoria_sesion")
            tema = st.text_input("Tema central", placeholder="Ej. Ajustes razonables, BAP...", key="relatoria_tema")
        with col2:
            fecha = st.date_input("Fecha de la sesión", value=date.today(), key="relatoria_fecha")
            asistentes = st.number_input("Renglones para firmas", 1, 30, 6, key="relatoria_asistentes")
        notas = st.text_area("Notas de Dirección", height=120, key="relatoria_notas")
        autorizado = st.checkbox(
            "Confirmo que cuento con autorización para procesar esta grabación con el proveedor seleccionado.",
            key="relatoria_autorizacion",
        )

        if st.button("Procesar audio y generar relatoría", type="primary", width="stretch", key="procesar_relatoria"):
            if audio is None:
                st.error("Selecciona un archivo o graba la sesión.")
            elif not autorizado:
                st.error("Confirma la autorización antes de continuar.")
            elif audio.size > 400 * 1024 * 1024:
                st.error("El archivo supera el límite de 400 MB.")
            else:
                extension = os.path.splitext(getattr(audio, "name", "audio.wav"))[1] or ".wav"
                ruta = None
                barra = st.progress(0, text="Preparando el audio...")
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=extension, prefix="usaer_relatoria_") as temporal:
                        audio.seek(0)
                        temporal.write(audio.getbuffer())
                        ruta = temporal.name
                    with st.spinner("Transcribiendo y redactando..."):
                        prompt = _prompt(sesion, tema, notas)
                        callback = lambda valor, mensaje: barra.progress(valor, text=mensaje)
                        if motor == "Gemini (Google)":
                            texto = _procesar_gemini(ruta, prompt)
                        else:
                            texto = _procesar_openai(ruta, prompt, callback)
                    if not texto:
                        raise RuntimeError("No se generó contenido.")
                    st.session_state["relatoria_texto_generado"] = texto
                    st.session_state.pop("relatoria_texto_editable", None)
                    st.success("Relatoría lista para revisión.")
                except Exception as exc:
                    st.error(f"No fue posible procesar el audio: {exc}")
                finally:
                    barra.empty()
                    if ruta and os.path.exists(ruta):
                        try:
                            os.remove(ruta)
                        except OSError:
                            pass

        texto = st.session_state.get("relatoria_texto_generado")
        if texto:
            texto_editado = st.text_area(
                "Revisa y edita el cuerpo antes de descargar",
                value=texto,
                height=420,
                key="relatoria_texto_editable",
            )
            pdf = generar_pdf_oficial(
                texto_editado, asistentes, fecha=fecha, sesion=sesion, tema=tema
            )
            st.download_button(
                "Descargar relatoría oficial en PDF",
                data=pdf,
                file_name=f"Relatoria_CTE_{sesion.replace(' ', '_')}_{fecha:%Y%m%d}.pdf",
                mime="application/pdf",
                type="primary",
                width="stretch",
                key="descargar_relatoria",
            )
