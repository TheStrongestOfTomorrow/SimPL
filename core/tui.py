"""
SimPL TUI - Terminal User Interface

A rich, interactive terminal UI that launches when you type just 'simpl'.
Provides a menu-driven interface for running scripts, REPL mode, package
management, auto-update checking, SimPL Studio (basic code editor),
dependency setup, and package browsing.

Supports: Linux, macOS, Windows, Termux (Android)
Requires: Python 3.8+ (no external deps - uses only stdlib)
"""

import os
import sys
import platform
import subprocess
import shutil
import json
import time
import re
from typing import Optional, List


# ── Import from package_manager ────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from package_manager import list_available_packages, install_package, get_dependency_status, check_node_available, check_curl_available, check_git_available, check_python_available


# ── ANSI Colors (works on Linux, macOS, Termux; graceful on Windows) ──────

class Colors:
    """ANSI color codes with automatic Windows/Termux compatibility."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"

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
    BG_GREEN = "\033[42m"

    @classmethod
    def supports_color(cls) -> bool:
        """Check if the terminal supports ANSI colors."""
        if platform.system() == 'Windows':
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
                return True
            except Exception:
                return False
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


# ── Version Helper ─────────────────────────────────────────────────────────

def _get_version() -> str:
    """Get SimPL version from simpl.py."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from simpl import VERSION
        return VERSION
    except Exception:
        return "0.8.0"


# ── Auto-Update Checker ───────────────────────────────────────────────────

def check_for_updates() -> Optional[str]:
    """
    Check GitHub for the latest SimPL version.

    Returns:
        The latest version string if an update is available, None otherwise.
    """
    try:
        result = subprocess.run(
            ['curl', '-sS', '--max-time', '5',
             'https://raw.githubusercontent.com/TheStrongestOfTomorrow/SimPL/main/simpl.py'],
            capture_output=True, text=True, timeout=8
        )
        if result.returncode != 0:
            return None

        for line in result.stdout.split('\n'):
            if line.strip().startswith('VERSION = '):
                remote_version = line.strip().split('"')[1]
                current_version = _get_version()
                if remote_version != current_version:
                    return remote_version
                return None
    except Exception:
        pass
    return None


def get_update_instructions() -> str:
    """Return instructions for updating SimPL based on install method."""
    plat = get_platform()
    simpl_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Check if installed via git clone
    git_dir = os.path.join(simpl_dir, '.git')
    if os.path.exists(git_dir):
        return "  cd " + simpl_dir + " && git pull"

    # Default: re-run install script
    if plat in ('linux', 'macos', 'termux'):
        return "  curl -sSL https://raw.githubusercontent.com/TheStrongestOfTomorrow/SimPL/main/install.sh | bash"
    elif plat == 'windows':
        return "  Download latest from: github.com/TheStrongestOfTomorrow/SimPL"
    return "  git pull or re-run install script"


# ── TUI Drawing Helpers ────────────────────────────────────────────────────

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if platform.system() == 'Windows' else 'clear')


def draw_banner(update_available: str = None) -> str:
    """Draw the SimPL banner with version info and optional update notice."""
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
    ]

    if update_available:
        banner_lines.append("")
        banner_lines.append(
            C.colorize(f"  UPDATE AVAILABLE: v{update_available}", C.BRIGHT_YELLOW + C.BOLD)
        )
        banner_lines.append(C.colorize("  Select [U] to update or see instructions", C.DIM))

    banner_lines.append("")
    return '\n'.join(banner_lines)


