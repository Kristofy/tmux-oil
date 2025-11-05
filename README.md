## tmux-oil

Delete, reorder, rename, and create tmux windows quickly using your editor. tmux-oil reads your current session state, opens a temporary buffer in $EDITOR, and then applies the changes.

This project is inspired by the excellent Oil file manager for Neovim.

- oil.nvim: https://github.com/stevearc/oil.nvim

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
- Python 3.13+ (likely will work from 3.10 >=, but did not check)

## Installation

Copy the tmux-oil file to your computer, and use it, alternatively:
```
wget https://raw.githubusercontent.com/Kristofy/tmux-oil/refs/heads/main/tmux-oil
```

## Usage

1) Make sure you have a tmux session:

```sh
tmux ls
```

2) Run tmux-oil with the session name (or id):

```sh
# Uses $EDITOR. Defaults to `vi` if not set.
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
tmux display-popup -w 90% -h 90% -T "Tmux oil" -E '/path/to/tmux-oil <your session id>'

# Keybinding example: Meta + -
bind M-- display-popup -w 90% -h 90% -T "Tmux oil" -E '/path/to/tmux-oil #S'
```

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


