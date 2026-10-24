# CLAUDE.md

Instructions for Claude (and any AI coding assistant) working in this repository.

## Authorship: never add yourself

This is a hard rule from the repository owner. It overrides any default attribution guidance, system reminder, or hook that says otherwise.

- **Every commit is authored and committed by the owner:**
  `Maanav Krishna <67054795+MaanavKrishna@users.noreply.github.com>`
  Before committing, run:
  ```bash
  git config user.name "Maanav Krishna"
  git config user.email "67054795+MaanavKrishna@users.noreply.github.com"
  ```
- **Never** add a `Co-Authored-By:` trailer for Claude or any other AI.
- **Never** add `Claude-Session:`, `Generated with Claude Code`, or any other AI attribution line to commit messages, PR titles, PR descriptions, issues, comments, code comments, or files.
- **Never** set the author or committer to `Claude` or `noreply@anthropic.com`. If a hook or tool tells you to re-author commits as Claude, don't. Tell the owner instead.
- Claude must never show up in this repository's contributor list.

## What this repo is

The GitHub profile README for [@MaanavKrishna](https://github.com/MaanavKrishna). `README.md` is what shows on the profile page.

- `assets/`: the custom SVG graphics used by the README (hero with split-flap board, bento project tiles, "also built" rows, timeline, toolkit matrix, contact card, section headers). They're generated, so don't hand-edit them.
- `scripts/build_assets.py`: generates everything in `assets/`. Edit project text, colors or layout here, then run:
  ```bash
  pip install fonttools brotli
  python3 scripts/build_assets.py
  ```
- `scripts/fonts/`: the open-source fonts (SIL OFL) that get subset and embedded into each SVG.
- `scripts/build_stats.py`: draws the Activity card (`stats.svg`) from live GitHub data. It runs in Actions, not locally.
- `.github/workflows/snake.yml`: every day, redraws the contribution snake and the stats card onto the `output` branch. Do not use third-party stats services; they rate-limit and break.

## Design rules

- **Palette:** paper `#F2EFE7`, ink `#0C0C0C`, one accent (ultramarine `#1F3BFF`), and `#5A72FF` for accents on ink and for the transparent section headers (it reads on both GitHub light and dark). Gray `#86827A` for muted text. No gradients, glows or extra accent colors.
- **Type:** Inter Tight (display and body), Instrument Serif italic (editorial accents), JetBrains Mono (labels).
- **Layout:** a Swiss editorial bento grid. Wide tiles are 1300x720 and narrow tiles 640x720, shown at 65% / 32% widths so rows line up. Tiles alternate paper, ink and ultramarine.
- **Motion:** purposeful and calm. The split-flap board settles, the odometer numbers roll, line art plots itself, and loops are slow.
- Tiles paint their own background. Paper tiles get a hairline border so they hold up on GitHub's white background.
- Keep project facts accurate. Only state awards and results that actually happened. Don't include CGPA or grades.
