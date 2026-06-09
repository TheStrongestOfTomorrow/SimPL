"""
SimPL TUI - Terminal User Interface

A rich, interactive terminal UI that launches when you type just 'simpl'.
Provides a menu-driven interface for running scripts, REPL mode, package
management, and more.

Supports: Linux, macOS, Windows, Termux (Android)
Requires: Python 3.8+ (no external deps - uses only stdlib)
"""

import os
import sys
import platform
import subprocess
import shutil
from typing import Optional, List


# ── ANSI Colors (works on Linux, macOS, Termux; graceful on Windows) ──────

class Colors:
    """ANSI color codes with automatic Windows/Termux compatibility."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    # Foreground
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright foreground
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Background
    BG_BLUE = "\033[44m"
    BG_CYAN = "\033[46m"
    BG_MAGENTA = "\033[45m"

    @classmethod
    def supports_color(cls) -> bool:
        """Check if the terminal supports ANSI colors."""
        # Windows 10+ with VT100
        if platform.system() == 'Windows':
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                # Enable ANSI escape sequences on Windows
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
                return True
            except Exception:
                return False
        # Termux and standard terminals
        if os.environ.get('TERM') == 'dumb':
            return False
        if not hasattr(sys.stdout, 'isatty') or not sys.stdout.isatty():
            return False
        return True

    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        """Apply color to text if colors are supported."""
        if cls.supports_color():
            return f"{color}{text}{cls.RESET}"
        return text


# ── Platform Detection ─────────────────────────────────────────────────────

def get_platform() -> str:
    """Detect the current platform: linux, macos, windows, termux, or unknown."""
    system = platform.system().lower()
    if system == 'linux':
        if os.path.exists('/data/data/com.termux'):
            return 'termux'
        if 'termux' in os.environ.get('PREFIX', '').lower():
            return 'termux'
        return 'linux'
    elif system == 'darwin':
        return 'macos'
    elif system == 'windows':
        return 'windows'
    return 'unknown'


def get_python_cmd() -> str:
    """Get the Python command for this platform."""
    return sys.executable or 'python3'


# ── TUI Drawing Helpers ────────────────────────────────────────────────────

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if platform.system() == 'Windows' else 'clear')


def draw_banner():
    """Draw the SimPL banner with version info."""
    C = Colors
    version = _get_version()

    banner_lines = [
        "",
        C.colorize("  ███████╗██╗███╗   ███╗", C.BRIGHT_CYAN),
        C.colorize("  ██╔════╝██║████╗ ████║", C.BRIGHT_CYAN),
        C.colorize("  ███████╗██║██╔████╔██║", C.BRIGHT_CYAN),
        C.colorize("  ╚════██║██║██║╚██╔╝██║", C.BRIGHT_CYAN),
        C.colorize("  ███████║██║██║ ╚═╝ ██║", C.BRIGHT_CYAN),
        C.colorize("  ╚══════╝╚═╝╚═╝     ╚═╝", C.BRIGHT_CYAN),
        "",
        C.colorize(f"  The Simple Programming Language v{version}", C.BRIGHT_WHITE + C.BOLD),
        C.colorize(f"  Platform: {get_platform().capitalize()} | Python {platform.python_version()}", C.DIM),
        "",
    ]
    return '\n'.join(banner_lines)


def draw_menu() -> str:
    """Draw the main menu."""
    C = Colors
    accent = C.BRIGHT_CYAN
    dim = C.DIM

    menu_items = [
        (C.colorize("1", accent), "Run a .simpl script"),
        (C.colorize("2", accent), "Interactive REPL"),
        (C.colorize("3", accent), "Install a package"),
        (C.colorize("4", accent), "Uninstall a package"),
        (C.colorize("5", accent), "List installed packages"),
        (C.colorize("6", accent), "Check script for errors"),
        (C.colorize("7", accent), "Show language reference"),
        (C.colorize("8", accent), "Create a new .simpl file"),
        (C.colorize("9", accent), "About SimPL"),
        (C.colorize("0", accent), "Exit"),
    ]

    lines = [
        C.colorize("  ┌──────────────────────────────────────┐", C.BRIGHT_CYAN),
        C.colorize("  │          ", C.BRIGHT_CYAN) + C.colorize("SimPL Main Menu", C.BOLD + C.BRIGHT_WHITE) + C.colorize("              │", C.BRIGHT_CYAN),
        C.colorize("  ├──────────────────────────────────────┤", C.BRIGHT_CYAN),
    ]

    for key, desc in menu_items:
        pad = 30 - len(desc)
        lines.append(
            C.colorize("  │", C.BRIGHT_CYAN) +
            f"  {key}. {desc}" + " " * pad +
            C.colorize("│", C.BRIGHT_CYAN)
        )

    lines.append(C.colorize("  └──────────────────────────────────────┘", C.BRIGHT_CYAN))
    lines.append("")
    return '\n'.join(lines)


def draw_prompt() -> str:
    """Draw the input prompt."""
    C = Colors
    return C.colorize("  simpl> ", C.BRIGHT_GREEN + C.BOLD)


def draw_separator(char: str = "─", width: int = 50) -> str:
    """Draw a horizontal separator line."""
    C = Colors
    return C.colorize(f"  {char * width}", C.BRIGHT_CYAN + C.DIM)


def draw_box(title: str, content: str) -> str:
    """Draw a titled box with content."""
    C = Colors
    lines = [
        draw_separator("═"),
        C.colorize(f"  {title}", C.BOLD + C.BRIGHT_WHITE),
        draw_separator("─"),
    ]
    for line in content.split('\n'):
        lines.append(f"  {line}")
    lines.append(draw_separator("═"))
    return '\n'.join(lines)


# ── Version Helper ─────────────────────────────────────────────────────────

def _get_version() -> str:
    """Get SimPL version from simpl.py."""
    try:
        # Try importing from the parent package
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from simpl import VERSION
        return VERSION
    except Exception:
        return "0.5.0"


# ── Interactive Actions ────────────────────────────────────────────────────

def action_run_script():
    """Prompt for a script path and run it."""
    C = Colors
    print()
    print(C.colorize("  Enter the path to your .simpl script:", C.BRIGHT_YELLOW))
    filepath = input(C.colorize("  path> ", C.BRIGHT_GREEN)).strip()

    if not filepath:
        print(C.colorize("  No path provided. Returning to menu.", C.RED))
        return

    if not os.path.exists(filepath):
        print(C.colorize(f"  File not found: {filepath}", C.RED))
        return

    # Run the script
    python_cmd = get_python_cmd()
    simpl_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'simpl.py')
    cmd = [python_cmd, simpl_path, 'run', filepath]
    print(draw_separator())
    try:
        subprocess.run(cmd)
    except Exception as e:
        print(C.colorize(f"  Error running script: {e}", C.RED))
    print(draw_separator())
    input(C.colorize("\n  Press Enter to continue...", C.DIM))


def action_repl():
    """Launch the interactive REPL."""
    python_cmd = get_python_cmd()
    simpl_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'simpl.py')
    cmd = [python_cmd, simpl_path, '--repl']
    try:
        subprocess.run(cmd)
    except Exception as e:
        print(Colors.colorize(f"  Error starting REPL: {e}", Colors.RED))


def action_install_package():
    """Prompt for a package name and install it."""
    C = Colors
    print()
    print(C.colorize("  Enter package name to install:", C.BRIGHT_YELLOW))
    print(C.colorize("  (prefix with npm: for NPM packages, e.g. npm:lodash)", C.DIM))
    pkg_name = input(C.colorize("  package> ", C.BRIGHT_GREEN)).strip()

    if not pkg_name:
        print(C.colorize("  No package name provided. Returning to menu.", C.RED))
        return

    python_cmd = get_python_cmd()
    simpl_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'simpl.py')
    cmd = [python_cmd, simpl_path, 'install', pkg_name]
    try:
        subprocess.run(cmd)
    except Exception as e:
        print(C.colorize(f"  Error installing package: {e}", C.RED))
    input(C.colorize("\n  Press Enter to continue...", C.DIM))


def action_uninstall_package():
    """Prompt for a package name and uninstall it."""
    C = Colors
    print()
    print(C.colorize("  Enter package name to uninstall:", C.BRIGHT_YELLOW))
    pkg_name = input(C.colorize("  package> ", C.BRIGHT_GREEN)).strip()

    if not pkg_name:
        print(C.colorize("  No package name provided. Returning to menu.", C.RED))
        return

    python_cmd = get_python_cmd()
    simpl_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'simpl.py')
    cmd = [python_cmd, simpl_path, 'uninstall', pkg_name]
    try:
        subprocess.run(cmd)
    except Exception as e:
        print(C.colorize(f"  Error uninstalling package: {e}", C.RED))
    input(C.colorize("\n  Press Enter to continue...", C.DIM))


def action_list_packages():
    """List all installed packages."""
    python_cmd = get_python_cmd()
    simpl_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'simpl.py')
    cmd = [python_cmd, simpl_path, 'list']
    try:
        subprocess.run(cmd)
    except Exception as e:
        print(Colors.colorize(f"  Error listing packages: {e}", Colors.RED))
    input(Colors.colorize("\n  Press Enter to continue...", Colors.DIM))


def action_check_script():
    """Prompt for a script path and check it for errors."""
    C = Colors
    print()
    print(C.colorize("  Enter the path to your .simpl script:", C.BRIGHT_YELLOW))
    filepath = input(C.colorize("  path> ", C.BRIGHT_GREEN)).strip()

    if not filepath:
        print(C.colorize("  No path provided. Returning to menu.", C.RED))
        return

    if not os.path.exists(filepath):
        print(C.colorize(f"  File not found: {filepath}", C.RED))
        return

    python_cmd = get_python_cmd()
    simpl_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'simpl.py')
    cmd = [python_cmd, simpl_path, '--check', filepath]
    try:
        subprocess.run(cmd)
    except Exception as e:
        print(C.colorize(f"  Error checking script: {e}", C.RED))
    input(C.colorize("\n  Press Enter to continue...", C.DIM))


def action_show_reference():
    """Show the SimPL language quick reference."""
    C = Colors
    ref = f"""
{C.colorize("VARIABLES", C.BOLD + C.BRIGHT_CYAN)}
  let name = "SimPL"        # String
  let version = 0.5          # Number
  let is_cool = true         # Boolean
  let items = [1, 2, 3]     # List