def draw_menu() -> str:
    """Draw the main menu."""
    C = Colors
    accent = C.BRIGHT_CYAN

    menu_items = [
        (C.colorize("1", accent), "Run a .simpl script"),
        (C.colorize("2", accent), "Interactive REPL"),
        (C.colorize("3", accent), "Install a package"),
        (C.colorize("4", accent), "Uninstall a package"),
        (C.colorize("5", accent), "List installed packages"),
        (C.colorize("6", accent), "Check script for errors"),
        (C.colorize("7", accent), "Show language reference"),
        (C.colorize("8", accent), "Create a new .simpl file"),
        (C.colorize("9", accent), "SimPL Studio (code editor)"),
        (C.colorize("S", accent), "Setup & Dependencies"),
        (C.colorize("B", accent), "Browse & Install Packages"),
        (C.colorize("A", accent), "About SimPL"),
        (C.colorize("U", accent), "Check for updates"),
        (C.colorize("0", accent), "Exit"),
    ]

    lines = [
        C.colorize("  ┌──────────────────────────────────────────┐", C.BRIGHT_CYAN),
        C.colorize("  │            ", C.BRIGHT_CYAN) + C.colorize("SimPL Main Menu", C.BOLD + C.BRIGHT_WHITE) + C.colorize("                  │", C.BRIGHT_CYAN),
        C.colorize("  ├──────────────────────────────────────────┤", C.BRIGHT_CYAN),
    ]

    for key, desc in menu_items:
        pad = 34 - len(desc)
        lines.append(
            C.colorize("  │", C.BRIGHT_CYAN) +
            f"  {key}. {desc}" + " " * pad +
            C.colorize("│", C.BRIGHT_CYAN)
        )

    lines.append(C.colorize("  └──────────────────────────────────────────┘", C.BRIGHT_CYAN))
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


# ── Syntax Highlighting for SimPL Studio ───────────────────────────────────

# SimPL keywords for syntax highlighting
SIMPL_KEYWORDS = {
    'let', 'if', 'then', 'elif', 'else', 'end', 'while', 'do', 'for', 'in',
    'function', 'return', 'repeat', 'times', 'true', 'false', 'null', 'and',
    'or', 'not', 'try', 'catch',
}

SIMPL_BUILTINS = {
    'print', 'input', 'type', 'int', 'float', 'str', 'bool',
    'abs', 'min', 'max', 'round', 'floor', 'ceil', 'sqrt', 'pow', 'random',
    'upper', 'lower', 'trim', 'split', 'join', 'replace', 'len',
    'push', 'pop', 'range', 'reverse', 'sort', 'contains', 'slice',
    'keys', 'values', 'has_key', 'remove',
    'read_file', 'write_file', 'append_file',
    'time', 'sleep', 'env', 'shell',
    'js_eval', 'get', 'post', 'parse_json', 'to_json',
    'index_of', 'starts_with', 'ends_with',
}


def highlight_simpl_line(line: str) -> str:
    """Apply basic syntax highlighting to a SimPL code line."""
    C = Colors
    if not C.supports_color():
        return line

    result = []
    i = 0
    length = len(line)

    while i < length:
        ch = line[i]

        # Comment: # to end of line
        if ch == '#':
            result.append(C.colorize(line[i:], C.DIM))
            break

        # String: double-quoted
        elif ch == '"':
            j = i + 1
            while j < length and line[j] != '"':
                if line[j] == '\\':
                    j += 1  # skip escaped char
                j += 1
            j = min(j + 1, length)  # include closing quote
            result.append(C.colorize(line[i:j], C.GREEN))
            i = j
            continue

        # String: single-quoted
        elif ch == "'":
            j = i + 1
            while j < length and line[j] != "'":
                if line[j] == '\\':
                    j += 1
                j += 1
            j = min(j + 1, length)
            result.append(C.colorize(line[i:j], C.GREEN))
            i = j
            continue

        # Number
        elif ch.isdigit() or (ch == '-' and i + 1 < length and line[i + 1].isdigit() and
                              (i == 0 or not line[i - 1].isalnum() and line[i - 1] != '_')):
            j = i
            if ch == '-':
                j += 1
            while j < length and (line[j].isdigit() or line[j] == '.'):
                j += 1
            result.append(C.colorize(line[i:j], C.YELLOW))
            i = j
            continue

        # Identifier / keyword
        elif ch.isalpha() or ch == '_':
            j = i
            while j < length and (line[j].isalnum() or line[j] == '_'):
                j += 1
            word = line[i:j]
            if word in SIMPL_KEYWORDS:
                result.append(C.colorize(word, C.CYAN + C.BOLD))
            elif word in SIMPL_BUILTINS:
                result.append(C.colorize(word, C.BRIGHT_MAGENTA))
            else:
                result.append(word)
            i = j
            continue

        # Operators and punctuation
        elif ch in '=<>!+-*/%':
            result.append(C.colorize(ch, C.BRIGHT_RED))
            i += 1
            continue

        else:
            result.append(ch)
            i += 1

    return ''.join(result)


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
  let version = 0.7          # Number
  let is_cool = true         # Boolean
  let items = [1, 2, 3]     # List
  let config = {{"key": "val"}}  # Dict

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

