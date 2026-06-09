#!/usr/bin/env python3
"""
SimPL - Main Entry Point and CLI Runner

This is the main entry point for the SimPL interpreter.
It provides a command-line interface for running SimPL scripts,
installing packages, and managing the SimPL environment.

Usage:
    simpl                              Launch the TUI (default when no args)
    simpl run <script.simpl>           Run a script
    simpl install <package-name>       Install a package
    simpl uninstall <package-name>     Uninstall a package
    simpl list                         List installed packages
    simpl --help                       Show help
    simpl --version                    Show version
    simpl --check <script.simpl>       Check for errors without running
    simpl --tokens <script.simpl>      Show tokens from lexer
    simpl --repl                       Run in interactive REPL mode
    simpl --tui                        Launch Terminal User Interface
"""

import sys
import os
import argparse

# Add the current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.lexer import Lexer, tokenize, MixedFlavorError
from core.parser import Parser, Interpreter, parse_and_execute, ParseError, RuntimeError as SimPLRuntimeError
from core.helper import SmartHelper, handle_error, get_helper
from package_manager import install_package, uninstall_package, list_installed_packages


VERSION = "0.5.0"


def load_source_file(filepath: str) -> str:
    """Load source code from a file."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Script file not found: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def resolve_imports(source: str, libs_dir: str = './libs') -> str:
    """
    Pre-process source code to resolve import statements.
    Replaces 'import <package>' with the contents of the package file.
    Also handles 'import npm:<package>' for NPM Bridge packages.

    Args:
        source: The source code with import statements.
        libs_dir: Directory where installed packages are stored.

    Returns:
        Source code with imports resolved.
    """
    import re

    lines = source.split('\n')
    resolved_lines = []
    imported_packages = set()

    for line in lines:
        stripped = line.strip()

        # Check for NPM import statement: import npm:<package-name>
        npm_import_match = re.match(r'^import\s+npm:([a-zA-Z0-9_][a-zA-Z0-9_.-]*)\s*$', stripped)

        if npm_import_match:
            npm_name = npm_import_match.group(1)
            package_key = f'npm:{npm_name}'

            if package_key in imported_packages:
                # Skip duplicate imports
                continue

            imported_packages.add(package_key)

            # Look for the NPM wrapper file: libs/npm_<name>/npm_<name>.simpl
            npm_dir_name = f'npm_{npm_name}'
            wrapper_file = os.path.join(libs_dir, npm_dir_name, f'{npm_dir_name}.simpl')

            if os.path.exists(wrapper_file):
                try:
                    with open(wrapper_file, 'r', encoding='utf-8') as f:
                        wrapper_code = f.read()

                    resolved_lines.append(f'# === Imported NPM: {npm_name} ===')
                    resolved_lines.extend(wrapper_code.split('\n'))
                    resolved_lines.append(f'# === End NPM: {npm_name} ===')
                except Exception as e:
                    print(f"Warning: Could not load NPM wrapper for '{npm_name}': {e}")
            else:
                print(f"Error: NPM package '{npm_name}' is not installed.")
                print(f"   Tip: Run 'simpl install npm:{npm_name}' to install it.")
                resolved_lines.append(line)
            continue

        # Check for regular import statement: import <package-name>
        import_match = re.match(r'^import\s+([a-zA-Z][a-zA-Z0-9_-]*)\s*$', stripped)

        if import_match:
            package_name = import_match.group(1)

            if package_name in imported_packages:
                # Skip duplicate imports
                continue

            imported_packages.add(package_name)

            # Look for the package file
            package_file = os.path.join(libs_dir, package_name, f'{package_name}.simpl')

            if os.path.exists(package_file):
                try:
                    with open(package_file, 'r', encoding='utf-8') as f:
                        package_code = f.read()

                    # Add a comment marker and the package code
                    resolved_lines.append(f'# === Imported: {package_name} ===')
                    resolved_lines.extend(package_code.split('\n'))
                    resolved_lines.append(f'# === End: {package_name} ===')
                except Exception as e:
                    print(f"Warning: Could not load package '{package_name}': {e}")
            else:
                print(f"Error: Package '{package_name}' is not installed.")
                print(f"   Tip: Run 'simpl install {package_name}' to install it.")
                # We'll let the parser handle this as an undefined variable error
                # Just keep the import line as-is for now
                resolved_lines.append(line)
        else:
            resolved_lines.append(line)

    return '\n'.join(resolved_lines)


def run_script(source: str, show_tokens: bool = False) -> int:
    """
    Run a SimPL script.

    Args:
        source: The source code to execute.
        show_tokens: If True, display tokens before execution.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    helper = get_helper()

    try:
        # Resolve imports first
        source = resolve_imports(source)

        # Optional: Show tokens for debugging
        if show_tokens:
            print("=== Tokens ===")
            lexer = Lexer(source)
            tokens = lexer.tokenize()
            for token in tokens:
                print(f"  {token}")
            print()

        # Parse and execute
        output = parse_and_execute(source)

        # Print output
        for line in output:
            print(line)

        return 0

    except MixedFlavorError as e:
        # Handle mixed flavor errors
        print(str(e))
        return 1

    except ParseError as e:
        print(handle_error(e, source))
        return 1

    except SimPLRuntimeError as e:
        print(handle_error(e, source, getattr(e, 'line', None)))
        return 1

    except Exception as e:
        print(handle_error(e, source))
        return 1