{C.colorize("CONDITIONALS", C.BOLD + C.BRIGHT_CYAN)}
  if x > 5 then             # Standard
      print "big"
  elif x > 3 then
      print "medium"
  else
      print "small"
  end

  if (x > 5) {{               # C/JS style
      print "big";
  }}

  if x > 5:                 # Python style
      print "big"

{C.colorize("LOOPS", C.BOLD + C.BRIGHT_CYAN)}
  while i < 10 do ... end
  for item in [1, 2, 3] do ... end
  for item in range(10) do ... end
  repeat 5 times ... end

{C.colorize("FUNCTIONS", C.BOLD + C.BRIGHT_CYAN)}
  function greet(name)
      return "Hello, " + name + "!"
  end

{C.colorize("BUILT-IN FUNCTIONS (30+)", C.BOLD + C.BRIGHT_CYAN)}
  Math:     abs, min, max, round, floor, ceil, sqrt, pow, random
  Strings:  str, upper, lower, trim, split, join, replace, len
  Lists:    push, pop, range, len, reverse, sort, contains
  Types:    type, int, float, str, bool
  I/O:      print, input, read_file, write_file, append_file
  System:   time, sleep, env, shell
  Interop:  js_eval(code)   # JavaScript Bridge

{C.colorize("DICTIONARIES", C.BOLD + C.BRIGHT_CYAN)}
  let person = {{"name": "Alice", "age": 30}}
  print person["name"]

