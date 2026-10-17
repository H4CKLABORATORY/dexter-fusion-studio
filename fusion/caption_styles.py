"""Render locally timed, styled ASS subtitles without a remote API.

SRT timestamps locate phrases, not individual words. Karaoke word timing is an
ESTIMATE distributed by written length; it is not forced alignment with speech.
"""
from __future__ import annotations

from html import unescape
from pathlib import Path
import math
import re

CAPTION_STYLES = ('classic', 'karaoke', 'punch')


def ass_clock(seconds: float) -> str:
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError('Invalid subtitle time')
    centis = round(seconds * 100)
    hours, centis = divmod(centis, 360000)
    minutes, centis = divmod(centis, 6000)
    secs, centis = divmod(centis, 100)
    return f'{hours}:{minutes:02}:{secs:02}.{centis:02}'


def safe_words(text: str) -> list[str]:
    """Avoid ASS override injection and strip basic formatting in SRT."""
    clean = unescape(re.sub(r'<[^>]*>', '', str(text)))
    clean = re.sub(r'[\x00-\x1f\x7f]', ' ', clean)
    clean = clean.replace('\\', '/').replace('{', '(').replace('}', ')')
    return clean.split()


def _word_weights(words: list[str]) -> list[int]:
    return [max(2, min(16, len(re.sub(r'\W', '', w, flags=re.UNICODE)))) for w in words]


def _karate_text(words: list[str], centiseconds: int) -> str:
    """Allocate karaoke durations by text length, keeping total exact."""
    weights = _word_weights(words)
    available = max(0, centiseconds - len(words))
    total = sum(weights)
    shares = [available * w / total for w in weights]
    durations = [1 + int(x) for x in shares]
    remaining = centiseconds - sum(durations)
    for index in sorted(range(len(words)), key=lambda i: (-(shares[i] % 1), i))[:remaining]:
        durations[index] += 1
    return ' '.join(f'{{\\kf{duration}}}{word}' for duration, word in zip(durations, words))


def render_ass(items: list[dict], *, width: int, height: int,
               style: str = 'karaoke') -> str:
    if style not in ('karaoke', 'punch'):
        raise ValueError('Use karaoke or punch for ASS subtitles')
    if width <= 0 or height <= 0:
        raise ValueError('Invalid frame dimensions')
    vertical = height > width
    fontsize = round(min(width, height) * (0.063 if style == 'karaoke' else 0.068))
    fontsize = max(20, fontsize)
    bottom_margin = round(height * (0.19 if vertical else 0.11))
    side_margin = round(width * 0.07)
    outline = max(2, round(fontsize * 0.065))
    header = f"""[Script Info]
Title: Dexter Fusion Studio - original animated captions
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {width}
PlayResY: {height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Dexter,Arial,{fontsize},&H00FFFFFF,&H0000CBFF,&H00110A06,&H90000000,-1,0,0,0,100,100,0,0,1,{outline},1,2,{side_margin},{side_margin},{bottom_margin},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    max_words = 3 if vertical or style == 'punch' else 5
    for item in items:
        start, end = float(item['start']), float(item['end'])
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start:
            continue
        words = safe_words(item.get('text', ''))
        if not words:
            continue
        groups = [words[i:i + max_words] for i in range(0, len(words), max_words)]
        # Do not create flashes for very dense/short SRT lines.
        if (end - start) / len(groups) < 0.10:
            groups = [words]
        weights = [sum(_word_weights(group)) for group in groups]
        total = sum(weights)
        elapsed = 0
        for group, weight in zip(groups, weights):
            a = start + (end - start) * elapsed / total
            elapsed += weight
            b = start + (end - start) * elapsed / total
            ticks = max(len(group), round((b - a) * 100))
            if b - a < 0.08:
                continue
            caption = _karate_text(group, ticks)
            if style == 'punch':
                caption = '{\\fad(70,90)\\fscx118\\fscy118\\t(0,170,\\fscx100\\fscy100)}' + caption
            else:
                caption = '{\\fad(60,75)}' + caption
            lines.append(
                f'Dialogue: 0,{ass_clock(a)},{ass_clock(b)},Dexter,,0,0,0,,{caption}'
            )
    return header + '\n'.join(lines) + ('\n' if lines else '')


def write_ass(items: list[dict], output: str | Path, *, width: int,
              height: int, style: str = 'karaoke') -> int:
    content = render_ass(items, width=width, height=height, style=style)
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return sum(x.startswith('Dialogue:') for x in content.splitlines())
