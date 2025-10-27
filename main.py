import argparse
from dataclasses import dataclass
import libtmux

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


def edit_text(
    content: str = "",
    suffix: str = ".txt",
) -> Optional[str]:
    # Get the editor command
    editor = os.environ.get('VISUAL') or os.environ.get('EDITOR') or 'vi'

    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w+', suffix=suffix, delete=False, encoding='utf-8') as tf:
        temp_path = Path(tf.name)
        tf.write(content)
        tf.flush()

    try:
        # Open the editor
        subprocess.run([editor, str(temp_path)], check=True)
        # Read the edited content
        edited_content = temp_path.read_text(encoding='utf-8')
        # Return None if file wasn't modified or is empty
        return edited_content
    except subprocess.CalledProcessError:
        # Editor exited with an error
        return None
    finally:
        # Clean up the temporary file
        temp_path.unlink(missing_ok=True)

@dataclass
class TmuxWindow:
    win: libtmux.Window
    id: str
    index: int
    name: str

    @classmethod
    def from_window(cls, win: libtmux.Window) -> 'TmuxWindow':
        if win.id is None:
            raise RuntimeError("Found None id, aborting")

        if win.index is None:
            raise RuntimeError("Index is None, aborting")

        if not win.index.isdigit():
            raise RuntimeError(f"Found index, that is not a number {win.index}")

        return cls(win, win.id, int(win.index), win.name or "")

@dataclass
class CreateEditKind:
    index: int
    name: str

@dataclass
class RenameEditKind:
    win: libtmux.Window
    name: str

@dataclass
class DeleteEditKind:
    win: libtmux.Window

@dataclass
class MoveEditKind:
    win: libtmux.Window
    target_index: int

