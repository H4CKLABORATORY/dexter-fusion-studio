"""Interfaz personal Windows, offline, sin dependencias UI externas."""
from __future__ import annotations
import json,queue,subprocess,sys,threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk,messagebox,filedialog,simpledialog
from .project import create_project,seed_personal_knowledge,PROFILES,read_json,safe_write,detect_profile
from .media import probe
from .engine import EFFECTS,generate_plan,export_plan
from .library import import_scripts,add_meme
from .integrations import scan,export_mcp_client_config,defaults,render_filmcraft_project,render_effectcraft_project
from .concat_bridge import create_concat_edit,list_concat_effects
from .timeline_ui import TimelinePanel
from .ai_local import capabilities as ai_capabilities, transcribe_local as ai_transcribe_local, analyze as ai_analyze, draft as ai_draft, approve_draft as ai_approve_draft
from .chatgpt_bridge import make_packet as chatgpt_packet, import_response as chatgpt_import, approve_response as chatgpt_approve

HOME=Path.home()/'Documents'/'DexterFusionStudio'
class Window:
    def __init__(self,root):
        self.root=root;root.title('DEXTER FUSION STUDIO — Editor personal')
        root.geometry('1020x785');root.minsize(800,640)
        self.workspace=tk.StringVar(value=str(HOME))
        self.input=tk.StringVar();self.title=tk.StringVar(value='Free Fire: nueva grabación')
        self.profile=tk.StringVar(value='Automático');self.platform=tk.StringVar(value='tiktok')
        self.effect=tk.StringVar(value='hype');self.cut=tk.StringVar(value='hard')
        self.silence=tk.BooleanVar(value=False);self.duration=tk.StringVar(value='30')
        self.script=tk.StringVar();self.captions=tk.StringVar();self.watermark=tk.StringVar()
        self.active=None;self.tasks=queue.Queue();self.running=False
        self.tabs=ttk.Notebook(root);self.tabs.pack(fill='both',expand=True,padx=12,pady=9)
        self.tab('Proyecto',self.create_tab)
        self.tab('Edición automática',self.edit_tab)
        self.tab('Efectos y memes',self.effects_tab)
        self.tab('Timeline v2',self.timeline_tab)
        self.tab('IA local · Etapa 3',self.ai_tab)
        self.tab('ChatGPT · Editor asistido',self.chatgpt_tab)
        self.tab('Nuevos contenidos',self.modes_tab)
        self.tab('Integraciones',self.integrations_tab)
        bottom=ttk.Frame(root,padding=(15,0,15,12));bottom.pack(fill='both')
        ttk.Label(bottom,text='Registro de actividades').pack(anchor='w')
        self.logs=tk.Text(bottom,height=6,wrap='word');self.logs.pack(fill='both')
        self.root.after(120,self.poll)
        seed_personal_knowledge(HOME)
        custom=read_json(HOME/'custom-profiles.json',{})
        PROFILES.update({key:val for key,val in custom.items() if key not in PROFILES})
        self.combo.configure(values=['Automático']+list(PROFILES))
        self.log('Listo. Selecciona una grabación y crea un proyecto. Todo el material queda en tu PC.')
    def tab(self,name,fn):
        page=ttk.Frame(self.tabs,padding=14);self.tabs.add(page,text=name);fn(page)
    def line(self,page,label,value,button=None,action=None):
        row=ttk.Frame(page);row.pack(fill='x',pady=6)
        ttk.Label(row,text=label,width=24).pack(side='left')
        ttk.Entry(row,textvariable=value).pack(side='left',fill='x',expand=True)
        if button:ttk.Button(row,text=button,command=action).pack(side='left',padx=6)
    def file(self,var,patterns):
        f=filedialog.askopenfilename(filetypes=[('Archivos',patterns)])
        if f:var.set(f)
    def create_tab(self,p):
        ttk.Label(p,text='Tu nuevo estudio de video',font=('Segoe UI',17,'bold')).pack(anchor='w',pady=(0,12))
        self.line(p,'Carpeta de trabajo',self.workspace,'Carpeta',self.pick_workspace)
        self.line(p,'Grabación',self.input,'Abrir',lambda:self.file(self.input,'*.mp4 *.mov *.mkv *.avi *.webm'))
        self.line(p,'Nombre del video',self.title)
        row=ttk.Frame(p);row.pack(fill='x',pady=7)
        ttk.Label(row,text='Tipo de contenido',width=24).pack(side='left')
        self.combo=ttk.Combobox(row,textvariable=self.profile,values=['Automático']+list(PROFILES),state='readonly',width=30)
        self.combo.pack(side='left')
        ttk.Button(row,text='Detectar tipo',command=self.classify).pack(side='left',padx=8)
        ttk.Button(p,text='Crear proyecto',command=self.create).pack(anchor='w',pady=14)
        self.project_label=ttk.Label(p,text='Sin proyecto activo',wraplength=770)
        self.project_label.pack(anchor='w',pady=10)
        ttk.Label(p,text='Los videos se referencian por su ruta. No se duplican ni se suben a la nube.').pack(anchor='w')
    def edit_tab(self,p):
        ttk.Label(p,text='Automatización de recortes y subtítulos',font=('Segoe UI',15,'bold')).pack(anchor='w',pady=(0,12))
        self.line(p,'Guion disponible',self.script,'Buscar',lambda:self.file(self.script,'*.txt *.md'))
        self.line(p,'Subtítulos (SRT)',self.captions,'Buscar',lambda:self.file(self.captions,'*.srt'))
        self.line(p,'Marca de agua (PNG)',self.watermark,'Buscar',lambda:self.file(self.watermark,'*.png *.webp'))
        row=ttk.Frame(p);row.pack(fill='x',pady=7)
        ttk.Label(row,text='Destino',width=24).pack(side='left')
        ttk.Combobox(row,textvariable=self.platform,values=['youtube','shorts','tiktok'],state='readonly',width=17).pack(side='left')
        ttk.Label(row,text='Duración máx. (0=todo)').pack(side='left',padx=8)
        ttk.Entry(row,textvariable=self.duration,width=9).pack(side='left')
        ttk.Checkbutton(p,text='Sugerir recortes por silencios (revisar resultado)',variable=self.silence).pack(anchor='w',pady=5)
        row=ttk.Frame(p);row.pack(anchor='w',pady=16)
        ttk.Button(row,text='1. Crear plan',command=self.plan).pack(side='left')
        ttk.Button(row,text='2. Exportar MP4',command=self.render).pack(side='left',padx=8)
        ttk.Button(row,text='Ver carpeta de salida',command=self.show_output).pack(side='left')
        ttk.Label(p,text='El plan es un JSON editable. Lo que aún necesita inteligencia audiovisual no se presenta como automático.').pack(anchor='w')
    def effects_tab(self,p):
        ttk.Label(p,text='Efectos realmente disponibles',font=('Segoe UI',15,'bold')).pack(anchor='w',pady=(0,12))
        for code,item in EFFECTS.items():
            ttk.Radiobutton(p,text=item['label']+'  ('+code+')',variable=self.effect,value=code).pack(anchor='w',pady=3)
        row=ttk.Frame(p);row.pack(fill='x',pady=10)
        ttk.Label(row,text='Transiciones').pack(side='left')
        ttk.Combobox(row,textvariable=self.cut,values=['hard','fade','crossfade'],state='readonly',width=15).pack(side='left',padx=10)
        ttk.Label(p,text='fade = fundido a negro entre segmentos; no es crossfade.').pack(anchor='w')
        ttk.Button(p,text='Importar meme de imagen con etiquetas',command=self.meme).pack(anchor='w',pady=10)
        ttk.Label(p,text='Memes sugeridos por palabras del SRT. Elige cuáles insertar (no se insertan sin aprobación).',wraplength=720).pack(anchor='w')
        ttk.Button(p,text='Revisar y aprobar memes sugeridos',command=self.approve_memes).pack(anchor='w',pady=8)
    def timeline_tab(self,p):
        self.timeline_panel=TimelinePanel(self,p)
    def ai_tab(self,p):
        ttk.Label(p,text='Asistente de IA local · Etapa 3',font=('Segoe UI',16,'bold')).pack(anchor='w',pady=(0,10))
        ttk.Label(p,text='Transcribe tu voz, analiza señales de tu video y crea un borrador de clips. '
                        'Ollama analiza sólo fotogramas y puede equivocarse. Tu revisión sigue siendo obligatoria.',
                  wraplength=750).pack(anchor='w',pady=(0,12))
        self.ai_model=tk.StringVar(value='llava')
        self.ai_whisper=tk.StringVar(value='tiny')
        self.ai_device=tk.StringVar(value='cpu')
        self.ai_vision=tk.BooleanVar(value=False)
        self.ai_frames=tk.StringVar(value='4')
        self.ai_scan=tk.StringVar(value='180')
        ttk.Button(p,text='Comprobar lo que está instalado',command=self.ai_check).pack(anchor='w',pady=7)
        row=ttk.Frame(p);row.pack(fill='x',pady=5)
        ttk.Label(row,text='Modelo Whisper',width=20).pack(side='left')
        ttk.Entry(row,textvariable=self.ai_whisper,width=16).pack(side='left',padx=4)
        ttk.Label(row,text='Dispositivo').pack(side='left',padx=6)
        ttk.Combobox(row,textvariable=self.ai_device,values=['cpu','cuda','auto'],
                     state='readonly',width=9).pack(side='left',padx=4)
        ttk.Button(p,text='1. Transcribir mi voz localmente',command=self.ai_transcribe).pack(anchor='w',pady=8)
        ttk.Separator(p).pack(fill='x',pady=9)
        ttk.Checkbutton(p,text='Usar además Ollama LOCAL (no envía fotogramas a la nube)',
                        variable=self.ai_vision).pack(anchor='w',pady=7)
        row=ttk.Frame(p);row.pack(fill='x',pady=5)
        ttk.Label(row,text='Modelo visual instalado',width=20).pack(side='left')
        ttk.Entry(row,textvariable=self.ai_model,width=18).pack(side='left',padx=4)
        ttk.Label(row,text='Fotogramas').pack(side='left',padx=6)
        ttk.Entry(row,textvariable=self.ai_frames,width=6).pack(side='left',padx=4)
        ttk.Label(row,text='Analizar hasta (s)').pack(side='left',padx=6)
        ttk.Entry(row,textvariable=self.ai_scan,width=8).pack(side='left',padx=4)
        ttk.Button(p,text='2. Analizar video / proponer momentos',command=self.ai_analyze_ui).pack(anchor='w',pady=8)
        row=ttk.Frame(p);row.pack(anchor='w',pady=9)
        ttk.Button(row,text='3. Crear borrador de clips',command=self.ai_draft_ui).pack(side='left')
        ttk.Button(row,text='4. Aceptar borrador en el Timeline',command=self.ai_accept_ui).pack(side='left',padx=8)
        ttk.Label(p,text='Orden sugerido: transcribir → analizar → proponer → revisar JSON → aceptar → '
                        'abrir Timeline v2 → preparar y exportar. Ningún paso publica a TikTok.',
                  wraplength=720).pack(anchor='w',pady=10)
        ttk.Label(p,text='Importante: los modelos Whisper pueden descargarse la primera vez. '
                        'Ollama debe instalarse y contar con un modelo visual; no se instala automáticamente.',
                  wraplength=720).pack(anchor='w')

    def ai_check(self):
        self.log('Módulos disponibles: '+json.dumps(ai_capabilities(),ensure_ascii=False))

    def ai_transcribe(self):
        try:folder=self.require()
        except Exception as exc:messagebox.showerror('Proyecto',str(exc));return
        model=self.ai_whisper.get().strip();device=self.ai_device.get()
        target=folder/'previews'/'ai-transcript.srt'
        replace=target.exists() and messagebox.askyesno('SRT existente','¿Volver a transcribir y reemplazar este SRT?')
        if target.exists() and not replace:return
        def completed(info):
            self.captions.set(info['subtitle_file'])
            config=read_json(folder/'project.json')
            config['subtitle_file']=info['subtitle_file']
            safe_write(folder/'project.json',config)
            self.log('Subtítulos vinculados al proyecto. Revísalos antes de renderizar.')
        self.background('Transcripción local Whisper',lambda:ai_transcribe_local(
            folder,model=model,device=device,compute_type='float16' if device=='cuda' else 'int8',
            overwrite=replace),completed)

    def ai_analyze_ui(self):
        try:
            folder=self.require()
            frames=int(self.ai_frames.get());scan=float(self.ai_scan.get())
            if not 1<=frames<=12 or not 10<=scan<=3600:raise ValueError('Fotogramas 1-12; análisis 10-3600 s')
        except Exception as exc:messagebox.showerror('Análisis',str(exc));return
        vision=self.ai_vision.get();model=self.ai_model.get().strip()
        if vision and not messagebox.askyesno('Visión local voluntaria',
                '¿Autorizar a Ollama, instalado en tu computadora, a procesar hasta '
                +str(frames)+' fotogramas de la grabación? No se ejecuta ninguna API de pago.'):
            return
        target=folder/'ai-analysis.json'
        overwrite=target.exists() and messagebox.askyesno('Reemplazar análisis','¿Sustituir el análisis anterior?')
        if target.exists() and not overwrite:return
        self.background('Analizar video sin nube',lambda:ai_analyze(
            folder,vision=vision,model=model,max_frames=frames,scan_seconds=scan,
            overwrite=overwrite))

    def ai_draft_ui(self):
        try:folder=self.require()
        except Exception as exc:messagebox.showerror('Proyecto',str(exc));return
        target=folder/'ai-proposed-timeline.json'
        overwrite=target.exists() and messagebox.askyesno('Propuesta previa','¿Reemplazar el borrador?')
        if target.exists() and not overwrite:return
        self.background('Crear borrador de escenas',lambda:ai_draft(folder,limit=4,overwrite=overwrite))

    def ai_accept_ui(self):
        try:folder=self.require()
        except Exception as exc:messagebox.showerror('Proyecto',str(exc));return
        if not messagebox.askyesno('Revisar y aceptar',
            '¿Ya revisaste ai-proposed-timeline.json? Se aplicarán sus clips al Timeline v2. '
            'El video original no cambia.'):
            return
        exists=(folder/'timeline-v2.json').exists()
        overwrite=exists and messagebox.askyesno('Respaldo y reemplazo',
            'Ya existe un Timeline. ¿Guardar copia antes de reemplazarlo con la propuesta?')
        if exists and not overwrite:return
        def completed(value):
            self.timeline_panel.load()
            self.log('Timeline listo para revisión final y exportación.')
        self.background('Aceptar cortes propuestos',lambda:ai_approve_draft(folder,overwrite=overwrite),completed)

    def chatgpt_tab(self,p):
        ttk.Label(p,text='ChatGPT + Dexter Fusion Studio',font=('Segoe UI',16,'bold')).pack(anchor='w',pady=(0,12))
        ttk.Label(p,text='Modo gratuito: prepara un paquete de cortes y subtítulos, lo compartes '
                        'con ChatGPT cuando tú quieras e importas la respuesta JSON. '
                        'Esta pestaña NO accede a tu cuenta de ChatGPT ni usa API de pago.',
                  wraplength=740).pack(anchor='w',pady=(0,15))
        ttk.Button(p,text='1. Preparar paquete para ChatGPT',command=self.chatgpt_export_ui).pack(anchor='w',pady=9)
        ttk.Label(p,text='Se crearán chatgpt-request.json y chatgpt-instructions.txt. '
                        'Revísalos: pueden contener tus diálogos antes de compartirlos.',
                  wraplength=740).pack(anchor='w',pady=(0,12))
        ttk.Button(p,text='2. Importar respuesta JSON de ChatGPT',command=self.chatgpt_import_ui).pack(anchor='w',pady=9)
        ttk.Label(p,text='Se validan los tiempos, los efectos y el proyecto correcto. '
                        'El resultado se guarda aparte como propuesta, sin cambiar la edición.',
                  wraplength=740).pack(anchor='w',pady=(0,12))
        ttk.Button(p,text='3. Aceptar la propuesta revisada',command=self.chatgpt_accept_ui).pack(anchor='w',pady=9)
        ttk.Label(p,text='La edición anterior se protege y solo puede reemplazarse con confirmación; '
                        'después revisa el Timeline v2 y exporta el MP4.',
                  wraplength=740).pack(anchor='w',pady=10)
        ttk.Separator(p).pack(fill='x',pady=15)
        ttk.Label(p,text='API automática (opcional y no habilitada)',font=('Segoe UI',11,'bold')).pack(anchor='w')
        ttk.Label(p,text='La API de OpenAI se factura por separado de ChatGPT Plus. '
                        'Este modo requiere configurar OPENAI_API_KEY en tu propia PC y autorizar '
                        'cada petición mediante el comando chatgpt-api --allow-paid-api. '
                        'Jamás pegues una clave en ChatGPT o en GitHub.',
                  wraplength=740).pack(anchor='w',pady=7)

    def chatgpt_export_ui(self):
        try:folder=self.require()
        except Exception as exc:messagebox.showerror('Proyecto',str(exc));return
        target=folder/'chatgpt-request.json'
        replace=target.exists() and messagebox.askyesno('Actualizar paquete','¿Reemplazar el paquete de ChatGPT anterior?')
        if target.exists() and not replace:return
        self.background('Preparar paquete ChatGPT',lambda:chatgpt_packet(folder,overwrite=replace))

    def chatgpt_import_ui(self):
        try:folder=self.require()
        except Exception as exc:messagebox.showerror('Proyecto',str(exc));return
        chosen=filedialog.askopenfilename(title='Respuesta de ChatGPT en JSON',
            filetypes=[('JSON o TXT','*.json *.txt')])
        if not chosen:return
        target=folder/'chatgpt-proposed-timeline.json'
        replace=target.exists() and messagebox.askyesno('Actualizar propuesta','¿Reemplazar la propuesta anterior?')
        if target.exists() and not replace:return
        self.background('Validar respuesta ChatGPT',lambda:chatgpt_import(folder,chosen,overwrite=replace))

    def chatgpt_accept_ui(self):
        try:folder=self.require()
        except Exception as exc:messagebox.showerror('Proyecto',str(exc));return
        if not messagebox.askyesno('Aceptar cortes',
            '¿Ya revisaste chatgpt-proposed-timeline.json? Se copiará al Timeline v2.'):
            return
        target=folder/'timeline-v2.json'
        replace=target.exists() and messagebox.askyesno('Backup y sustitución',
            'Ya existe un montaje. ¿Guardar respaldo y reemplazarlo?')
        if target.exists() and not replace:return
        def finish(data):
            self.timeline_panel.load()
            self.log('Propuesta aplicada; revisa la edición en Timeline v2.')
        self.background('Aceptar propuesta ChatGPT',lambda:chatgpt_approve(folder,overwrite=replace),finish)

    def modes_tab(self,p):
        ttk.Label(p,text='Biblioteca y futuros contenidos',font=('Segoe UI',15,'bold')).pack(anchor='w',pady=(0,14))
        ttk.Button(p,text='Importar todos mis guiones (.txt/.md/.srt)',command=self.import_scripts).pack(anchor='w',pady=6)
        ttk.Button(p,text='Ver conocimientos conocidos',command=self.knowledge).pack(anchor='w',pady=6)
        ttk.Label(p,text='Nuevos tipos, sin reprogramar:').pack(anchor='w',pady=(15,3))
        self.new_mode=tk.StringVar();self.new_keywords=tk.StringVar()
        self.line(p,'Nombre de estilo nuevo',self.new_mode)
        self.line(p,'Palabras clave',self.new_keywords)
        ttk.Button(p,text='Añadir tipo de contenido',command=self.add_profile).pack(anchor='w',pady=8)
        ttk.Label(p,text='Cuando el sistema no reconoce claramente el contenido, pregunta su tipo, objetivo, plataforma y estilo.').pack(anchor='w')
    def integrations_tab(self,p):
        ttk.Label(p,text='Conexiones locales opcionales',font=('Segoe UI',15,'bold')).pack(anchor='w',pady=(0,14))
        ttk.Button(p,text='Detectar programas instalados',command=self.scan).pack(anchor='w',pady=7)
        ttk.Button(p,text='Crear configuración MCP para FilmCraft/EffectCraft',command=self.mcp).pack(anchor='w',pady=7)
        ttk.Button(p,text='Enviar edit a Concat (JSON-RPC + token)',command=self.concat).pack(anchor='w',pady=7)
        ttk.Button(p,text='Consultar biblioteca de efectos Concat',command=self.concat_effects).pack(anchor='w',pady=7)
        ttk.Button(p,text='Exportar proyecto FilmCraft (.fcproj)',command=self.export_filmcraft).pack(anchor='w',pady=7)
        ttk.Button(p,text='Exportar proyecto EffectCraft (.ecproj)',command=self.export_effectcraft).pack(anchor='w',pady=7)
        ttk.Label(p,text='Concat requiere iniciar su API local y pegar su token. No se publica el token. FilmCraft y EffectCraft tienen CLI/MCP separados.',wraplength=750).pack(anchor='w',pady=10)
        ttk.Label(p,text='No se instala software externo desde el editor. El resultado básico funciona solo con FFmpeg.').pack(anchor='w')
    def pick_workspace(self):
        p=filedialog.askdirectory();
        if p:self.workspace.set(p)
    def log(self,text):
        if not hasattr(self,'logs'):return
        self.logs.insert('end',text+'\n');self.logs.see('end')
    def background(self,label,fn,callback=None):
        if self.running:messagebox.showinfo('En curso','Espera a la tarea anterior');return
        self.running=True;self.log('▶ '+label)
        def worker():
            try:self.tasks.put((True,fn(),callback))
            except Exception as e:self.tasks.put((False,str(e),None))
        threading.Thread(target=worker,daemon=True).start()
    def poll(self):
        try:
            while True:
                ok,value,callback=self.tasks.get_nowait();self.running=False
                if ok:
                    self.log('✓ '+str(value))
                    if callback:callback(value)
                else:
                    self.log('ERROR: '+value);messagebox.showerror('Error',value)
        except queue.Empty:pass
        self.root.after(120,self.poll)
    def classify(self):
        profile=detect_profile(self.title.get(),filename=Path(self.input.get()).stem)
        self.log('Análisis del tipo (solo texto): '+json.dumps(profile,ensure_ascii=False))
        if profile['profile']:self.profile.set(profile['profile'])
        else:messagebox.showinfo('Necesito una decisión','No hay evidencia suficiente. Elige un método o créalo en Nuevos contenidos.')
    def create(self):
        src=self.input.get(); name=self.title.get(); profile=self.profile.get()
        if profile=='Automático':
            self.classify();profile=self.profile.get()
            if profile=='Automático':return
        goal=simpledialog.askstring('Propósito','¿Para qué quieres este video?',initialvalue='entretenimiento')
        if goal is None:return
        platform=simpledialog.askstring('Destino','¿YouTube, Shorts o TikTok?',initialvalue=PROFILES[profile]['format'])
        if platform is None:return
        platform=platform.lower().strip()
        if platform not in ('youtube','shorts','tiktok'):
            messagebox.showerror('Destino','youtube, shorts o tiktok');return
        workspace=self.workspace.get()
        def work():return create_project(workspace,name,src,profile,goal,platform)
        def done(info):
            self.active=info[0];self.project_label.configure(text='Proyecto: '+str(self.active));self.platform.set(info[1]['platform']);self.effect.set(info[1]['effects']);self.duration.set(str(info[1]['maximum_length']));self.log('Archivos conservados en: '+str(self.active))
        self.background('Crear proyecto',work,done)
    def require(self):
        if not self.active:raise ValueError('Crea un proyecto primero')
        return self.active
    def plan(self):
        try:folder=self.require();duration=float(self.duration.get());
        except Exception as e:messagebox.showerror('Datos',str(e));return
        workspace=self.workspace.get()
        selections={'platform':self.platform.get(),'effects':self.effect.get(),'cut_style':self.cut.get(),'subtitle_file':self.captions.get() or None,'guion':self.script.get() or None,'watermark_file':self.watermark.get() or None}
        use_silence=self.silence.get()
        def work():
            p=read_json(folder/'project.json');p['meme_assets']=read_json(Path(workspace)/'memes'/'index.json',{'assets':[]}).get('assets',[])
            p.update(selections)
            safe_write(folder/'project.json',p)
            plan=generate_plan(folder,auto_silence=use_silence,max_duration=duration)
            return 'Plan preparado: '+str(folder/'edit-plan.json')+'; clips '+str(len(plan['clips']))
        self.background('Analizar grabación y planificar edición',work)
    def render(self):
        try:folder=self.require()
        except Exception as e:messagebox.showerror('Proyecto',str(e));return
        self.background('Exportar video MP4',lambda:export_plan(folder,overwrite=False))
    def show_output(self):
        if not self.active:return
        folder=self.active/'output'
        try:
            if sys.platform=='win32':subprocess.Popen(['explorer',str(folder)])
            else:self.log('Ruta: '+str(folder))
        except Exception as e:self.log(str(e))
    def approve_memes(self):
        try:folder=self.require()
        except Exception as exc:messagebox.showerror('Proyecto',str(exc));return
        filename=folder/'edit-plan.json';p=read_json(filename,{})
        if not p:messagebox.showinfo('Plan','Crea un plan de edición primero.');return
        candidates=p.get('meme_suggestions',[])
        if not candidates:messagebox.showinfo('Memes','No se encontraron etiquetas que coincidan con los subtítulos.');return
        selected=[]
        for row in candidates:
            prompt=f"Palabra: {row['trigger']}\nSegundo: {row['start']:.1f}\nArchivo: {Path(row['path']).name}\n\n¿Insertar este meme?"
            if messagebox.askyesno('Revisar meme',prompt):
                selected.append({'path':row['path'],'start':row['start'],'end':row['end'],'approved':True})
        p['meme_events_approved']=selected;safe_write(filename,p)
        self.log('Memes aprobados: '+str(len(selected)))

    def import_scripts(self):
        directory=filedialog.askdirectory()
        if directory:
            workspace=self.workspace.get()
            self.background('Importar guiones',lambda:import_scripts(workspace,directory))
    def meme(self):
        image=filedialog.askopenfilename(filetypes=[('Imagen','*.png *.jpg *.jpeg *.webp')])
        if not image:return
        tags=simpledialog.askstring('Etiquetas','Palabras clave para sugerir este meme:')
        if tags is None:return
        if not messagebox.askyesno('Derechos','¿Es tuyo o tienes autorización para incluirlo en videos?'):return
        workspace=self.workspace.get()
        self.background('Guardar meme',lambda:add_meme(workspace,image,tags))
    def knowledge(self):
        files=seed_personal_knowledge(self.workspace.get())
        self.log('Conocimiento base: '+str(files[0]))
        data=read_json(files[0]);messagebox.showinfo('Estilo conocido',json.dumps(data,ensure_ascii=False,indent=2)[:1800])
    def add_profile(self):
        import re
        name=self.new_mode.get().strip();kw=self.new_keywords.get().strip()
        if not name or not kw:messagebox.showerror('Falta información','Agrega nombre y palabras clave');return
        ident=re.sub(r'[^a-z0-9]+','-',name.lower()).strip('-')
        if not ident or ident in PROFILES:messagebox.showerror('Duplicado','Otro método con ese nombre ya existe');return
        platform=simpledialog.askstring('Formato','¿YouTube, Shorts o TikTok?',initialvalue='youtube')
        if not platform or platform.strip() not in ('youtube','shorts','tiktok'):return
        goal=simpledialog.askstring('Objetivo','¿Para qué harás ese contenido?',initialvalue='informar')
        if goal is None:return
        style={'name':name,'keywords':[x.strip() for x in kw.split(',') if x.strip()], 'format':platform.strip(),'duration':0 if platform.strip()=='youtube' else 30,'effects':'clean','kind':'long' if platform.strip()=='youtube' else 'short','goal':goal}
        PROFILES[ident]=style
        path=Path(self.workspace.get())/'custom-profiles.json'
        obj=read_json(path,{});obj[ident]=style;safe_write(path,obj)
        self.combo.configure(values=['Automático']+list(PROFILES))
        self.profile.set(ident);self.log('Nuevo método guardado: '+name)
    def scan(self):
        self.log('Instalaciones: '+json.dumps(scan(),ensure_ascii=False))
    def mcp(self):
        out=Path(self.workspace.get())/'mcp-integrations.json'
        names=export_mcp_client_config(out,defaults())
        self.log('MCP '+str(out)+'; motores encontrados: '+', '.join(names or ['ninguno']))
    def export_filmcraft(self):
        project=filedialog.askopenfilename(filetypes=[('FilmCraft','*.fcproj')])
        if not project:return
        output=filedialog.asksaveasfilename(defaultextension='.mp4',filetypes=[('Video','*.mp4')])
        if not output:return
        cli=defaults()['filmcraft_cli']
        self.background('Render FilmCraft externo',lambda:render_filmcraft_project(cli,project,output))

    def export_effectcraft(self):
        project=filedialog.askopenfilename(filetypes=[('EffectCraft','*.ecproj')])
        if not project:return
        output=filedialog.asksaveasfilename(defaultextension='.mp4',filetypes=[('Video','*.mp4')])
        if not output:return
        comp=simpledialog.askstring('Composición','Nombre de la composición a exportar:',initialvalue='Main')
        if not comp:return
        cli=defaults()['effectcraft_cli']
        self.background('Render EffectCraft externo',lambda:render_effectcraft_project(cli,project,output,comp))

    def concat_effects(self):
        token=simpledialog.askstring('Concat','Token local para consultar catálogo de efectos:',show='*')
        if not token:return
        def result(items):
            self.log('Concat: efectos reales disponibles '+str(len(items)))
            if items:
                rows='\n'.join(item.get('id','')+' — '+item.get('name','') for item in items[:55])
                dialog=tk.Toplevel(self.root);dialog.title('Catálogo Concat (primeros 55)')
                widget=tk.Text(dialog,width=95,height=26);widget.pack(fill='both',expand=True)
                widget.insert('1.0',rows);widget.configure(state='disabled')
        self.background('Consultar catálogo Concat',lambda:list_concat_effects(token),result)

    def concat(self):
        try:folder=self.require()
        except Exception as e:messagebox.showerror('Proyecto',str(e));return
        token=simpledialog.askstring('Concat local','Token de Settings > Remote (no se guarda):',show='*')
        if not token:return
        effect=simpledialog.askstring('Efecto Concat','ID opcional de efecto del catálogo (vacío=sin efecto):',initialvalue='')
        if effect is None:return
        self.background('Crear proyecto en Concat',lambda:create_concat_edit(folder,token,effect_id=effect.strip() or None))

def run_gui():
    from .runtime_windows import configure_runtime
    from .windows_setup import first_launch
    configure_runtime()
    root=tk.Tk();Window(root)
    root.after(900, lambda: first_launch(root))
    root.mainloop()
