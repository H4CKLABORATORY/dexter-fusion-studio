"""Pruebas para propuestas conservadoras del Modo Creador."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fusion.creator_mode import (
    suggest_repeated_takes, analyze_retakes, apply_reviewed_retakes,
)
from fusion.project import safe_write, read_json


class CreatorModeTests(unittest.TestCase):
    def test_repeated_take_without_removing_intentional_short_repetition(self):
        rows = [
            {'start':0.0,'end':2.0,'text':'Hoy vamos a jugar una partida muy divertida'},
            {'start':2.5,'end':4.2,'text':'Hoy vamos a jugar una partida muy divertida'},
            {'start':4.5,'end':5.5,'text':'No no no'},
            {'start':5.8,'end':6.7,'text':'No no no'},
        ]
        result = suggest_repeated_takes(rows)
        self.assertEqual(len(result), 1)
        self.assertEqual((result[0]['start'], result[0]['end']), (0, 2))
        self.assertTrue(result[0]['review_required'])

    def test_unrelated_adjacent_dialogue_not_cut(self):
        rows = [
            {'start':0,'end':1,'text':'El enemigo estaba encima de la casa'},
            {'start':1.1,'end':2,'text':'Que fuerte se puso esta pelea hermano'},
        ]
        self.assertEqual(suggest_repeated_takes(rows), [])

    def test_review_required_and_original_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            video = p/'original.mp4'
            video.write_bytes(b'not changed')
            srt = p/'captions.srt'
            srt.write_text(
                '1\n00:00:00,000 --> 00:00:02,000\n'
                'Hoy vamos a jugar una partida muy divertida\n\n'
                '2\n00:00:02,500 --> 00:00:04,200\n'
                'Hoy vamos a jugar una partida muy divertida\n',
                encoding='utf-8',
            )
            safe_write(p/'project.json', {
                'source':str(video),'subtitle_file':str(srt),
            })
            report = analyze_retakes(p)
            self.assertEqual(len(report['suggestions']), 1)
            safe_write(p/'timeline-v2.json', {
                'source':str(video),
                'clips':[{'id':1,'start':0.,'end':8.,'effect':'clean','zoom':1.}],
                'cut_style':'hard','platform':'youtube','transition_seconds':.25,
            })
            with self.assertRaises(ValueError):
                apply_reviewed_retakes(p, suggestion_indices=[0])
            with patch('fusion.phase2.validate_timeline'):
                output=apply_reviewed_retakes(
                    p, suggestion_indices=[0], overwrite=True)
            self.assertEqual(output['clips'], 1)
            self.assertEqual(read_json(p/'timeline-v2.json')['clips'][0]['start'], 2.0)
            self.assertEqual(video.read_bytes(), b'not changed')


if __name__ == '__main__':
    unittest.main()
