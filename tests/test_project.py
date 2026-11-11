"""Regression checks for multi-piece configuration and excerpt generation."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from scripts.book import compile_book, prepare_book
from scripts.build import new_piece
from scripts.practice import excerpt_length, generate, engrave
from scripts.project import ROOT, Piece, load_project, local_path, tex_escape, validate_piece, write_text

SOURCE = r'''
\version "2.26.0"
tune = \relative g' {
  g1 | % 1
  a1 | % 2
  b1 | % 3
  c1 | % 4
}
bass = { c1*4 }
upper = { s1*4 }
lower = { s1*4 }
ensemble = << \new Staff = "treble" \tune \new Staff = "bassStaff" \bass >>
\score { \ensemble }
'''

class ProjectTests(unittest.TestCase):
    def setUp(self):
        sandbox = (ROOT / 'build/test-runs').resolve()
        sandbox.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=sandbox)
        self.root = Path(self.temp.name).resolve()
        assert self.root.is_relative_to(sandbox)
        self.addCleanup(self.temp.cleanup)

    def make_piece(self, pid='first-piece'):
        folder = self.root / 'pieces' / pid
        write_text(folder / 'source/score.ly', SOURCE)
        data = {'id': pid, 'title': '曲目 & 标题', 'source': 'source/score.ly',
                'extraction': {'strategy': 'bar-comments', 'pickup_duration': '0',
                               'first_full_bar': 1, 'bar_duration': '1', 'last_bar': 4,
                               'score_variable': 'ensemble',
                               'staves': {'upper': 'treble', 'lower': 'bassStaff'},
                               'voices': {'primary': 'tune', 'accompaniment': 'bass',
                                          'upper_support': 'upper', 'lower_support': 'lower'}},
                'segments': [{'id': '01', 'title': '前段', 'first_bar': 1, 'last_bar': 2,
                              'key': {'pitch': 'd', 'mode': 'major'}},
                             {'id': '02', 'title': '后段', 'first_bar': 3, 'last_bar': 4,
                              'key': {'pitch': 'd', 'mode': 'major'}}]}
        write_text(folder / 'piece.json', json.dumps(data))
        return Piece(self.root, folder, data)

    def make_book(self, ids):
        book = {'title': '练习曲集', 'subtitle': '笔记', 'author': '作者', 'year': '2026',
                'pieces': [{'id': pid, 'enabled': enabled} for pid, enabled in ids]}
        write_text(self.root / 'book.json', json.dumps(book))
        return book

    def test_current_piece_keeps_ten_segments_and_pickup_length(self):
        _, pieces = load_project(ROOT)
        self.assertEqual(len(pieces[0].segments), 10)
        self.assertEqual(excerpt_length(pieces[0].data['extraction'], 9), Fraction(25, 4))

    def test_different_meter_key_voice_and_staff_names_are_not_hardcoded(self):
        piece = self.make_piece()
        validate_piece(piece)
        jobs = generate(piece)
        text = jobs[1][1].read_text(encoding='utf-8')
        self.assertIn('showFirstLength = s1*4/1', text)
        self.assertIn(r'\key d \major', text)
        self.assertIn(r'\context Staff = "treble"', text)
        self.assertIn("\\removeWithTag #'midiOnly \\ensemble", text)
        self.assertIn(r'\ensemble', text)
        self.assertNotIn(r'\pianoMusic', text)

    def test_overlapping_or_incomplete_segments_fail(self):
        piece = self.make_piece()
        piece.data['segments'][1]['first_bar'] = 2
        with self.assertRaisesRegex(ValueError, 'contiguous'):
            validate_piece(piece)
        piece.data['segments'][1]['first_bar'] = 3
        piece.data['segments'][1]['last_bar'] = 3
        with self.assertRaisesRegex(ValueError, 'cover through'):
            validate_piece(piece)

    def test_source_cannot_escape_its_piece(self):
        with self.assertRaises(ValueError):
            local_path(self.root, '../outside.ly', required=False)

    def test_collection_order_disabled_entries_and_single_piece_selection(self):
        self.make_piece('first-piece')
        self.make_piece('second-piece')
        self.make_book([('second-piece', True), ('first-piece', False)])
        _, active = load_project(self.root)
        self.assertEqual([p.id for p in active], ['second-piece'])
        _, selected = load_project(self.root, 'first-piece')
        self.assertEqual([p.id for p in selected], ['first-piece'])

    def test_catalog_groups_each_piece_and_uses_distinct_asset_paths(self):
        first, second = self.make_piece(), self.make_piece('second-piece')
        book = self.make_book([(first.id, True), (second.id, True)])
        prepare_book(self.root, book, [second, first], 'book')
        catalog = (self.root / 'build/generated/book/catalog.tex').read_text(encoding='utf-8')
        self.assertLess(catalog.index('piece:second-piece'), catalog.index('piece:first-piece'))
        self.assertIn('build/scores/second-piece/part-01.cropped.pdf', catalog)
        self.assertIn('build/scores/first-piece/part-01.cropped.pdf', catalog)
        self.assertIn(r'曲目 \& 标题', catalog)

    def test_new_piece_starts_disabled_with_editable_source_and_notes(self):
        self.make_book([])
        shutil.copytree(ROOT / 'templates', self.root / 'templates')
        new_piece(self.root, 'next-piece', '下一首', '作曲者')
        book = json.loads((self.root / 'book.json').read_text(encoding='utf-8'))
        self.assertFalse(book['pieces'][0]['enabled'])
        _, pieces = load_project(self.root, 'next-piece')
        self.assertEqual(pieces[0].data['title'], '下一首')
        self.assertTrue(pieces[0].source.is_file())
        self.assertTrue((pieces[0].folder / 'study/segments/01.tex').is_file())

    def test_failed_engraving_does_not_mark_old_output_as_current(self):
        piece = self.make_piece()
        write_text(self.root / 'lilypond/note-names.ily', '% helper')
        job = generate(piece)[0]
        write_text(job[1].with_suffix('.cropped.pdf'), 'old output')
        with patch('scripts.practice.subprocess.run') as run:
            run.return_value.returncode = 1
            with self.assertRaisesRegex(RuntimeError, 'LilyPond failed'):
                engrave(job)
        self.assertFalse(job[1].with_suffix('.stamp.json').exists())

    def test_tex_metadata_escaping(self):
        self.assertEqual(tex_escape('A&B_1%'), r'A\&B\_1\%')

    def test_first_build_creates_all_cache_directories_before_latex(self):
        for target in ('book', 'piece-first-piece'):
            with self.subTest(target=target):
                root = self.root / target
                self.assertFalse((root / 'build').exists())

                def fake_latex(command, **kwargs):
                    for name in ('tex', 'graphics', 'lyluatex'):
                        self.assertTrue((root / 'build/cache' / name).is_dir())
                    work = root / 'build/latex' / target
                    self.assertEqual(kwargs['cwd'], work)
                    (work / f'{target}.pdf').write_bytes(b'%PDF-test')
                    return type('Result', (), {'returncode': 0})()

                with patch('scripts.book.subprocess.run', side_effect=fake_latex) as run:
                    output = compile_book(root, target)
                self.assertEqual(run.call_count, 2)
                self.assertEqual(output.read_bytes(), b'%PDF-test')

if __name__ == '__main__':
    unittest.main()
