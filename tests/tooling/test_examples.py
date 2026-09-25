"""Exercise the shipped examples with the actual IIgs interpreter."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(os.environ.get('TEST_LUA'), 'set TEST_LUA to run IIgs examples')
class ExamplePrograms(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / 'build/test-runs'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        for path in (ROOT / 'examples').glob('*.lua'):
            shutil.copyfile(path, self.work / path.name)

    def run_example(self, name, *args, stdin='', success=True):
        result = subprocess.run([os.environ.get('IIX', 'iix'), '--memcheck',
                                 str(Path(os.environ['TEST_LUA']).resolve()), '-E', name+'.lua', *args],
                                cwd=self.work, input=stdin.encode(), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=90)
        output = result.stdout.decode(errors='replace').replace('\r\n', '\n')
        self.assertNotIn('MemCheck:', output)
        self.assertNotRegex(output, r'\bBRK\b')
        if success:
            self.assertEqual(result.returncode, 0, output)
        else:
            self.assertNotEqual(result.returncode, 0, output)
        return output

    def test_greeting_and_warehouse(self):
        self.assertIn('Hello from Lua on the Apple IIgs!', self.run_example('hello'))
        self.assertIn('WAREHOUSE PASSED events=600 shipped=499 backorders=320 digest=32697 top=11',
                      self.run_example('warehouse'))

    def test_queens_known_counts_and_board(self):
        for n, expected in [(1,1), (2,0), (3,0), (4,2), (8,92)]:
            with self.subTest(n=n):
                out = self.run_example('queens', str(n))
                self.assertIn(f'Queens: n={n} solutions={expected}', out)
                board = [line.split() for line in out.splitlines() if re.fullmatch(r'[Q.]( [Q.])*',line)]
                if expected:
                    self.assertEqual(len(board), n)
                    cols = [row.index('Q') for row in board]
                    self.assertEqual(len(set(cols)), n)
                    self.assertEqual(len({i+c for i,c in enumerate(cols)}), n)
                    self.assertEqual(len({i-c for i,c in enumerate(cols)}), n)
                else:
                    self.assertEqual(board, [])
        for bad in ['0', '9', '2.5', 'invalid']:
            self.assertIn('Usage:',self.run_example('queens',bad,success=False))

    def test_life_glider_moves_one_cell_in_four_generations(self):
        out = self.run_example('life','4')
        blocks = re.findall(r'Generation \d+\n((?:[O.]{20}\n){10})Population: (\d+)',out)
        self.assertEqual(len(blocks),5)
        def cells(block):
            return {(x,y) for y,row in enumerate(block[0].splitlines()) for x,c in enumerate(row) if c=='O'}
        self.assertEqual(cells(blocks[-1]),{(x+1,y+1) for x,y in cells(blocks[0])})
        self.assertTrue(all(count=='5' for _,count in blocks))
        self.assertIn('Usage:',self.run_example('life','-1',success=False))

    def test_maze_is_connected_without_cycles_and_solution_reaches_exit(self):
        for seed in ['0','42','65535']:
            with self.subTest(seed=seed):
                out = self.run_example('maze',seed,'solve')
                grid = [line for line in out.splitlines() if line.startswith('#')]
                self.assertEqual(len(grid),17)
                self.assertTrue(all(len(row)==25 for row in grid))
                walkable = {(x,y) for y,row in enumerate(grid) for x,c in enumerate(row) if c!='#'}
                def neighbors(p):
                    x,y=p
                    return {(x-1,y),(x+1,y),(x,y-1),(x,y+1)}
                reached,queue = {(1,1)},[(1,1)]
                while queue:
                    for point in neighbors(queue.pop()) & walkable - reached:
                        reached.add(point); queue.append(point)
                self.assertEqual(reached,walkable)
                self.assertEqual(len(walkable),191)  # 96 cells and 95 connecting passages
                self.assertEqual(sum(len(neighbors(p)&walkable) for p in walkable)//2,len(walkable)-1)
                path = {(x,y) for x,y in walkable if grid[y][x] in '.SE'}
                ends = {(1,1),(23,15)}
                for point in path:
                    self.assertEqual(len(neighbors(point)&path),1 if point in ends else 2)
        self.assertIn('Usage:',self.run_example('maze','-1',success=False))

    def test_mandelbrot_has_bounded_symmetric_raster(self):
        out = self.run_example('mandel')
        lines = out.splitlines()
        start = lines.index('Mandelbrot: 39 x 16, 32 iterations')+1
        raster = lines[start:start+16]
        self.assertEqual(len(raster),16)
        self.assertTrue(all(len(line)==39 for line in raster))
        self.assertEqual(raster,raster[::-1])
        self.assertIn('@',''.join(raster))
        self.assertIn('Mandelbrot complete.',out)

    def test_word_counts_ties_empty_and_missing_file(self):
        (self.work/'sample.txt').write_text('Pear apple PEAR\n\nBanana apple!\n')
        out = self.run_example('words','sample.txt')
        self.assertIn('Words: 5 total, 3 distinct',out)
        self.assertLess(out.index('  apple'),out.index('  pear'))
        self.assertLess(out.index('  pear'),out.index('  banana'))
        (self.work/'empty.txt').write_text('')
        self.assertIn('Words: 0 total, 0 distinct',self.run_example('words','empty.txt'))
        self.run_example('words','missing.txt',success=False)
        self.assertIn('Words:',self.run_example('words'))

    def test_routes_and_coroutine_schedule(self):
        out = self.run_example('routes')
        self.assertIn('12  Depot > Mill > Orchard > Market > Harbor',out)
        out = self.run_example('workers')
        self.assertEqual(re.findall(r'Tick (\d+)',out),['0','1','2','3','4'])
        self.assertEqual(len(re.findall(r'(?:Loader|Printer|Backup) step \d',out)),9)
        self.assertIn('Workers complete: 3 jobs, 9 steps.',out)

    def test_adventure_wrong_actions_win_and_eof(self):
        out = self.run_example('adventure',stdin='use key\ntake key\nnorth\ntake key\nuse key\neast\nnorth\nuse key\n')
        for text in ['You need a key.','No key here.','Taken.','Nothing here needs unlocking.','Adventure complete.']:
            self.assertIn(text,out)
        self.assertIn('Goodbye.',self.run_example('adventure'))
        self.assertIn('Goodbye.',self.run_example('adventure',stdin='\nunknown\nquit\n'))

    def test_poker_all_categories_wheel_and_invalid_cards(self):
        out = self.run_example('poker')
        expected = ['straight flush','four of a kind','full house','flush','straight',
                    'three of a kind','two pair','pair','high card']
        self.assertEqual(re.findall(r' : ([a-z ]+)\n',out),expected)
        self.assertRegex(self.run_example('poker','AS','2D','3H','4C','5S'),r'(?m)^straight$')
        for cards in [('AS','AS','QH','JC','TS'),('AS','KD'),('XX','KD','QH','JC','TS')]:
            self.run_example('poker',*cards,success=False)

    def test_pager_handles_pages_blank_lines_quit_and_eof(self):
        self.assertIn('No file selected.',self.run_example('more'))
        (self.work/'page.txt').write_text('one\n\nthree\n')
        self.assertIn('one\n\nthree\nEnd of file.',self.run_example('more','page.txt'))
        (self.work/'long.txt').write_text(''.join(f'line {n}\n' for n in range(1,24)))
        for stdin in ['', 'q\n']:
            out = self.run_example('more','long.txt',stdin=stdin)
            self.assertIn('Pager closed.',out)
            self.assertNotIn('line 21',out)
        self.assertIn('line 23',self.run_example('more','long.txt',stdin='\n'))
        self.run_example('more','missing.txt',success=False)

    def test_blackjack_quit_invalid_commands_and_repeatable_shuffle(self):
        out = self.run_example('blackjack',stdin='invalid\ns\nn\n')
        self.assertIn('Please enter h, s, or q.',out)
        self.assertIn('Thanks for playing Blackjack!',out)
        self.assertEqual(re.search(r'Score: .+',out)[0],re.search(r'Score: .+',self.run_example('blackjack',stdin='s\nn\n'))[0])
        self.assertIn('Score: 0 wins, 0 losses, 0 pushes',self.run_example('blackjack'))
        self.run_example('blackjack','65536',success=False)

    def test_blackjack_naturals_pushes_and_multiple_aces(self):
        for seed, score in [('4','0 wins, 1 losses, 0 pushes'),
                            ('7','1 wins, 0 losses, 0 pushes'),
                            ('1259','0 wins, 0 losses, 1 pushes')]:
            with self.subTest(seed=seed):
                self.assertIn('Score: '+score,self.run_example('blackjack',seed,stdin='n\n'))
        self.assertIn('Push: a tie.',self.run_example('blackjack','19',stdin='s\nn\n'))
        out = self.run_example('blackjack','727',stdin='h\ns\nn\n')
        self.assertRegex(out,r'You: A[CDHS] A[CDHS] (?:10|[JQK])[CDHS] = 12')


if __name__ == '__main__':
    unittest.main()
