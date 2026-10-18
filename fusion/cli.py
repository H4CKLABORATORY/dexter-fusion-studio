"""Interfaz oficial de automatización local del estudio; estable y transparente."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from .project import create_project,read_json
from .phase2 import build_timeline,apply_timeline,validate_timeline
from .engine import export_plan,EFFECTS
from .creator_mode import analyze_retakes, apply_reviewed_retakes
from .director import parse_prompt, render_motion, reference_to_timeline, reference_cuts
from .media import probe


def parser():
    p=argparse.ArgumentParser(description='Dexter Fusion Studio CLI · FFmpeg local')
    actions=p.add_subparsers(dest='action',required=True)
    q=actions.add_parser('create',help='Crear proyecto sin editar originales')
    q.add_argument('--workspace',required=True);q.add_argument('--name',required=True)
    q.add_argument('--source',required=True)
    q.add_argument('--profile',default='freefire_short')
    q.add_argument('--platform',choices=['youtube','tiktok','shorts'])
    q=actions.add_parser('timeline',help='Crear propuestas y timeline editable')
    q.add_argument('--project',required=True)
    q.add_argument('--highlights',action='store_true')
    q.add_argument('--remove-silences',action='store_true')
    q.add_argument('--no-auto-effects',action='store_true')
    q.add_argument('--window',type=float,default=12)
    q.add_argument('--limit',type=int,default=4)
    q.add_argument('--overwrite',action='store_true')
    q=actions.add_parser('prepare',help='Convertir timeline en plan revisable')
    q.add_argument('--project',required=True)
    q.add_argument('--overwrite',action='store_true')
    q=actions.add_parser('render',help='Exportar MP4 desde un plan')
    q.add_argument('--project',required=True)
    q.add_argument('--overwrite',action='store_true')
    q=actions.add_parser('retakes',help='Proponer tomas repetidas a partir de un SRT')
    q.add_argument('--project',required=True)
    q.add_argument('--apply',default='',help='Índices revisados separados por coma: 0,2')
    q.add_argument('--overwrite',action='store_true')
    q=actions.add_parser('motion',help='Crear intro animada a partir de instrucciones en español')
    q.add_argument('--prompt',required=True)
    q.add_argument('--output',required=True)
    q.add_argument('--title')
    q.add_argument('--seconds',type=float)
    q.add_argument('--platform',choices=['youtube','shorts','tiktok'])
    q.add_argument('--overwrite',action='store_true')
    q=actions.add_parser('reference',help='Usar los cortes aproximados de un video de referencia')
    q.add_argument('--project',required=True)
    q.add_argument('--reference',required=True)
    q.add_argument('--prompt',default='estilo neón')
    q.add_argument('--analyze-only',action='store_true')
    q.add_argument('--overwrite',action='store_true')
    q=actions.add_parser('status',help='Mostrar proyecto sin modificar nada')
    q.add_argument('--project',required=True)
    q=actions.add_parser('effects',help='Mostrar efectos FFmpeg reales')
    return p


def main(argv=None):
    args=parser().parse_args(argv)
    if args.action=='create':
        folder,item=create_project(args.workspace,args.name,args.source,profile=args.profile,
                                   platform=args.platform)
        response={'project':str(folder),'mode':item['profile'],'platform':item['platform']}
    elif args.action=='timeline':
        if not 2<=args.window<=90 or not 1<=args.limit<=20:
            raise ValueError('window 2-90 y limit 1-20')
        tl=build_timeline(args.project,select_highlights=args.highlights,limit=args.limit,
                          window=args.window,automatic_silence=args.remove_silences,
                          automatic_effects=not args.no_auto_effects,overwrite=args.overwrite)
        response={'timeline':str(Path(args.project)/'timeline-v2.json'),
                  'clips':len(tl['clips']),'candidates':len(tl['candidates']),
                  'review_required':tl['review_required']}
    elif args.action=='prepare':
        plan=apply_timeline(args.project,overwrite=args.overwrite)
        response={'plan':str(Path(args.project)/'edit-plan.json'),
                  'clips':len(plan['clips']),'review_required':True}
    elif args.action=='render':
        path=export_plan(args.project,overwrite=args.overwrite)
        response={'export':str(path),'media':probe(path)}
    elif args.action=='retakes':
        if args.apply:
            try:
                indices=[int(x.strip()) for x in args.apply.split(',')]
            except ValueError as exc:
                raise ValueError('Escribe índices numéricos separados por comas.') from exc
            response=apply_reviewed_retakes(args.project,suggestion_indices=indices,overwrite=args.overwrite)
        else:
            response=analyze_retakes(args.project,overwrite=args.overwrite)
            response['report_file']=str(Path(args.project).expanduser().resolve()/'retakes-report.json')
    elif args.action=='motion':
        spec=parse_prompt(args.prompt,title=args.title,seconds=args.seconds,platform=args.platform)
        path=render_motion(spec,args.output,overwrite=args.overwrite)
        response={'export':str(path),'settings':spec,'media':probe(path)}
    elif args.action=='reference':
        if args.analyze_only:
            response=reference_cuts(args.reference)
        else:
            tl=reference_to_timeline(args.project,args.reference,prompt=args.prompt,overwrite=args.overwrite)
            response={'timeline':str(Path(args.project)/'timeline-v2.json'),
                      'clips':len(tl['clips']),'analysis':tl['reference_analysis'],
                      'review_required':True}
    elif args.action=='status':
        folder=Path(args.project).expanduser().resolve()
        response={'project':str(folder),'settings':read_json(folder/'project.json'),
                  'timeline':read_json(folder/'timeline-v2.json'),
                  'prepared':(folder/'edit-plan.json').is_file()}
    else:
        response={'effects':EFFECTS,'count':len(EFFECTS)}
    print(json.dumps(response,ensure_ascii=False,indent=2))
    return response

if __name__=='__main__':
    try:main()
    except (ValueError,FileNotFoundError,RuntimeError,OSError,KeyError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)},ensure_ascii=False),file=sys.stderr)
        sys.exit(2)