{C.colorize("FILE I/O", C.BOLD + C.BRIGHT_CYAN)}
  let content = read_file("data.txt")
  write_file("output.txt", "Hello!")

{C.colorize("TRY / CATCH", C.BOLD + C.BRIGHT_CYAN)}
  try
      let result = x / y
  catch
      print "Division error!"
  end
"""
    print(draw_box("SimPL Language Reference", ref))
    input(C.colorize("\n  Press Enter to continue...", C.DIM))


def action_new_file():
    """Create a new .simpl file with a template."""
    C = Colors
    print()
    print(C.colorize("  Enter filename (e.g., hello.simpl):", C.BRIGHT_YELLOW))
    filename = input(C.colorize("  filename> ", C.BRIGHT_GREEN)).strip()

    if not filename:
        print(C.colorize("  No filename provided. Returning to menu.", C.RED))
        return

    if not filename.endswith('.simpl'):
        filename += '.simpl'

    if os.path.exists(filename):
        print(C.colorize(f"  File already exists: {filename}", C.BRIGHT_YELLOW))
        overwrite = input(C.colorize("  Overwrite? (y/N): ", C.BRIGHT_YELLOW)).strip().lower()
        if overwrite != 'y':
            return

    template = '''# SimPL Script: {name}
# Created with SimPL TUI

let message = "Hello, SimPL!"
print message

# Try uncommenting these:
# let x = 10
# let y = 20
# print "Sum: " + str(x + y)

# function greet(name)
#     return "Hello, " + name + "!"
# end
# print greet("World")
'''.format(name=filename.replace('.simpl', ''))

    try:
        with open(filename, 'w') as f:
            f.write(template)
        print(C.colorize(f"  Created {filename}", C.BRIGHT_GREEN))
        print(C.colorize(f"  Run it with: simpl run {filename}", C.DIM))
    except Exception as e:
        print(C.colorize(f"  Error creating file: {e}", C.RED))

    input(C.colorize("\n  Press Enter to continue...", C.DIM))


def action_about():
    """Show about information."""
    C = Colors
    version = _get_version()
    plat = get_platform().capitalize()
    py_ver = platform.python_version()
    node_status = "Available"
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            node_status = f"Available ({result.stdout.strip()})"
        else:
            node_status = "Not found"
    except Exception:
        node_status = "Not found"

    about = f"""
{C.colorize("SimPL", C.BOLD + C.BRIGHT_CYAN)} - The Simple Programming Language
Version: {version}

