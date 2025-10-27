## tmux-oil

Delete, reorder, rename, and create tmux windows quickly using your editor. tmux-oil reads your current session state, opens a temporary buffer in $VISUAL/$EDITOR, and then applies the changes.

This project is inspired by the excellent Oil file manager for Neovim.

- oil.nvim: https://github.com/stevearc/oil.nvim

The name “tmux-oil” nods to that workflow of editing a structured view directly in your editor.

---

## What it does

- Opens your tmux session’s windows as editable text: one line per window.
- Lets you reorder windows by reordering lines.
- Rename windows by editing the text after the colon.
- Create new windows with a special placeholder.
- Delete windows by removing their line.

---

## Requirements

- tmux installed and a running tmux server
- An existing tmux session to operate on
- Linux/macOS shell environment
- Python 3.13+ (likely will work from 3.10 >=, but did not check)
- Python dependencies: libtmux (installed automatically if using uv or pip)

Optional for building a single-file binary:

- Nuitka (dev dependency)

---

## Installation

You can run the script directly with Python, or build a static-ish binary with Nuitka.

### Option A: Get the prebuilt binary

Just download the latest release, make the file executable, and then you can use it.

### Option B: install using pipx, uvx, or tmp

TBD


### Option C: For development run from source

Using uv (recommended):

```sh
# Ensure you have uv installed: https://docs.astral.sh/uv/
uv sync

# Run the tool
uv run python main.py <session-name>
```

Using pip:

```sh
python -m venv .venv
source .venv/bin/activate
pip install libtmux
python main.py <session-name>
```

### Option D: Build a single-file binary

We ship a tiny helper to build with Nuitka.

```sh
# Install dev dependency
uv run uv pip install nuitka  # or: pip install nuitka

# Build via project script (pyproject [project.scripts])
uv run python -m tools.build_binary

# Or call the entry script name if exposed by your launcher
uv run build-binary
```

Output binary will be placed at `dist/bin/tmux-oil`.

#TODO(Kristofy) Add a prebuilt release artifact link once CI is set up.

---

## Usage

1) Make sure you have a tmux session:

```sh
tmux ls
```

2) Run tmux-oil with the session name (or id):

```sh
# Uses $VISUAL or $EDITOR. Defaults to `vi` if neither is set.
python main.py <session-name-or-id>
```

3) Your editor opens with content like:

```
# Edit windows for session. Format: N: Title
# Use _: Title to create new windows. Comments (#) and blank lines are ignored.

0: editor
1: server
2: logs
```

4) Make your changes, save, and exit the editor. tmux-oil will compute a plan and apply it.

### Edit language (what you can change)

- Reorder windows: reorder the lines.
- Rename a window: change the text after the colon.
- Delete a window: delete its line.
- Create a new window: add a line starting with `_:`, for example: `_: scratch`.

Constraints and validations:

- Indices must be numbers except `_` which signals a new window.
- You cannot reference an index that didn’t exist in the original list (to create, use `_:`).
- Duplicate indices are not allowed.
- An empty plan (no lines) is currently not supported and will error instead of deleting the session.

Error messages are explicit (e.g., “Index: 3 appeared twice”). Fix the line(s) and re-run.

---

## Examples

Rename and reorder:

Before:

```
0: editor
1: server
2: logs
```

After you edit and save:

```
1: api
0: editor
2: logs
_: scratch
```

Result:

- Window 1 renamed to `api`
- Windows reordered to `[1, 0, 2]`
- New window `scratch` created and placed at the appropriate index

#TODO(Kristofy) Insert a short screencast GIF of this flow.

---

## Run inside tmux (popup + keybind)

You can invoke tmux-oil inside a tmux popup for a smooth, built-in UI.

If you have the single-file binary available:

```tmux
# Popup 90% width/height, with a title
display-popup -w 90% -h 90% -T "Tmux oil" -E '/path/to/tmux-oil #S'

# Keybinding example: Meta + -
bind M-- display-popup -w 90% -h 90% -T "Tmux oil" -E '/path/to/tmux-oil #S'
```

If running from source (Python script), swap the command:

```tmux
display-popup -w 90% -h 90% -T "Tmux oil" -E 'python /path/to/main.py #S'
bind M-- display-popup -w 90% -h 90% -T "Tmux oil" -E 'python /path/to/main.py #S'
```

Notes:

- `#S` expands to the current session name. You can also pass a literal session name.
- Replace `/path/to/...` with your actual binary or script path.
- The `-E` flag makes tmux execute the given string in a shell.
- If you add `tmux-oil` to your PATH, you can simplify to `-E 'tmux-oil #S'`.  
	#TODO(Kristofy) Provide a console script entrypoint so `tmux-oil` is installed as a command.

