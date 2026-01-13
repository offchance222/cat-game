# Space Dodger — Pygame port with shooting and patterned enemies

What this is
- A Pygame port of the Space Dodger browser game.
- Player can move left/right and shoot.
- Enemies spawn and move in three patterns:
  - Straight downward
  - Sine-wave horizontal oscillation
  - Zig-zag switching horizontal direction at intervals
- Score for destroying enemies; game difficulty increases over time.
- Restart after game over by pressing R or clicking the restart button.

Requirements
- Python 3.8+
- Pygame (install with `pip install -r requirements.txt`)

Files
- `game.py` — main Pygame game file

How to run
1. Save `game.py` and `requirements.txt` in a folder.
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run:
   ```
   python game.py
   ```

Controls
- Left / A: move left
- Right / D: move right
- Space: shoot
- R: restart after game over
- Esc / window close: quit

Ideas to extend
- Add enemy bullets and patterns that shoot
- Add power-ups (spread shot, rapid fire, shields)
- Add sound effects and music (I can add simple data-URI wave sounds or instructions for asset files)
- Use sprite images instead of shapes and add particle explosions

If you want, I can now:
- Add enemy shooting patterns and different enemy types (boss),
- Add local high-score persistence,
- Add simple sound effects and background music.
