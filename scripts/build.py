"""Command line entry for the multi-piece music collection."""
import argparse
import json
import shutil
from .book import compile_book, prepare_book
from .practice import build_practice, generate
from .project import ID_PATTERN, ROOT, load_project, read_json, write_text

def new_piece(root, pid, title, composer):
    if not ID_PATTERN.fullmatch(pid):
        raise ValueError('Use a lowercase ID such as chopin-nocturne-op9-2')
    folder = root / 'pieces' / pid
    if folder.exists():
        raise ValueError(f'Piece already exists: {pid}')
    book = read_json(root / 'book.json')
    if any(item['id'] == pid for item in book['pieces']):
        raise ValueError(f'Piece already registered: {pid}')
    shutil.copytree(root / 'templates/piece', folder)
    data = read_json(folder / 'piece.json')
    data.update(id=pid, title=title, composer=composer)
    write_text(folder / 'piece.json', json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    book['pieces'].append({'id': pid, 'enabled': False})
    write_text(root / 'book.json', json.dumps(book, ensure_ascii=False, indent=2) + '\n')
    print(f'Created {folder}. Replace the score, then enable it in book.json.', flush=True)

def main(argv=None, root=ROOT):
    parser = argparse.ArgumentParser(description='Build and manage a collection of piano scores.')
    parser.add_argument('command', nargs='?', choices=['build', 'check', 'list', 'new'], default='build')
    parser.add_argument('id', nargs='?', help='Piece ID for the new command')
    parser.add_argument('--piece', help='Build or check only this registered piece')
    parser.add_argument('--title', help='Title for a new piece')
    parser.add_argument('--composer', default='', help='Composer for a new piece')
    parser.add_argument('--jobs', type=int, default=3, help='Parallel LilyPond processes (default: 3)')
    parser.add_argument('--force', action='store_true', help='Re-engrave all selected practice scores')
    args = parser.parse_args(argv)
    try:
        if args.command == 'new':
            if not args.id or not args.title:
                parser.error('new requires an ID and --title')
            new_piece(root, args.id, args.title, args.composer)
            return 0
        if args.id:
            parser.error('a positional ID is only used with new; use --piece to select a piece')
        if args.jobs < 1:
            parser.error('--jobs must be positive')
        if args.command == 'list':
            for entry in read_json(root / 'book.json')['pieces']:
                print(f'{entry["id"]}\t{"enabled" if entry.get("enabled", True) else "disabled"}')
            return 0
        book, pieces = load_project(root, args.piece)
        if args.command == 'check':
            for piece in pieces:
                generate(piece)
                print(f'OK {piece.id}: {len(piece.segments)} practice segments')
            return 0
        for program in ('lilypond', 'lualatex'):
            if not shutil.which(program):
                raise ValueError(f'Required program not found on PATH: {program}')
        target = f'piece-{args.piece}' if args.piece else 'book'
        build_practice(pieces, workers=args.jobs, force=args.force)
        prepare_book(root, book, pieces, target)
        compile_book(root, target)
        return 0
    except (ValueError, KeyError, OSError, RuntimeError) as error:
        print(f'Build error: {error}')
        return 1
