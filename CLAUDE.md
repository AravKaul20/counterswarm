# Counter-Swarm

3D counter-drone swarm simulation. Python simulation core in `sim/`, scripts at
the repo root, Three.js viewer in `viewer/`, LaTeX paper in `paper/`.

- Changes go through the developer/critic loop in `docs/review-loop.md`, using
  the agents in `.claude/agents/`.
- Before claiming anything works: `python -m pytest -q` and
  `python run_sanity.py`.
- Any change that can alter simulation output means re-running the full
  pipeline and updating every number in `README.md` and `paper/paper.tex`
  from the `make_plots.py` printout.
- No emoji in code, docs, or commit messages.