{C.colorize("BUILT-IN FUNCTIONS (50+)", C.BOLD + C.BRIGHT_CYAN)}
  Math:     abs, min, max, round, floor, ceil, sqrt, pow, random
  Strings:  str, upper, lower, trim, split, join, replace, len
  Lists:    push, pop, range, len, reverse, sort, contains, slice
  Dicts:    keys, values, has_key, remove
  Types:    type, int, float, str, bool
  I/O:      print, input, read_file, write_file, append_file
  HTTP:     get(url), post(url, data), response.json()
  JSON:     parse_json(string), to_json(obj, pretty?)
  System:   time, sleep, env, shell
  Interop:  js_eval(code)   # JavaScript Bridge

{C.colorize("HTTP REQUESTS", C.BOLD + C.BRIGHT_CYAN)}
  let response = get "https://api.example.com/data"
  print response["status"]
  let data = response.json()
  print data["name"]

  let result = post "https://api.example.com/submit", {{"key": "value"}}

{C.colorize("JSON", C.BOLD + C.BRIGHT_CYAN)}
  let obj = parse_json('{{"name": "SimPL"}}')
  let str = to_json(obj, true)

{C.colorize("DICTIONARIES", C.BOLD + C.BRIGHT_CYAN)}
  let person = {{"name": "Alice", "age": 30}}
  print person["name"]
  print has_key(person, "age")
  remove(person, "age")

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
# Created with SimPL TUI v{version}

let message = "Hello, SimPL!"
print message

# Try uncommenting these:
# let x = 10
# let y = 20
# print "Sum: " + str(x + y)

# HTTP example:
# let response = get "https://api.github.com/repos/TheStrongestOfTomorrow/SimPL"
# let data = response.json()
# print data["full_name"]

