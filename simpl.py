#!/usr/bin/env python3
"""
SimPL - Main Entry Point and CLI Runner

This is the main entry point for the SimPL interpreter.
It provides a command-line interface for running SimPL scripts.

Usage:
    python simpl.py <script.simpl>          # Run a script
    python simpl.py --help                   # Show help
    python simpl.py --version                # Show version
    python simpl.py --check <script.simpl>   # Check for errors without running
    python simpl.py --tokens <script.simpl>  # Show tokens from lexer
"""

import sys
import os
import argparse

# Add the current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.lexer import Lexer, tokenize
from core.parser import Parser, Interpreter, parse_and_execute, ParseError, RuntimeError as SimPLRuntimeError
from core.helper import SmartHelper, handle_error, get_helper


VERSION = "0.1.0"


def load_source_file(filepath: str) -> str:
    """Load source code from a file."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Script file not found: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


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
Examples:
  python simpl.py hello.simpl           Run a script
  python simpl.py --check hello.simpl   Check for errors
  python simpl.py --tokens hello.simpl  Show tokens
  python simpl.py --repl                Interactive mode
        """
    )
    
    parser.add_argument(
        'script',
        nargs='?',
        help='SimPL script file to run'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version=f'SimPL v{VERSION}'
    )
    
    parser.add_argument(
        '--check',
        action='store_true',
        help='Check script for errors without running'
    )
    
    parser.add_argument(
        '--tokens',
        action='store_true',
        help='Show tokens from the lexer'
    )
    
    parser.add_argument(
        '--repl',
        action='store_true',
        help='Run in interactive REPL mode'
    )
    
    args = parser.parse_args()
    
    # REPL mode
    if args.repl:
        repl_mode()
        return 0
    
    # Need a script file for other modes
    if not args.script:
        parser.print_help()
        return 0
    
    # Load the script
    try:
        source = load_source_file(args.script)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    
    # Check mode
    if args.check:
        return check_script(source)
    
    # Run mode (default)
    return run_script(source, show_tokens=args.tokens)


if __name__ == '__main__':
    sys.exit(main())
