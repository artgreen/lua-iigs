# Lua examples for the IIgs

Thirteen standalone programs, from a one-line greeting to games, text graphics,
file tools, and a coroutine simulation. They use the standard libraries included
in this port: no modules to install, terminal escape codes, or graphics toolbox.
Every top-level `.lua` file here is included in the standard `LUA.SHK` / `lua.po`
distribution. The compact package includes only `hello.lua`.

Run commands below from the installed directory. From the source checkout,
use the script path `examples/name.lua` instead of `name.lua`.

| Program | Try it | What it demonstrates |
| --- | --- | --- |
| [hello.lua](hello.lua) | `lua -E hello.lua` | First-run greeting |
| [adventure.lua](adventure.lua) | `lua -E adventure.lua` | Explore an island, find a key, light a beacon; tables and command dispatch |
| [blackjack.lua](blackjack.lua) | `lua -E blackjack.lua 42` | Hit/stand card game; deck shuffling, multiple aces, natural blackjacks, ties |
| [poker.lua](poker.lua) | `lua -E poker.lua AS 2D 3H 4C 5S` | Classify five cards; counting, sorting, pattern validation |
| [life.lua](life.lua) | `lua -E life.lua 6` | Conway's Life with a glider; two buffers and neighborhood rules |
| [maze.lua](maze.lua) | `lua -E maze.lua 42 solve` | Generate a maze and draw its route; iterative depth-first search |
| [mandel.lua](mandel.lua) | `lua -E mandel.lua` | A 39-column Mandelbrot postcard; floating-point arithmetic |
| [queens.lua](queens.lua) | `lua -E queens.lua 8` | Count all 92 eight-queens solutions; bounded recursive backtracking |
| [routes.lua](routes.lua) | `lua -E routes.lua` | Find delivery routes between seven stations with Dijkstra's algorithm |
| [workers.lua](workers.lua) | `lua -E workers.lua` | Schedule three coroutines using virtual time |
| [words.lua](words.lua) | `lua -E words.lua myfile.txt` | Count words in a file, rank the top twelve, break ties alphabetically |
| [more.lua](more.lua) | `lua -E more.lua myfile.txt` | Read a file a page at a time without loading the whole file |
| [warehouse.lua](warehouse.lua) | `lua -E warehouse.lua` | Three coroutine producers, 600 transactions, audit replay, and stock accounting |

## Games and input

Blackjack uses `h` to hit, `s` to stand, and `q` to quit. The dealer stands on
soft 17. A two-card 21 beats a longer 21; matching hands push. This is a simple
no-betting game without splits, doubling, or insurance. Blackjack and the maze
use an optional integer seed from 0 to 65535 (default 42), so a session can be
repeated. Their small deterministic generators are for demonstrations.

Poker accepts five distinct two-character cards, separated by spaces: ranks
`2` through `9`, `T`, `J`, `Q`, `K`, `A`, and suits `C`, `D`, `H`, `S`.
With no cards supplied it shows all nine hand categories. It classifies hands;
it does not rank two hands within the same category.

The adventure explains its commands when it starts. `quit` or end-of-input
leaves cleanly. The pager displays 20 lines before prompting: Enter continues,
`q` or end-of-input closes it. With no filename it prompts for one. Quitting
does not modify the file. All examples leave the user's files unchanged.

## Demos and limits

Life prints generations 0 through the requested generation (default 6,
range 0..100). The 20-by-10 board has empty boundaries rather than wrapping.
It scrolls snapshots instead of assuming screen-control sequences or a timer.
A dot on standard error marks each newly computed generation.

The maze is 12 by 8 cells, rendered in 25 columns. Omit `solve` to hide its
solution. Each maze has exactly one path between any two cells.
N-queens accepts board sizes 1..8 and shows the first solution, if one exists.
The workers use virtual ticks, so they do not actually sleep or create threads.

Word counts recognize ASCII letters, ignore punctuation, and count uppercase
and lowercase together. The vocabulary is limited to 512 distinct words;
choose modest text files with reasonably short lines for the IIgs. Without a
filename, it counts a built-in sample. It reads line by line, as does the pager.

Warehouse prints progress every 100 records and ends with:

```text
WAREHOUSE PASSED events=600 shipped=499 backorders=320 digest=32697 top=11
```

To try a demo with the compact interpreter, use the matching IIgs compiler:

```text
luac -o queens.luo queens.lua
luasmall -E queens.luo 8
```

Copy the example source from the standard distribution or source ZIP first.
Compile on the IIgs for its native floating-point behavior. Mandelbrot shading
can vary slightly between GoldenGate and hardware; exact raster equality
across platforms is not promised.

## Checks and embedding

`make test` includes example checks when it runs the tooling group with the
built interpreter. They check known queens counts, glider movement, maze
connectivity and solution paths, card rules, file handling, the adventure's
winning path, and clean exits. These are GoldenGate checks, not new hardware
acceptance claims. See the [validation guide](../docs/VALIDATION.md).

`embedding/` is a separate C example: host (`test.c`), bindings (`testiface.c`),
collection implementation (`testbridge.c`), header, and `bridge.lua`.
Build it with `make bridge`, then run with your SDK path exported for `iix`:

```sh
export GOLDEN_GATE=/absolute/path/to/orca-sdk-2.2.1
iix --memcheck build/dev/lua/out/bridge examples/embedding/bridge.lua
```

See [embedding](../docs/EMBEDDING.md) for initialization and link requirements.
The collection example leaves index, allocation-failure, and use-after-free
validation to the caller; it demonstrates registration, not a production API.