A beginner-friendly programming language designed to be as readable
as English while remaining versatile enough for scripts, web projects,
and games.

{C.colorize("Features:", C.BOLD)}
  - 3 Syntax Flavors: Standard, C/JS, Python
  - 30+ Built-in Functions
  - NPM Bridge (JavaScript interop)
  - Community Package Manager
  - Smart Error Messages
  - Interactive REPL & TUI

{C.colorize("Environment:", C.BOLD)}
  Platform:    {plat}
  Python:      {py_ver}
  Node.js:     {node_status}

{C.colorize("Links:", C.BOLD)}
  GitHub:  github.com/thestrongestoftomorrow/SimPL
  Packages: github.com/thestrongestoftomorrow/SimPL-Libraries

Copyright (c) 2024-2026 TheStrongestOfTomorrow
MIT License
"""
    print(draw_box("About SimPL", about))
    input(C.colorize("\n  Press Enter to continue...", C.DIM))


# ── Main TUI Loop ──────────────────────────────────────────────────────────

MENU_ACTIONS = {
    '1': action_run_script,
    '2': action_repl,
    '3': action_install_package,
    '4': action_uninstall_package,
    '5': action_list_packages,
    '6': action_check_script,
    '7': action_show_reference,
    '8': action_new_file,
    '9': action_about,
}


def run_tui():
    """Main TUI entry point - interactive menu loop."""
    C = Colors

    while True:
        clear_screen()
        print(draw_banner())
        print(draw_menu())

        try:
            choice = input(draw_prompt()).strip()
        except (KeyboardInterrupt, EOFError):
            print(C.colorize("\n  Goodbye!", C.BRIGHT_GREEN))
            break

        if choice in ('0', 'exit', 'quit', 'q'):
            print()
            print(C.colorize("  Goodbye! Thanks for using SimPL!", C.BRIGHT_GREEN))
            print()
            break

        action = MENU_ACTIONS.get(choice)
        if action:
            action()
        else:
            print(C.colorize(f"  Unknown option: {choice}", C.RED))
            input(C.colorize("  Press Enter to continue...", C.DIM))


# ── Entry Point ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    run_tui()