# JSON example:
# let config = {{"name": "{name}", "version": "1.0"}}
# write_file("config.json", to_json(config, true))
'''.format(name=filename.replace('.simpl', ''), version=_get_version())

    try:
        with open(filename, 'w') as f:
            f.write(template)
        print(C.colorize(f"  Created {filename}", C.BRIGHT_GREEN))
        print(C.colorize(f"  Run it with: simpl run {filename}", C.DIM))
    except Exception as e:
        print(C.colorize(f"  Error creating file: {e}", C.RED))

    input(C.colorize("\n  Press Enter to continue...", C.DIM))


def action_setup_dependencies():
    """Setup & Dependencies - show dependency status and install options."""
    C = Colors
    plat = get_platform()

    while True:
        print()
        print(draw_separator("═"))
        print(C.colorize("  Setup & Dependencies", C.BOLD + C.BRIGHT_MAGENTA))
        print(C.colorize(f"  Platform: {plat.capitalize()}", C.DIM))
        print(draw_separator("─"))

        # Get dependency status
        try:
            deps = get_dependency_status()
        except Exception:
            deps = {
                'python': {'available': True, 'version': platform.python_version(), 'required': True, 'label': 'Python (Required)'},
                'node': {'available': False, 'version': None, 'required': False, 'label': 'Node.js (NPM Bridge)'},
                'curl': {'available': False, 'version': None, 'required': True, 'label': 'curl (Required)'},
                'git': {'available': False, 'version': None, 'required': False, 'label': 'git (Updates)'},
            }

        print()
        print(C.colorize("  Dependency Status:", C.BOLD + C.BRIGHT_CYAN))
        print()

        for name, info in deps.items():
            avail = info['available']
            ver = info['version'] or 'N/A'
            req = "Required" if info['required'] else "Optional"

            if avail:
                status_icon = C.colorize("✓", C.BRIGHT_GREEN + C.BOLD)
                status_text = C.colorize(f"Available (v{ver})", C.BRIGHT_GREEN)
            else:
                status_icon = C.colorize("✗", C.BRIGHT_RED + C.BOLD)
                status_text = C.colorize("Not found", C.BRIGHT_RED)

            print(f"  {status_icon}  {info['label']}: {status_text}  [{C.colorize(req, C.DIM)}]")

        # Show install instructions for missing dependencies
        missing = {k: v for k, v in deps.items() if not v['available']}

        if missing:
            print()
            print(C.colorize("  Install Commands:", C.BOLD + C.BRIGHT_YELLOW))
            print()

            if plat == 'termux':
                if 'node' in missing:
                    print(f"    Node.js:  {C.colorize('pkg install nodejs', C.BRIGHT_WHITE)}")
                if 'curl' in missing:
                    print(f"    curl:     {C.colorize('pkg install curl', C.BRIGHT_WHITE)}")
                if 'git' in missing:
                    print(f"    git:      {C.colorize('pkg install git', C.BRIGHT_WHITE)}")

            elif plat == 'linux':
                if 'node' in missing:
                    print(f"    Node.js:  {C.colorize('sudo apt install nodejs', C.BRIGHT_WHITE)}")
                if 'curl' in missing:
                    print(f"    curl:     {C.colorize('sudo apt install curl', C.BRIGHT_WHITE)}")
                if 'git' in missing:
                    print(f"    git:      {C.colorize('sudo apt install git', C.BRIGHT_WHITE)}")

            elif plat == 'macos':
                cmds = []
                if 'node' in missing:
                    cmds.append('node')
                if 'curl' in missing:
                    cmds.append('curl')
                if 'git' in missing:
                    cmds.append('git')
                if cmds:
                    print(f"    All:      {C.colorize('brew install ' + ' '.join(cmds), C.BRIGHT_WHITE)}")

            elif plat == 'windows':
                if 'node' in missing:
                    print(f"    Node.js:  {C.colorize('https://nodejs.org/en/download/', C.BRIGHT_WHITE)}")
                if 'curl' in missing:
                    print(f"    curl:     {C.colorize('Usually included with Windows 10+', C.DIM)}")
                if 'git' in missing:
                    print(f"    git:      {C.colorize('https://git-scm.com/download/win', C.BRIGHT_WHITE)}")

            else:
                if 'node' in missing:
                    print(f"    Node.js:  Install from https://nodejs.org/")
                if 'curl' in missing:
                    print(f"    curl:     Install via your package manager")
                if 'git' in missing:
                    print(f"    git:      Install from https://git-scm.com/")

            # Auto-install on supported platforms
            if plat in ('termux', 'linux'):
                print()
                print(C.colorize("  Auto-Install:", C.BOLD + C.BRIGHT_CYAN))
                if 'node' in missing:
                    print(f"    [1] Install Node.js")
                if 'curl' in missing:
                    print(f"    [2] Install curl")
                if 'git' in missing:
                    print(f"    [3] Install git")
                print(f"    [A] Install all missing")
        else:
            print()
            print(C.colorize("  All dependencies satisfied! ✓", C.BRIGHT_GREEN + C.BOLD))

        print()
        print(C.colorize("  [R] Refresh  [Q] Back to menu", C.DIM))
        print()

        try:
            choice = input(C.colorize("  setup> ", C.BRIGHT_GREEN + C.BOLD)).strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if choice in ('q', 'quit', 'back', ''):
            break

        elif choice == 'r':
            continue

        elif choice == '1' and 'node' in missing:
            if plat == 'termux':
                print(C.colorize("  Installing Node.js (pkg install nodejs)...", C.BRIGHT_YELLOW))
                try:
                    subprocess.run(['pkg', 'install', 'nodejs', '-y'], check=False)
                    print(C.colorize("  Done! Node.js installed.", C.BRIGHT_GREEN))
                except Exception as e:
                    print(C.colorize(f"  Error: {e}", C.RED))
            elif plat == 'linux':
                print(C.colorize("  Installing Node.js (sudo apt install nodejs)...", C.BRIGHT_YELLOW))
                try:
                    subprocess.run(['sudo', 'apt', 'install', 'nodejs', '-y'], check=False)
                    print(C.colorize("  Done! Node.js installed.", C.BRIGHT_GREEN))
                except Exception as e:
                    print(C.colorize(f"  Error: {e}", C.RED))
            else:
                print(C.colorize("  Auto-install not supported on this platform.", C.BRIGHT_YELLOW))
            input(C.colorize("\n  Press Enter to continue...", C.DIM))

        elif choice == '2' and 'curl' in missing:
            if plat == 'termux':
                print(C.colorize("  Installing curl (pkg install curl)...", C.BRIGHT_YELLOW))
                try:
                    subprocess.run(['pkg', 'install', 'curl', '-y'], check=False)
                    print(C.colorize("  Done! curl installed.", C.BRIGHT_GREEN))
                except Exception as e:
                    print(C.colorize(f"  Error: {e}", C.RED))
            elif plat == 'linux':
                print(C.colorize("  Installing curl (sudo apt install curl)...", C.BRIGHT_YELLOW))
                try:
                    subprocess.run(['sudo', 'apt', 'install', 'curl', '-y'], check=False)
                    print(C.colorize("  Done! curl installed.", C.BRIGHT_GREEN))
                except Exception as e:
                    print(C.colorize(f"  Error: {e}", C.RED))
            else:
                print(C.colorize("  Auto-install not supported on this platform.", C.BRIGHT_YELLOW))
            input(C.colorize("\n  Press Enter to continue...", C.DIM))

        elif choice == '3' and 'git' in missing:
            if plat == 'termux':
                print(C.colorize("  Installing git (pkg install git)...", C.BRIGHT_YELLOW))
                try:
                    subprocess.run(['pkg', 'install', 'git', '-y'], check=False)
                    print(C.colorize("  Done! git installed.", C.BRIGHT_GREEN))
                except Exception as e:
                    print(C.colorize(f"  Error: {e}", C.RED))
            elif plat == 'linux':
                print(C.colorize("  Installing git (sudo apt install git)...", C.BRIGHT_YELLOW))
                try:
                    subprocess.run(['sudo', 'apt', 'install', 'git', '-y'], check=False)
                    print(C.colorize("  Done! git installed.", C.BRIGHT_GREEN))
                except Exception as e:
                    print(C.colorize(f"  Error: {e}", C.RED))
            else:
                print(C.colorize("  Auto-install not supported on this platform.", C.BRIGHT_YELLOW))
            input(C.colorize("\n  Press Enter to continue...", C.DIM))

        elif choice == 'a':
            if plat == 'termux':
                pkgs = []
                if 'node' in missing:
                    pkgs.append('nodejs')
                if 'curl' in missing:
                    pkgs.append('curl')
                if 'git' in missing:
                    pkgs.append('git')
                if pkgs:
                    print(C.colorize(f"  Installing: {', '.join(pkgs)}...", C.BRIGHT_YELLOW))
                    try:
                        subprocess.run(['pkg', 'install'] + pkgs + ['-y'], check=False)
                        print(C.colorize("  Done! All missing packages installed.", C.BRIGHT_GREEN))
                    except Exception as e:
                        print(C.colorize(f"  Error: {e}", C.RED))
            elif plat == 'linux':
                pkgs = []
                if 'node' in missing:
                    pkgs.append('nodejs')
                if 'curl' in missing:
                    pkgs.append('curl')
                if 'git' in missing:
                    pkgs.append('git')
                if pkgs:
                    print(C.colorize(f"  Installing: {', '.join(pkgs)}...", C.BRIGHT_YELLOW))
                    try:
                        subprocess.run(['sudo', 'apt', 'install'] + pkgs + ['-y'], check=False)
                        print(C.colorize("  Done! All missing packages installed.", C.BRIGHT_GREEN))
                    except Exception as e:
                        print(C.colorize(f"  Error: {e}", C.RED))
            elif plat == 'macos':
                pkgs = []
                if 'node' in missing:
                    pkgs.append('node')
                if 'curl' in missing:
                    pkgs.append('curl')
                if 'git' in missing:
                    pkgs.append('git')
                if pkgs:
                    print(C.colorize(f"  Installing: {', '.join(pkgs)} via brew...", C.BRIGHT_YELLOW))
                    try:
                        subprocess.run(['brew', 'install'] + pkgs, check=False)
                        print(C.colorize("  Done! All missing packages installed.", C.BRIGHT_GREEN))
                    except Exception as e:
                        print(C.colorize(f"  Error: {e}", C.RED))
            else:
                print(C.colorize("  Auto-install not supported on this platform.", C.BRIGHT_YELLOW))
            input(C.colorize("\n  Press Enter to continue...", C.DIM))


def action_browse_packages():
    """Browse & Install Packages - list available packages and let user pick one."""
    C = Colors

    print()
    print(C.colorize("  Fetching available packages...", C.BRIGHT_YELLOW))

    try:
        packages = list_available_packages()
    except Exception as e:
        print(C.colorize(f"  Error fetching packages: {e}", C.RED))
        input(C.colorize("\n  Press Enter to continue...", C.DIM))
        return

    if not packages:
        print(C.colorize("  No packages available.", C.BRIGHT_YELLOW))
        input(C.colorize("\n  Press Enter to continue...", C.DIM))
        return

    while True:
        print()
        print(draw_separator("═"))
        print(C.colorize("  Browse & Install Packages", C.BOLD + C.BRIGHT_MAGENTA))
        print(C.colorize(f"  {len(packages)} package(s) available", C.DIM))
        print(draw_separator("─"))
        print()

        for idx, pkg in enumerate(packages, 1):
            name = pkg.get('name', 'unknown')
            version = pkg.get('version', '0.0.0')
            description = pkg.get('description', 'No description')
            author = pkg.get('author', '')

            num = C.colorize(f"{idx:2d}", C.BRIGHT_CYAN)
            pkg_name = C.colorize(name, C.BRIGHT_WHITE + C.BOLD)
            pkg_ver = C.colorize(f"v{version}", C.BRIGHT_GREEN)
            pkg_desc = C.colorize(f" - {description}", C.DIM)

            print(f"  {num}. {pkg_name} {pkg_ver}{pkg_desc}")

        print()
        print(C.colorize("  Enter number to install, or [Q] to go back", C.DIM))
        print()

        try:
            choice = input(C.colorize("  browse> ", C.BRIGHT_GREEN + C.BOLD)).strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if choice in ('q', 'quit', 'back', ''):
            break

        # Try to parse as a number
        try:
            num = int(choice)
            if 1 <= num <= len(packages):
                pkg = packages[num - 1]
                pkg_name = pkg.get('name', '')
                pkg_ver = pkg.get('version', '?')
                pkg_desc = pkg.get('description', '')

                print()
                print(C.colorize(f"  Installing: {pkg_name} v{pkg_ver}", C.BRIGHT_YELLOW))
                print(C.colorize(f"  {pkg_desc}", C.DIM))
                print()

                try:
                    result = install_package(pkg_name)
                    if result:
                        print(C.colorize(f"  Successfully installed {pkg_name}!", C.BRIGHT_GREEN))
                    else:
                        print(C.colorize(f"  Could not install {pkg_name}.", C.BRIGHT_YELLOW))
                except Exception as e:
                    print(C.colorize(f"  Error installing package: {e}", C.RED))

                input(C.colorize("\n  Press Enter to continue...", C.DIM))
            else:
                print(C.colorize(f"  Invalid number: {num}. Choose 1-{len(packages)}.", C.RED))
                input(C.colorize("\n  Press Enter to continue...", C.DIM))
        except ValueError:
            print(C.colorize(f"  Invalid input. Enter a number or Q to go back.", C.RED))
            input(C.colorize("\n  Press Enter to continue...", C.DIM))


def action_studio():
    """SimPL Studio - An in-terminal code editor with syntax highlighting."""
    C = Colors

    print()
    print(draw_separator("═"))
    print(C.colorize("  SimPL Studio v2.0", C.BOLD + C.BRIGHT_MAGENTA))
    print(C.colorize("  A code editor for .simpl files with syntax highlighting", C.DIM))
    print(draw_separator("─"))
    print()
    print(C.colorize("  Commands:", C.BOLD + C.BRIGHT_CYAN))
    print(C.colorize("    :save <filename>   Save to file", C.BRIGHT_WHITE))
    print(C.colorize("    :run               Run the current code", C.BRIGHT_WHITE))
    print(C.colorize("    :load <filename>   Load a file into editor", C.BRIGHT_WHITE))
    print(C.colorize("    :new               Clear and start fresh", C.BRIGHT_WHITE))
    print(C.colorize("    :clear             Clear the editor", C.BRIGHT_WHITE))
    print(C.colorize("    :help              Show all editor commands", C.BRIGHT_WHITE))
    print(C.colorize("    :quit              Exit studio", C.BRIGHT_WHITE))
    print()

    code_lines = []
    current_file = None

    def _show_help():
        """Show studio help."""
        print()
        print(draw_separator("─"))
        print(C.colorize("  SimPL Studio Commands:", C.BOLD + C.BRIGHT_CYAN))
        print()
        print(C.colorize("    :save <filename>   Save code to a file", C.BRIGHT_WHITE))
        print(C.colorize("    :save              Save to current file (if loaded)", C.BRIGHT_WHITE))
        print(C.colorize("    :run               Run the current code", C.BRIGHT_WHITE))
        print(C.colorize("    :load <filename>   Load a file into the editor", C.BRIGHT_WHITE))
        print(C.colorize("    :new               Clear editor and start fresh", C.BRIGHT_WHITE))
        print(C.colorize("    :clear             Clear all lines from editor", C.BRIGHT_WHITE))
        print(C.colorize("    :help              Show this help message", C.BRIGHT_WHITE))
        print(C.colorize("    :quit  or  :q      Exit SimPL Studio", C.BRIGHT_WHITE))
        print()
        print(C.colorize("  Syntax Highlighting:", C.BOLD + C.BRIGHT_CYAN))
        print(C.colorize("    Keywords", C.CYAN + C.BOLD) + "  " +
              C.colorize("Strings", C.GREEN) + "  " +
              C.colorize("Comments", C.DIM) + "  " +
              C.colorize("Numbers", C.YELLOW) + "  " +
              C.colorize("Built-ins", C.BRIGHT_MAGENTA))
        print(draw_separator("─"))
        print()

    while True:
        try:
            line_num = len(code_lines) + 1
            # Show current file name in prompt
            if current_file:
                file_label = C.colorize(f"[{current_file}]", C.BRIGHT_YELLOW)
                prompt = C.colorize(f"  {line_num:3d} | ", C.BRIGHT_CYAN) + file_label + " "
            else:
                prompt = C.colorize(f"  {line_num:3d} | ", C.BRIGHT_CYAN)
            line = input(prompt)
        except (KeyboardInterrupt, EOFError):
            print()
            break

        # Check for commands
        stripped = line.strip()

        if stripped == ':quit' or stripped == ':q':
            break

        elif stripped.startswith(':save'):
            parts = stripped.split(None, 1)
            filename = parts[1] if len(parts) > 1 else current_file
            if not filename:
                print(C.colorize("  Error: No filename specified. Use :save <filename>", C.RED))
                continue
            if not filename.endswith('.simpl'):
                filename += '.simpl'
            try:
                with open(filename, 'w') as f:
                    f.write('\n'.join(code_lines))
                current_file = filename
                print(C.colorize(f"  Saved to {filename} ({len(code_lines)} lines)", C.BRIGHT_GREEN))
            except Exception as e:
                print(C.colorize(f"  Error saving: {e}", C.RED))

        elif stripped == ':run':
            if not code_lines:
                print(C.colorize("  Nothing to run!", C.BRIGHT_YELLOW))
                continue
            code = '\n'.join(code_lines)
            python_cmd = get_python_cmd()
            simpl_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'simpl.py')

            # Write to a temp file and run
            tmp_file = '.simpl_studio_temp.simpl'
            try:
                with open(tmp_file, 'w') as f:
                    f.write(code)
                print(draw_separator())
                subprocess.run([python_cmd, simpl_path, 'run', tmp_file])
                print(draw_separator())
            except Exception as e:
                print(C.colorize(f"  Error running: {e}", C.RED))
            finally:
                if os.path.exists(tmp_file):
                    os.unlink(tmp_file)

        elif stripped == ':new':
            code_lines = []
            current_file = None
            print(C.colorize("  Editor cleared. Starting fresh.", C.BRIGHT_GREEN))

        elif stripped == ':clear':
            code_lines = []
            print(C.colorize("  Editor cleared.", C.BRIGHT_GREEN))

        elif stripped.startswith(':load'):
            parts = stripped.split(None, 1)
            if len(parts) < 2:
                print(C.colorize("  Usage: :load <filename>", C.RED))
                continue
            filename = parts[1]
            if not os.path.exists(filename):
                print(C.colorize(f"  File not found: {filename}", C.RED))
                continue
            try:
                with open(filename, 'r') as f:
                    code_lines = f.read().split('\n')
                current_file = filename
                # Remove trailing empty line if present
                if code_lines and code_lines[-1] == '':
                    code_lines = code_lines[:-1]
                print(C.colorize(f"  Loaded {filename} ({len(code_lines)} lines)", C.BRIGHT_GREEN))
                # Show the loaded code with syntax highlighting
                for i, code_line in enumerate(code_lines):
                    highlighted = highlight_simpl_line(code_line)
                    print(C.colorize(f"  {i+1:3d} | ", C.BRIGHT_CYAN) + highlighted)
            except Exception as e:
                print(C.colorize(f"  Error loading: {e}", C.RED))

        elif stripped == ':help':
            _show_help()

        else:
            # Regular code line - show with syntax highlighting feedback
            code_lines.append(line)
            # Echo the line back with highlighting
            highlighted = highlight_simpl_line(line)
            print(f"  {'':>3s}   {highlighted}")


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

    curl_status = "Available"
    try:
        result = subprocess.run(['curl', '--version'], capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            first_line = result.stdout.split('\n')[0]
            curl_status = f"Available ({first_line.split()[1]})"
        else:
            curl_status = "Not found"
    except Exception:
        curl_status = "Not found"

    about = f"""
{C.colorize("SimPL", C.BOLD + C.BRIGHT_CYAN)} - The Simple Programming Language
Version: {version}

A beginner-friendly programming language designed to be as readable
as English while remaining versatile enough for scripts, web projects,
and games.

{C.colorize("Features:", C.BOLD)}
  - 3 Syntax Flavors: Standard, C/JS, Python
  - 50+ Built-in Functions
  - HTTP Built-ins: get(), post() with response objects
  - JSON Built-ins: parse_json(), to_json()
  - NPM Bridge (JavaScript interop)
  - Community Package Manager
  - Smart Error Messages
  - Interactive REPL, TUI, and Studio
  - Auto-Update Checker
  - Dependency Setup & Auto-Installer

{C.colorize("Environment:", C.BOLD)}
  Platform:    {plat}
  Python:      {py_ver}
  Node.js:     {node_status}
  curl:        {curl_status}

{C.colorize("Links:", C.BOLD)}
  GitHub:  github.com/TheStrongestOfTomorrow/SimPL
  Packages: github.com/TheStrongestOfTomorrow/SimPL-Libraries

{C.colorize("Update:", C.BOLD)}
  {get_update_instructions()}

Copyright (c) 2024-2026 TheStrongestOfTomorrow
MIT License
"""
    print(draw_box("About SimPL", about))
    input(C.colorize("\n  Press Enter to continue...", C.DIM))


def action_check_updates():
    """Check for updates and show instructions."""
    C = Colors
    print()
    print(C.colorize("  Checking for updates...", C.BRIGHT_YELLOW))

    latest = check_for_updates()
    current = _get_version()

    if latest:
        print()
        print(C.colorize(f"  Update available! v{current} -> v{latest}", C.BRIGHT_GREEN + C.BOLD))
        print(C.colorize("  To update, run:", C.BRIGHT_WHITE))
        print(C.colorize(get_update_instructions(), C.BRIGHT_CYAN))
        print()
        print(C.colorize("  Or if using git clone:", C.DIM))
        simpl_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        print(C.colorize(f"    cd {simpl_dir} && git pull", C.DIM))
    else:
        print()
        print(C.colorize(f"  You are up to date! (v{current})", C.BRIGHT_GREEN))

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
    '9': action_studio,
    's': action_setup_dependencies,
    'S': action_setup_dependencies,
    'b': action_browse_packages,
    'B': action_browse_packages,
    'a': action_about,
    'A': action_about,
    'u': action_check_updates,
    'U': action_check_updates,
}


def run_tui():
    """Main TUI entry point - interactive menu loop."""
    C = Colors

    # Check for updates in background on first load
    update_available = None
    try:
        update_available = check_for_updates()
    except Exception:
        pass

    while True:
        clear_screen()
        print(draw_banner(update_available))
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
