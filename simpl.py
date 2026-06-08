#!/usr/bin/env python3
"""
SimPL - Main Entry Point and CLI Runner

This is the main entry point for the SimPL interpreter.
It provides a command-line interface for running SimPL scripts,
installing packages, and managing the SimPL environment.

Usage:
    python simpl.py run <script.simpl>          # Run a script
    python simpl.py install <package-name>      # Install a package
    python simpl.py uninstall <package-name>    # Uninstall a package
    python simpl.py list                        # List installed packages
    python simpl.py --help                      # Show help
    python simpl.py --version                   # Show version
    python simpl.py --check <script.simpl>      # Check for errors without running
    python simpl.py --tokens <script.simpl>     # Show tokens from lexer
"""

import sys
import os
import argparse

# Add the current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.lexer import Lexer, tokenize
from core.parser import Parser, Interpreter, parse_and_execute, ParseError, RuntimeError as SimPLRuntimeError
from core.helper import SmartHelper, handle_error, get_helper
from package_manager import install_package, uninstall_package, list_installed_packages


VERSION = "0.2.0"


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
        
        # Check for import statement: import <package-name>
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
                    print(f"⚠️  Warning: Could not load package '{package_name}': {e}")
            else:
                print(f"🛑 Error: Package '{package_name}' is not installed.")
                print(f"   💡 Tip: Run 'python simpl.py install {package_name}' to install it.")
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
        
    except ParseError as e:
        # Handle parser errors with friendly messages
        print(handle_error(e, source))
        return 1
        
    except SimPLRuntimeError as e:
        # Handle runtime errors with friendly messages
        print(handle_error(e, source, getattr(e, 'line', None)))
        return 1
        
    except Exception as e:
        # Handle unexpected errors
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
        print(f"🛑 Error resolving imports: {e}")
        return 1
    
    # Check for common mistakes proactively
    issues = helper.check_common_mistakes(source)
    
    if issues:
        print("⚠️  Potential issues found:")
        print()
        for issue in issues:
            print(f"  Line {issue['line']}: {issue['message']}")
            print(f"     💡 {issue['tip']}")
            print()
        has_errors = True
    
    # Try to parse
    try:
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        
        parser = Parser(tokens)
        ast = parser.parse()
        
        if not has_errors:
            print("✓ No syntax errors found!")
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
                print("  let x = 10       - Define a variable")
                print("  print x          - Print a value")
                print("  if x > 5 then ... end  - Conditional")
                print("  while x > 0 do ... end - Loop")
                print("  exit             - Exit REPL")
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


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="SimPL - The Simple Programming Language",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  run <script.simpl>              Run a SimPL script
  install <package-name>          Install a package from GitHub Issues
  uninstall <package-name>        Uninstall a package
  list                            List installed packages
  
Options:
  --check <script.simpl>          Check script for errors without running
  --tokens <script.simpl>         Show tokens from the lexer
  --repl                          Run in interactive REPL mode
  --version                       Show version
  --help                          Show this help message

Examples:
  python simpl.py run hello.simpl           Run a script
  python simpl.py install super-math        Install a package
  python simpl.py --check hello.simpl       Check for errors
  python simpl.py --repl                    Interactive mode
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
    
    # No command provided
    if not args.command:
        parser.print_help()
        return 0
    
    # Handle commands
    if args.command == 'run':
        if not args.target:
            print("Error: 'run' command requires a script file argument")
            print("Usage: python simpl.py run <script.simpl>")
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
            print("Usage: python simpl.py install <package-name>")
            return 1
        
        # Check for npm: prefix (future feature placeholder)
        if args.target.startswith('npm:'):
            package_name = args.target[4:]
            print(f"⚠️  NPM bridge is not yet implemented.")
            print(f"   Requested package: {package_name}")
            print(f"   This will be available in a future version.")
            return 1
        
        return 0 if install_package(args.target, mock=args.mock) else 1
    
    elif args.command == 'uninstall':
        if not args.target:
            print("Error: 'uninstall' command requires a package name argument")
            print("Usage: python simpl.py uninstall <package-name>")
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
            print("Install a package with: python simpl.py install <package-name>")
        return 0
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
