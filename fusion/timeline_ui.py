"""Pestaña de edición de timeline con revisión humana; no simula comprender videos."""
from __future__ import annotations
import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from .engine import EFFECTS, export_plan
from .media import probe
from .project import read_json,safe_write
from .phase2 import build_timeline, apply_timeline, still_preview, transcribe_local,validate_timeline
from .creator_mode import analyze_retakes


class TimelinePanel:
    def __init__(self,app,parent):
        self.app=app
        self.page=parent
        self.highlights=tk.BooleanVar(value=False)
        self.auto_effects=tk.BooleanVar(value=True)
        self.remove_silences=tk.BooleanVar(value=False)
        self.crossfade=tk.BooleanVar(value=True)
        self.effect=tk.StringVar(value='hype')
        self.zoom=tk.StringVar(value='1.0')
        self.window=tk.StringVar(value='12')
        self.limit=tk.StringVar(value='4')
        ttk.Label(parent,text='Línea de tiempo inteligente (Etapa 2)',font=('Segoe UI',15,'bold')).pack(anchor='w',pady=(0,8))
        ttk.Label(parent,text='Elige clips propuestos por cambios de escena, silencios y SRT. Corrige el montaje antes de publicar.',wraplength=800).pack(anchor='w',pady=4)
        r=ttk.Frame(parent);r.pack(anchor='w',pady=6)
        ttk.Checkbutton(r,text='Proponer highlights (heurística, no IA multimodal)',variable=self.highlights).pack(side='left')
        ttk.Checkbutton(r,text='Quitar silencios',variable=self.remove_silences).pack(side='left',padx=12)
        ttk.Checkbutton(r,text='Sugerir efectos',variable=self.auto_effects).pack(side='left',padx=12)
        row=ttk.Frame(parent);row.pack(anchor='w',pady=5)
        ttk.Label(row,text='Ventana de análisis (s):').pack(side='left')
        ttk.Entry(row,textvariable=self.window,width=7).pack(side='left',padx=5)
        ttk.Label(row,text='Clips sugeridos:').pack(side='left')
        ttk.Entry(row,textvariable=self.limit,width=6).pack(side='left',padx=5)
        ttk.Button(row,text='Generar línea de tiempo',command=self.generate).pack(side='left',padx=8)
        ttk.Button(row,text='Cargar',command=self.load).pack(side='left')
        cols=('id','start','end','effect','zoom','label')
        self.tree=ttk.Treeview(parent,columns=cols,show='headings',height=9,selectmode='browse')
        for col,width in [('id',45),('start',90),('end',90),('effect',135),('zoom',75),('label',190)]:
            self.tree.heading(col,text=col.title());self.tree.column(col,width=width,anchor='center')
        self.tree.pack(fill='both',expand=True,pady=(8,5))
        row=ttk.Frame(parent);row.pack(fill='x',pady=4)
        ttk.Button(row,text='Editar inicio/fin',command=self.adjust).pack(side='left')
        ttk.Button(row,text='Dividir en 2',command=self.split).pack(side='left',padx=5)
        ttk.Button(row,text='Eliminar clip',command=self.delete).pack(side='left',padx=5)
        ttk.Button(row,text='Subir ↑',command=lambda:self.shift(-1)).pack(side='left',padx=5)
        ttk.Button(row,text='Bajar ↓',command=lambda:self.shift(1)).pack(side='left',padx=5)
        row=ttk.Frame(parent);row.pack(anchor='w',pady=5)
        ttk.Label(row,text='Efecto:').pack(side='left')
        ttk.Combobox(row,textvariable=self.effect,values=list(EFFECTS),state='readonly',width=18).pack(side='left',padx=5)
        ttk.Label(row,text='Zoom:').pack(side='left')
        ttk.Combobox(row,textvariable=self.zoom,values=['1.0','1.05','1.10','1.15','1.25','1.35'],width=7).pack(side='left',padx=5)
        ttk.Button(row,text='Aplicar al clip',command=self.update_effect).pack(side='left',padx=8)
        ttk.Button(row,text='Vista de fotograma',command=self.preview).pack(side='left')
        row=ttk.Frame(parent);row.pack(anchor='w',pady=7)
        ttk.Checkbutton(row,text='Fundido cruzado entre clips',variable=self.crossfade).pack(side='left')
        ttk.Button(row,text='Guardar y preparar edición',command=self.prepare).pack(side='left',padx=10)
        ttk.Button(row,text='Exportar MP4',command=self.render).pack(side='left')
        ttk.Button(parent,text='Subtitular mi voz (Whisper local opcional)',command=self.whisper).pack(anchor='w',pady=7)
        ttk.Button(parent,text='Analizar tomas repetidas (requiere SRT)',command=self.retakes).pack(anchor='w',pady=5)
        ttk.Label(parent,text='Los originales y guiones no se envían a ningún servicio. Presets no equivalen a los efectos propietarios de otra app.',wraplength=800).pack(anchor='w')
        self.current=None

    def folder(self):
        if not self.app.active:raise ValueError('Primero crea un proyecto en la primera pestaña.')
        return Path(self.app.active)

    def selected(self):
        item=self.tree.selection()
        if not item:raise ValueError('Selecciona un clip en la tabla.')
        return int(item[0])

    def display(self):
        self.tree.delete(*self.tree.get_children())
        if self.current:
            for idx,clip in enumerate(self.current['clips']):
                self.tree.insert('', 'end', iid=str(idx),values=(idx+1,f"{clip['start']:.2f}",f"{clip['end']:.2f}",
                                 clip['effect'],f"{clip.get('zoom',1):.2f}",clip.get('label','')))

    def load(self):
        try:
            folder=self.folder()
            content=read_json(folder/'timeline-v2.json')
            if not content:raise FileNotFoundError('Crea la línea de tiempo primero.')
            self.current=content
            self.crossfade.set(content.get('cut_style')=='crossfade')
            self.display()
            self.app.log('Timeline cargado: '+str(len(content['clips']))+' escenas')
        except Exception as exc:messagebox.showerror('Timeline',str(exc))

    def generate(self):
        try:
            folder=self.folder()
            window=float(self.window.get());limit=int(self.limit.get())
            if not 2<=window<=90 or not 1<=limit<=20:raise ValueError('Ventana 2-90 s y 1-20 clips.')
            if (folder/'timeline-v2.json').exists() and not messagebox.askyesno('Reemplazar','Ya tienes un timeline guardado. ¿Generar uno nuevo?'):
                return
            auto=self.highlights.get();silence=self.remove_silences.get();effects=self.auto_effects.get()
            def job():return build_timeline(folder,select_highlights=auto,automatic_silence=silence,
                        window=window,limit=limit,automatic_effects=effects,overwrite=True)
            def done(data):self.current=data;self.display()
            self.app.background('Analizar escenas y preparar timeline',job,done)
        except Exception as exc:messagebox.showerror('Datos',str(exc))

    def save(self):
        folder=self.folder()
        if self.current is None:raise ValueError('No hay timeline activo.')
        self.current['cut_style']='crossfade' if self.crossfade.get() and len(self.current['clips'])>1 else 'hard'
        validate_timeline(self.current)
        safe_write(folder/'timeline-v2.json',self.current)
        self.display()

    def modify(self,callback):
        try:
            idx=self.selected()
            callback(idx)
            self.save()
        except Exception as exc:messagebox.showerror('Editar escena',str(exc))

    def adjust(self):
        def inner(idx):
            clip=self.current['clips'][idx]
            a=simpledialog.askfloat('Recorte','Inicio del fragmento (segundos)',initialvalue=clip['start'],parent=self.app.root)
            if a is None:return
            b=simpledialog.askfloat('Recorte','Final del fragmento (segundos)',initialvalue=clip['end'],parent=self.app.root)
            if b is None:return
            clip['start'],clip['end']=round(a,3),round(b,3)
        self.modify(inner)

    def split(self):
        def inner(idx):
            clip=self.current['clips'][idx]
            middle=round((clip['start']+clip['end'])/2,3)
            other=dict(clip)
            clip['end']=middle;other['start']=middle
            self.current['clips'].insert(idx+1,other)
        self.modify(inner)

    def delete(self):
        def inner(idx):
            if len(self.current['clips'])==1:raise ValueError('No se puede quitar el último clip.')
            self.current['clips'].pop(idx)
        self.modify(inner)

    def shift(self,direction):
        def inner(idx):
            other=idx+direction
            if 0<=other<len(self.current['clips']):
                self.current['clips'][idx],self.current['clips'][other]=self.current['clips'][other],self.current['clips'][idx]
        self.modify(inner)

    def update_effect(self):
        def inner(idx):
            self.current['clips'][idx]['effect']=self.effect.get()
            self.current['clips'][idx]['zoom']=float(self.zoom.get())
        self.modify(inner)

    def preview(self):
        try:
            idx=self.selected();folder=self.folder()
            path=still_preview(folder,idx)
            if hasattr(os,'startfile'):os.startfile(str(path))
            else:self.app.log('Fotograma: '+str(path))
        except Exception as exc:messagebox.showerror('Fotograma',str(exc))

    def prepare(self):
        try:
            self.save()
            folder=self.folder()
            if (folder/'edit-plan.json').exists() and not messagebox.askyesno('Plan existente','Se reemplazará el plan de edición anterior. ¿Continuar?'):
                return
            plan=apply_timeline(folder,overwrite=True)
            self.app.log(f"Plan de fase 2 guardado: {len(plan['clips'])} clips, {len(plan['subtitles'])} subtítulos")
        except Exception as exc:messagebox.showerror('Plan',str(exc))

    def render(self):
        try:folder=self.folder()
        except Exception as exc:messagebox.showerror('Proyecto',str(exc));return
        self.app.background('Exportar línea de tiempo v2',lambda:export_plan(folder,overwrite=False))

    def whisper(self):
        try:folder=self.folder()
        except Exception as exc:messagebox.showerror('Proyecto',str(exc));return
        if not messagebox.askyesno('Whisper local','Necesitas faster-whisper instalado y descargar un modelo una vez. ¿Ejecutar si está disponible?'):
            return
        self.app.background('Transcribir voz en PC local',lambda:transcribe_local(folder))

    def retakes(self):
        try:
            folder = self.folder()
            def finished(report):
                suggestions = report['suggestions']
                if not suggestions:
                    messagebox.showinfo('Modo Creador', 'No se detectaron frases repetidas de alta similitud. No se ha recortado nada.')
                    return
                brief = '\\n'.join(f"{i}: {s['start']:.1f}-{s['end']:.1f}s — {s['original_text'][:60]}" for i, s in enumerate(suggestions[:8]))
                messagebox.showinfo('Modo Creador', f"Se detectaron {len(suggestions)} posibles tomas repetidas.\\n\\n{brief}\\n\\nSe guardó retakes-report.json. No se aplicaron cortes; revísalos primero.")
            self.app.background('Analizar tomas repetidas por subtítulos', lambda:analyze_retakes(folder,overwrite=True),finished)
        except Exception as exc:
            messagebox.showerror('Modo Creador',str(exc))