@dataclass
class Plan:
    session: libtmux.Session
    steps: list[CreateEditKind | DeleteEditKind | MoveEditKind | RenameEditKind]
    initial_windows: list[TmuxWindow]

    @classmethod
    def create_plan(cls, session: libtmux.Session, initial_windows: list[TmuxWindow], new_state: str) -> 'Plan':

        existing_indexes: dict[int, TmuxWindow] = { win.index: win for win in initial_windows }

        # Remove leading and trailing whitespaces
        lines = [line.strip() for line in new_state.split('\n')]
        # Remove comments, that begin with #, or empty lines
        lines = [line for line in lines if not line.startswith('#') and line != ""]
        # Parse lines, accepted cases

        ##############
        # id: name   # -> split at the first :, and id must be a number, name can be empty, the the space is optional
        # _: name    # -> split at the first :, and id must be a '_', name can be empty, the the space is optional, means a new window, that we have to figure out the index for
        ##############

        if len(lines) == 0:
            # TODO: Handle close session
            raise RuntimeError("We do now currently support deleting the session")


        target_windows: list[tuple[int, str]] = []
        for line in lines:
            if ':' not in line:
                raise RuntimeError(f"Invalid line: {line}, expected: \"id: name\" or \"_: name\"")

            index, name = line.split(':', 1)
            if index != '_' and not index.isdigit():
                raise RuntimeError(f"Invalid line: {line}, invalid index, expected: number or _")

            index = -1 if index == '_' else int(index)
            target_windows.append((index, name.strip()))

        # target windows cannot have duplicate indexes (excluding -1), and every index must have existed beforehand
        seen_indecies: set[int] = set()
        for (index, _) in target_windows:
            if index == -1:  # This is a new entry
                continue

            # Check for duplicates
            if index in seen_indecies:
                raise RuntimeError(f"Index: {index} appeared twice")
            seen_indecies.add(index)

            if index not in existing_indexes:
                raise RuntimeError(f"Index: {index} did not exist, use \"_: name\" to create a new window")

        remaining_indexes: dict[int, str] = {index: name for (index, name) in target_windows if index != -1}

        # Steps
        # 1. Delete
        # 3. Rename windows
        # 2. Create the correct order
        # 4. Create new


        steps: list[CreateEditKind | DeleteEditKind | MoveEditKind | RenameEditKind] = []
        # The final position of the created element is the index(?)
        base_index = min(initial_windows, key=lambda x: x.index).index

        # Delete
        # The index offset should at position i mean that an index in the initial windows at pos i, should be shifted down index_offset[i]
        index_offset: list[int] = [0] * len(initial_windows)
        for (index, win) in existing_indexes.items():
            if index not in remaining_indexes:
                steps.append(DeleteEditKind(win.win))
                index_offset[win.index - base_index] = 1

        for i in range(1, len(index_offset)):
            index_offset[i] += index_offset[i - 1]


        # Rename
        for (index, win) in existing_indexes.items():
            # rename if it still exists and the name is different
            if index in remaining_indexes and remaining_indexes[index] != win.name:
                steps.append(RenameEditKind(win.win, remaining_indexes[index]))

        # Reorder
        # its tricky, since we can only move from A to pos B, meaning that if A < B then all indexes bigger then A and smaller then B will shift down
        # since things are only shifted down, we can start on the top and assign everything from the furthest target, since it is always the biggest remaining
        # it will not change positions after

        new_order: list[TmuxWindow] = [win for win in initial_windows if win.index in remaining_indexes]
        # print(f"base index: {base_index}")
        # print(index_offset)
        # target_windows_order = [w for w in target_windows if w[0] != -1]
        # for new_index, (initial_old_index, _) in reversed(list(enumerate(target_windows_order))):
        #     old_index = initial_old_index - index_offset[initial_old_index - base_index] - base_index
        #     print(f"move: {old_index} -> {new_index}")
        #     # target_windows_order[old_index] = (initial_old_index, target_windows_order[old_index][1])
        #     new_order[new_index], new_order[old_index] = new_order[old_index], new_order[new_index]
        
        new_index_by_old_index: dict[int, int] = {old_index: i + base_index for i, (old_index, _) in enumerate([w for w in target_windows if w[0] != -1]) }
        new_order.sort(key=lambda win: new_index_by_old_index[win.index])

        indecies = [i + base_index for i in range(len(new_order))]
        for i, win in reversed(list(enumerate(new_order))):
            new_index = i + base_index
            old_index = win.index - index_offset[win.index - base_index]

            if old_index != indecies[i]:
                # 1 3 4 5 2 || op 3 -> 4 
                index = indecies.index(old_index)
                indecies.pop(index)
                steps.append(MoveEditKind(win.win, new_index))
            else:
                indecies.pop()

        # Create new
        for i, (index, name) in enumerate(target_windows):
            if index == -1:
                steps.append(CreateEditKind(i + base_index, name))

        return Plan(session, steps, initial_windows)


    def execute(self) -> None:

        windows = list(self.session.windows)
        windows.sort(key = lambda x: int(x.index or ""))
        base_index = int(windows[0].index or "")

        def tmux_swap_and_shift(src: int, dest:int) -> None:
            current_pos = src
            while current_pos > dest:
                print(f"down, at index: {current_pos - base_index}")
                windows[current_pos - base_index].cmd("swap-window", "-s", f"{self.session.name}:{windows[current_pos - base_index].index}", target=f"{self.session.name}:{windows[current_pos - base_index - 1].index}")
                # windows[current_pos - base_index], windows[current_pos - 1 - base_index] = windows[current_pos - 1 - base_index], windows[current_pos - base_index]
                current_pos -= 1

            while current_pos < dest:
                print(f"up, at index: {current_pos - base_index}")
                windows[current_pos - base_index].cmd("swap-window", "-s", f"{self.session.name}:{windows[current_pos - base_index].index}", target=f"{self.session.name}:{windows[current_pos - base_index + 1].index}")
                # windows[current_pos - base_index], windows[current_pos + 1 - base_index] = windows[current_pos + 1 - base_index], windows[current_pos - base_index]
                current_pos += 1

        for step in self.steps:
            match step:
                case DeleteEditKind(win):
                    win.kill()
                case RenameEditKind(win, name):
                    win.rename_window(name)
                case MoveEditKind(win, target_index):
                    # win.move_window(str(target_index))
                    tmux_swap_and_shift(int(win.index or ""), target_index)
                case CreateEditKind(index, name):
                    win = self.session.new_window(name)
                    tmux_swap_and_shift(int(win.index or ""), index)


def main(session_id: str):
    server = libtmux.Server()  # Current server
    session = server.sessions.get(lambda x: x.name == session_id)
    if not session:
        raise RuntimeError("Found no sessions, and the lib does not work, since it sould not return None ever")
    windows = [TmuxWindow.from_window(win) for win in session.windows]


    # windows = list(session.windows)
    # windows.sort(key = lambda x: int(x.index or ""))
    # print(windows)
    # print(f"Things: {windows[3]}, {windows[3].id}, {windows[3].index}, {windows[3].window_index}, {windows[3].window_id}")
    # res = windows[3].cmd("swap-window", "-s", windows[3].index, target= "-1")
    # print(res.stdout)
    # print(res.stderr)
    # return 0


    buffer = ""
    buffer += "# Edit windows for session. Format: N: Title\n"
    buffer += "# Use _: Title to create new windows. Comments (#) and blank lines are ignored.\n"
    buffer += "\n"
    buffer += "\n".join(f"{w.index}: {w.name}" for w in windows)

    user_request = edit_text(buffer, ".tmux")
    if user_request is None:
        raise RuntimeError("Something went wrong opening the file")

    plan = Plan.create_plan(session, windows, user_request)

    print(plan.steps, flush=False)

    plan.execute()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a tmux session ID.")
    parser.add_argument("session_id", type=str, help="The tmux session ID (e.g., 1, 0:1, or my-session)")
    args = parser.parse_args()
    session_id = args.session_id
    main(session_id)
