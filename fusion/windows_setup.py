"""Welcome wizard: no scripts, credentials, paid subscriptions or silent downloads."""
from __future__ import annotations

from pathlib import Path
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

from .runtime_windows import environment_report

USER_DATA = Path.home() / "Documents" / "DexterFusionStudio"
FLAG = USER_DATA / ".v03-welcome-completed"


def first_launch(root):
    if FLAG.exists():
        return
    show_setup(root)


def show_setup(root):
    wizard = tk.Toplevel(root)
    wizard.title("DEXTER FF · Primera configuración")
    wizard.geometry("610x495")
    wizard.minsize(500,420)
    wizard.transient(root)

    outer=ttk.Frame(wizard,padding=20)
    outer.pack(fill="both",expand=True)
    ttk.Label(outer,text="Dexter Fusion Studio · Preparación",font=("Segoe UI",16,"bold")).pack(anchor="w",pady=(0,12))
    ttk.Label(outer,text=(
        "Ya puedes editar con herramientas locales. La IA funciona por módulos: "
        "subtítulos Whisper disponibles sin API de pago y visión Ollama opcional. "
        "Ninguna compra, instalación de terceros o descarga se hace sin avisarte."),
        wraplength=545).pack(anchor="w",pady=(0,12))
    status=tk.StringVar(value="")
    ttk.Label(outer,textvariable=status,wraplength=545).pack(anchor="w",pady=8)
    report=environment_report()

    def refresh():
        data=environment_report()
        status.set(
            ("✔ FFmpeg incluido o detectado" if data["ready_for_base_editing"]
             else "⚠ FFmpeg no detectado; la exportación aún no funcionará")+
            "\n"+
            ("✔ Motor Whisper incluido (modelo no descargado aún)"
             if data["transcription_library"] else
             "⚠ Whisper no está incluido: transcripción automática no disponible")
            +"\nOllama: opcional, se instala por separado para análisis visual."
        )
    refresh()

    def download_whisper():
        if not environment_report()["transcription_library"]:
            messagebox.showerror("Whisper", "Esta compilación no incluye faster-whisper.",parent=wizard)
            return
        if not messagebox.askyesno("Descarga gratuita",
                    "¿Descargar el modelo de voz tiny (aprox. 75 MB) en tu PC? "
                    "Necesita Internet la primera vez. No usa ninguna API de pago.",
                    parent=wizard):
            return
        status.set("Descargando y preparando modelo de voz tiny…\nPuede tardar unos minutos.")
        def work():
            try:
                from faster_whisper import WhisperModel
                WhisperModel("tiny",device="cpu",compute_type="int8")
                root.after(0, lambda: status.set("✔ Modelo de voz tiny listo para transcribir sin pago."))
            except Exception as exc:
                message=str(exc)[:300]
                root.after(0, lambda:messagebox.showerror("Modelo de voz",message,parent=wizard))
        threading.Thread(target=work,daemon=True).start()

    buttons=ttk.Frame(outer)
    buttons.pack(fill="x",pady=12)
    ttk.Button(buttons,text="Comprobar componentes",command=refresh).pack(fill="x",pady=3)
    ttk.Button(buttons,text="Preparar subtítulos IA gratis (Whisper tiny)",command=download_whisper).pack(fill="x",pady=3)
    ttk.Button(buttons,text="Ver Ollama (opcional, otro instalador)",command=lambda:webbrowser.open("https://ollama.com/download/windows")).pack(fill="x",pady=3)

    ttk.Label(outer,text=(
        "El modelo visual no viene instalado. Si quieres usarlo, "
        "instala Ollama y descarga un modelo compatible en su aplicación o consola. "
        "La conexión automática de OpenAI continúa desactivada."
    ),wraplength=545).pack(anchor="w",pady=(2,10))

    def close():
        USER_DATA.mkdir(parents=True,exist_ok=True)
        FLAG.write_text("Welcome v0.3 shown.\n",encoding="utf-8")
        wizard.destroy()
    ttk.Button(outer,text="Empezar a editar",command=close).pack(anchor="e",pady=5)
    wizard.protocol("WM_DELETE_WINDOW",close)
