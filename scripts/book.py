"""Generate the collection contents and compile either a book or one piece."""
import os
import shutil
import subprocess
from .project import local_path, range_text, tex_escape, write_text

def prepare_book(root, book, pieces, target):
    generated = root / 'build/generated' / target
    metadata = '\n'.join('\\newcommand{\\' + name + '}{' + tex_escape(value) + '}'
                         for name, value in [('BookTitle', book['title']), ('BookSubtitle', book['subtitle']),
                                             ('BookAuthor', book['author']), ('BookYear', book['year'])])
    write_text(generated / 'metadata.tex', '% Generated from book.json.\n' + metadata + '\n')
    lines = ['% Generated from book.json and pieces/*/piece.json.']
    for piece in pieces:
        data = piece.data
        lines += [r'\chapter{' + tex_escape(data['title']) + '}', r'\label{piece:' + piece.id + '}']
        if data.get('composer'):
            lines.append(r'\noindent\textbf{作曲：}' + tex_escape(data['composer']) + r'\par')
        if data.get('description'):
            lines.append(r'\noindent ' + tex_escape(data['description']) + r'\par')
        lines += [r'\section{完整乐谱}', r'\FullScore{' + piece.source.as_posix() + '}']
        if not piece.segments:
            continue
        lines += [r'\clearpage', r'\section{分段练习}']
        if data.get('overview'):
            lines.append(r'\input{' + local_path(piece.folder, data['overview']).as_posix() + '}')
        lines.append(r'\input{\ProjectRoot tex/note-name-guide.tex}')
        lines += [r'\begin{center}\begin{tabular}{cll}', r'\toprule 段落 & 小节范围 & 内容 \\ \midrule']
        for number, segment in enumerate(piece.segments, 1):
            lines.append(f'{number} & {range_text(piece, segment)} & {tex_escape(segment["title"])}' + r' \\')
        lines += [r'\bottomrule\end{tabular}\end{center}']
        for number, segment in enumerate(piece.segments, 1):
            lines += [r'\clearpage', r'\subsection{第 ' + str(number) + ' 段：' + tex_escape(segment['title']) + '}',
                      r'\label{practice:' + piece.id + ':' + segment['id'] + '}',
                      r'\def\CurrentSegmentRange{' + range_text(piece, segment) + '}',
                      r'\def\SegmentMaxHeight{' + str(segment.get('max_height', .74)) + '}',
                      r'\def\SegmentPDF{' + (piece.output / f'part-{segment["id"]}.cropped.pdf').as_posix() + '}']
            if segment.get('lesson'):
                lines.append(r'\input{' + local_path(piece.folder, segment['lesson']).as_posix() + '}')
            else:
                lines += [r'\noindent\textbf{范围：\CurrentSegmentRange。}', r'\SegmentScore']
    write_text(generated / 'catalog.tex', '\n'.join(lines) + '\n')

def compile_book(root, target):
    work = root / 'build/latex' / target
    work.mkdir(parents=True, exist_ok=True)
    cache = root / 'build/cache/tex'
    # lyluatex cannot reliably create an absolute Windows cache path itself.
    # Create every required directory before invoking either TeX or LilyPond.
    for name in ('tex', 'graphics', 'lyluatex'):
        (root / 'build/cache' / name).mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['TEXMFVAR'] = env['TEXMFCACHE'] = str(cache)
    for number in (1, 2):
        log_path = work / f'pass-{number}.log'
        print(f'Building {target}: LaTeX pass {number}', flush=True)
        with log_path.open('w', encoding='utf-8') as log:
            result = subprocess.run(['lualatex', '--shell-escape', '-interaction=nonstopmode',
                                     '-halt-on-error', '-synctex=0', f'-jobname={target}',
                                     r'\def\ProjectRoot{' + root.as_posix() + r'/}\def\BuildTarget{'
                                     + target + r'}\input{' + (root / 'main.tex').as_posix() + '}'],
                                    cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError(f'LaTeX failed; see {log_path}')
    destination = root / 'output' / ('book.pdf' if target == 'book' else f'pieces/{target.removeprefix("piece-")}.pdf')
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(work / f'{target}.pdf', destination)
    print(f'PDF: {destination}', flush=True)
    return destination
