"""Read and validate the collection and per-piece metadata (standard library only)."""
from dataclasses import dataclass
from fractions import Fraction
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ID_PATTERN = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def write_text(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding='utf-8') != content:
        path.write_text(content, encoding='utf-8')

def local_path(base, relative, *, required=True):
    base = Path(base).resolve()
    path = (base / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(base):
        raise ValueError(f'Path must stay inside {base}: {relative}')
    if required and not path.is_file():
        raise ValueError(f'Missing file: {path}')
    return path

def duration(value, *, zero=False):
    result = Fraction(value)
    if result < 0 or (result == 0 and not zero):
        raise ValueError(f'Invalid duration: {value}')
    return result

@dataclass
class Piece:
    root: Path
    folder: Path
    data: dict

    @property
    def id(self):
        return self.data['id']

    @property
    def source(self):
        return local_path(self.folder, self.data['source'])

    @property
    def segments(self):
        return self.data.get('segments', [])

    @property
    def output(self):
        return self.root / 'build' / 'scores' / self.id

def validate_piece(piece):
    data = piece.data
    if not ID_PATTERN.fullmatch(data.get('id', '')) or data['id'] != piece.folder.name:
        raise ValueError(f'Invalid piece ID in {piece.folder}')
    if not data.get('title') or piece.source.suffix.lower() != '.ly':
        raise ValueError(f'{piece.id}: title and a LilyPond .ly source are required')
    if data.get('overview'):
        local_path(piece.folder, data['overview'])
    engraving = data.get('engraving', {})
    if not 0 < engraving.get('line_width_mm', 164) <= 170:
        raise ValueError(f'{piece.id}: line_width_mm must fit the 170 mm A4 text area')
    if not 0 < engraving.get('staff_size', 18) <= 30:
        raise ValueError(f'{piece.id}: invalid staff_size')
    if not piece.segments:
        return
    extraction = data.get('extraction', {})
    if extraction.get('strategy') != 'bar-comments':
        raise ValueError(f'{piece.id}: practice excerpts require the bar-comments extraction profile')
    for role in ('primary', 'accompaniment', 'upper_support', 'lower_support'):
        if not re.fullmatch(r'[A-Za-z][A-Za-z_-]*', extraction.get('voices', {}).get(role, '')):
            raise ValueError(f'{piece.id}: invalid or missing voice mapping: {role}')
    names = [extraction.get('score_variable', 'pianoMusic')]
    staves = extraction.get('staves', {'upper': 'up', 'lower': 'down'})
    if set(staves) != {'upper', 'lower'}:
        raise ValueError(f'{piece.id}: upper and lower staff IDs are required')
    names.extend(staves.values())
    if any(not re.fullmatch(r'[A-Za-z][A-Za-z_-]*', name) for name in names):
        raise ValueError(f'{piece.id}: invalid score or staff identifier')
    duration(extraction['pickup_duration'], zero=True)
    duration(extraction['bar_duration'])
    if not 1 <= extraction['first_full_bar'] <= extraction['last_bar']:
        raise ValueError(f'{piece.id}: invalid measure numbering')
    previous, ids = 0, set()
    for segment in piece.segments:
        sid = segment['id']
        if not re.fullmatch(r'[0-9]{2}', sid) or sid in ids:
            raise ValueError(f'{piece.id}: invalid or duplicate segment ID: {sid}')
        ids.add(sid)
        first, last = segment['first_bar'], segment['last_bar']
        if first != previous + 1 or last < first:
            raise ValueError(f'{piece.id}/{sid}: segments must be contiguous and non-overlapping')
        previous = last
        key = segment['key']
        if not re.fullmatch(r'[a-g](?:is|es)*', key['pitch']) or key['mode'] not in ('major', 'minor'):
            raise ValueError(f'{piece.id}/{sid}: invalid starting key')
        if not 0 < segment.get('max_height', .74) <= .85:
            raise ValueError(f'{piece.id}/{sid}: invalid score height')
        if segment.get('lesson'):
            local_path(piece.folder, segment['lesson'])
    if previous != extraction['last_bar']:
        raise ValueError(f'{piece.id}: practice segments must cover through bar {extraction["last_bar"]}')

def load_project(root=ROOT, selected=None):
    root = Path(root).resolve()
    book = read_json(root / 'book.json')
    pieces, seen = [], set()
    for entry in book['pieces']:
        pid = entry['id']
        if not ID_PATTERN.fullmatch(pid) or pid in seen:
            raise ValueError(f'Invalid or duplicate collection piece ID: {pid}')
        seen.add(pid)
        if selected is not None and pid != selected:
            continue
        if selected is None and not entry.get('enabled', True):
            continue
        folder = root / 'pieces' / pid
        piece = Piece(root, folder, read_json(folder / 'piece.json'))
        validate_piece(piece)
        pieces.append(piece)
    if not pieces:
        raise ValueError(f'No enabled pieces found{": " + selected if selected else ""}')
    return book, pieces

def tex_escape(text):
    replacements = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$',
                    '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}',
                    '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(replacements.get(char, char) for char in str(text))

def range_text(piece, segment):
    first, last = segment['first_bar'], segment['last_bar']
    if first == 1 and duration(piece.data['extraction']['pickup_duration'], zero=True):
        return f'开头弱起至第 {last} 小节'
    return f'第 {first}--{last} 小节'
