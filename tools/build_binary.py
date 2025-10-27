import subprocess
import sys
import pathlib

def main():
    root = pathlib.Path(__file__).resolve().parent.parent
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "main.py",
        "--mode=onefile",
        "--output-dir=dist/bin",
        "--remove-output",
        "--output-filename=tmux-oil",
    ]
    print("🏗️  Building binary with Nuitka...")
    subprocess.run(cmd, cwd=root, check=True)
    print("✅  Binary built successfully at dist/bin/tmux-oil")

if __name__ == "__main__":
    main()