---

## Environment variables

- VISUAL / EDITOR: editor command used to open the temporary file. Defaults to `vi`.

---

## Build details

We use Nuitka to build a single-file binary for convenient distribution:

- One-file mode
- Output at `dist/bin/tmux-oil`
- Removes previous output before building

To build locally:

```sh
uv run python -m tools.build_binary
# or
python -m tools.build_binary
```

#TODO(Kristofy) Add CI workflow to build and upload release binaries.

---

## Troubleshooting

- “Found no sessions…”: Start tmux or create a session first (`tmux new -s mysession`).
- Editor didn’t open: Ensure `$VISUAL` or `$EDITOR` is set, or that `vi` is available.
- Plan rejected (runtime error): Check the edit rules and the error message; fix the offending line.
- libtmux connectivity: Ensure you’re running inside a user environment that can reach the tmux server.

Edge cases handled by tmux-oil:

- Non-numeric indices are rejected unless `_` for creation.
- Duplicate indices are rejected.
- Attempting to reference a non-existent existing index is rejected.

Known limitation:

- Deleting the entire session (by emptying the file) is not supported yet.

#TODO(Kristofy) Decide on behavior for “delete entire session” (confirm prompt + session kill?).

---

## How it works

At a high level:

1) Read current windows for the tmux session via libtmux.
2) Open a temp file in your editor seeded with the current state.
3) Parse the edited buffer into a target state with validation.
4) Compute an execution plan with these steps:
	- Delete windows not present anymore
	- Rename windows whose names changed
	- Reorder windows by issuing `swap-window` operations
	- Create new windows for each `_:` entry and place them
5) Apply the plan sequentially to the tmux server.

Notes:

- If you make no changes, nothing is applied.
- If your editor exits with a failure code, no changes are applied.
- Reordering uses repeated swaps; large moves will “walk” the window through indices.

---

## Compatibility and assumptions

- Assumes tmux allows reordering windows. Internally this tool uses `swap-window` to move windows.  
	If your setup restricts reordering, behavior is undefined.
- The tmux option `renumber-windows` may influence indices during deletes; the planner accounts for deletions first, then moves.  
	#TODO(Kristofy) Verify behavior with both `set -g renumber-windows on` and `off`.
- Some tmux options (e.g., aggressive resize, hooks) might affect window state while applying changes.  
	#TODO(Kristofy) List specific tmux options that could interfere.

---

## Performance and roadmap

Current implementation reorders using adjacent swaps, which can take O(n^2) swaps in the worst case.  
Potential optimizations:

- Compute a minimal move plan and use direct `move-window` operations when safe.
- Create all new windows first, then perform a single pass of moves for O(n) placements.
- Only swap/move windows that are out of place.

#TODO(Kristofy) Evaluate reliability of libtmux `move_window` across tmux versions and replace adjacent-swap strategy where possible.
#TODO(Kristofy) Implement an O(n) reorder step post-creation.

#IMPORTANT
#TODO(Kristofy) Libtmux is cool, but not really needed, I could implement the few methods I'm using myself, and I would have a single python file that could also be shipped directly
- This will be my immediate goal


---

## Development

Project layout:

- `main.py` – CLI entry point and tmux planning/execution logic.
- `tools/build_binary.py` – Build helper using Nuitka.
- `pyproject.toml` – Project metadata and dev dependencies.

Run locally:

```sh
uv sync
uv run python main.py <session-name>
```

Style and testing:

#TODO(Kristofy) Choose and add a linter/formatter (ruff/black) and minimal tests.
#TODO(Kristofy) Add a --dry-run flag to preview the plan without applying changes.
#TODO(Kristofy) Add confirmation for delete operations

---


## Disclaimer

This is primarily for personal use. Use it with care and at your own risk.  
No warranty is provided; the author assumes no responsibility for any side effects or data loss caused by using this tool.


## Maintainer checklist

- [ ] Write a short project description (README top).  #TODO(Kristofy)
- [ ] Add a demo GIF and screenshots.  #TODO(Kristofy)
- [ ] Publish prebuilt binaries (GitHub Releases).  #TODO(Kristofy)
- [ ] Add CI to build/test on push.  #TODO(Kristofy)
- [ ] Package and publish to PyPI (optional).  #TODO(Kristofy)
- [ ] Add a simple `tmux-oil` console script entrypoint.  #TODO(Kristofy)
- [ ] Document Windows support status (likely unsupported).  #TODO(Kristofy)

---

## License

#TODO(Kristofy) Add license (e.g., MIT) and file.