def check_script(source: str) -> int:
    """
    Check a SimPL script for errors without executing.

    Args:
        source: The source code to check.

    Returns:
        Exit code (0 for no errors, 1 for errors).
    """
    helper = get_helper()
    has_errors = False

    # Resolve imports first (with libs dir)
    try:
        source = resolve_imports(source)
    except Exception as e:
        print(f"Error resolving imports: {e}")
        return 1

    # Check for common mistakes proactively
    issues = helper.check_common_mistakes(source)

    if issues:
        print("Potential issues found:")
        print()
        for issue in issues:
            print(f"  Line {issue['line']}: {issue['message']}")
            print(f"     {issue['tip']}")
            print()
        has_errors = True

    # Try to parse
    try:
        lexer = Lexer(source)
        tokens = lexer.tokenize()

        parser = Parser(tokens)
        ast = parser.parse()

        if not has_errors:
            print("No syntax errors found!")
            print(f"  Parsed {len(ast.statements)} statement(s)")

    except ParseError as e:
        print(handle_error(e, source))
        has_errors = True

    return 1 if has_errors else 0


def repl_mode():
    """Run SimPL in REPL (Read-Eval-Print Loop) mode."""
    print(f"SimPL Interactive v{VERSION}")
    print("Type 'exit' or 'quit' to exit, 'help' for help.")
    print()

    interpreter = Interpreter()
    helper = get_helper()

    while True:
        try:
            line = input("simpl> ").strip()

            if not line:
                continue

            if line.lower() in ('exit', 'quit'):
                print("Goodbye!")
                break

            if line.lower() == 'help':
                print("SimPL Interactive Help:")
                print("  let x = 10         - Define a variable")
                print("  print x            - Print a value")
                print("  if x > 5 then ... end  - Conditional")
                print("  while x > 0 do ... end - Loop")
                print("  function f(x) ... end  - Define function")
                print("  js_eval('1+2')     - NPM Bridge")
                print("  exit               - Exit REPL")
                print()
                continue

            # For REPL, we need to handle single expressions vs statements
            source = line

            # Try to execute
            output = parse_and_execute(source)
            for result in output:
                print(result)

        except KeyboardInterrupt:
            print("\nUse 'exit' to quit.")
        except Exception as e:
            print(handle_error(e, line))


def tui_mode():
    """Launch the SimPL TUI (Terminal User Interface)."""
    from core.tui import run_tui
    run_tui()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="SimPL - The Simple Programming Language",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  run <script.simpl>              Run a SimPL script
  install <package-name>          Install a SimPL package from GitHub Issues
  install npm:<package-name>      Install an NPM package (JS Bridge)
  uninstall <package-name>        Uninstall a package
  list                            List installed packages

Options:
  --check <script.simpl>          Check script for errors without running
  --tokens <script.simpl>         Show tokens from the lexer
  --repl                          Run in interactive REPL mode
  --tui                           Launch Terminal User Interface
  --version                       Show version
  --help                          Show this help message

Examples:
  simpl                           Launch TUI (default)
  simpl run hello.simpl           Run a script
  simpl install super-math        Install a SimPL package
  simpl install npm:lodash        Install an NPM package (JS Bridge)
  simpl --check hello.simpl       Check for errors
  simpl --repl                    Interactive mode

Syntax Flavors:
  Standard:  if x > 5 then ... end
  C/JS:      if (x > 5) { ... }
  Python:    if x > 5: (indent-based)
        """
    )

    parser.add_argument(
        'command',
        nargs='?',
        choices=['run', 'install', 'uninstall', 'list'],
        help='Command to execute'
    )

    parser.add_argument(
        'target',
        nargs='?',
        help='Target (script file or package name)'
    )

    parser.add_argument(
        '--version', '-v',
        action='version',
        version=f'SimPL v{VERSION}'
    )

    parser.add_argument(
        '--check',
        metavar='SCRIPT',
        help='Check script for errors without running'
    )

    parser.add_argument(
        '--tokens',
        metavar='SCRIPT',
        help='Show tokens from the lexer'
    )

    parser.add_argument(
        '--repl',
        action='store_true',
        help='Run in interactive REPL mode'
    )

    parser.add_argument(
        '--tui',
        action='store_true',
        help='Launch Terminal User Interface'
    )

    parser.add_argument(
        '--mock',
        action='store_true',
        help='Use mock data for package installation (for testing)'
    )

    args = parser.parse_args()

    # Handle --check option (legacy compatibility)
    if args.check:
        try:
            source = load_source_file(args.check)
            return check_script(source)
        except FileNotFoundError as e:
            print(f"Error: {e}")
            return 1

    # Handle --tokens option (legacy compatibility)
    if args.tokens:
        try:
            source = load_source_file(args.tokens)
            return run_script(source, show_tokens=True)
        except FileNotFoundError as e:
            print(f"Error: {e}")
            return 1

    # REPL mode
    if args.repl:
        repl_mode()
        return 0

    # TUI mode (explicit)
    if args.tui:
        tui_mode()
        return 0

    # No command provided — launch TUI by default
    if not args.command:
        # If stdin is a TTY (interactive), launch TUI
        # Otherwise show help
        if sys.stdin.isatty():
            tui_mode()
        else:
            parser.print_help()
        return 0

    # Handle commands
    if args.command == 'run':
        if not args.target:
            print("Error: 'run' command requires a script file argument")
            print("Usage: simpl run <script.simpl>")
            return 1

        try:
            source = load_source_file(args.target)
        except FileNotFoundError as e:
            print(f"Error: {e}")
            return 1

        return run_script(source)

    elif args.command == 'install':
        if not args.target:
            print("Error: 'install' command requires a package name argument")
            print("Usage: simpl install <package-name>")
            return 1

        # install_package handles the npm: prefix internally via the NPM Bridge
        result = install_package(args.target, mock=args.mock)
        return 0 if result else 1

    elif args.command == 'uninstall':
        if not args.target:
            print("Error: 'uninstall' command requires a package name argument")
            print("Usage: simpl uninstall <package-name>")
            return 1

        return 0 if uninstall_package(args.target) else 1

    elif args.command == 'list':
        packages = list_installed_packages()
        if packages:
            print("Installed packages:")
            for name, info in packages.items():
                mock_tag = " (mock)" if info.get('mock') else ""
                source_tag = f" [{info.get('source', 'unknown')}]" if info.get('source') else ""
                print(f"  - {name}@{info.get('version', 'unknown')}{mock_tag}{source_tag}")
        else:
            print("No packages installed yet.")
            print("Install a package with: simpl install <package-name>")
        return 0

    return 0


if __name__ == '__main__':
    sys.exit(main())
