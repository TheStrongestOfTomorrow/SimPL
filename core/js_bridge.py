"""
SimPL JS Bridge - Execute JavaScript from SimPL

This module provides the ``js_eval`` built-in function that allows SimPL
programs to execute JavaScript code via Node.js and capture the result.

How it works:
    1. SimPL code calls ``js_eval("some JS expression")``.
    2. The function spawns a ``node -e`` subprocess that evaluates the
       expression and prints the result to stdout.
    3. The stdout is captured, parsed, and returned as a native SimPL
       value (string, number, or dict/list via JSON).

Requirements:
    - Node.js must be installed and available on the system PATH.
    - If Node.js is not found, a friendly error message is printed.
"""

import json
import subprocess
import shlex
import os
import sys
from typing import Any, Optional, Union


class JSBridgeError(Exception):
    """Exception raised for JS Bridge errors."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _find_node() -> Optional[str]:
    """
    Locate the Node.js executable on the system.

    Returns:
        The path to the ``node`` binary, or None if not found.
    """
    # Common names for the Node.js executable
    candidates = ['node', 'nodejs']
    
    for candidate in candidates:
        try:
            result = subprocess.run(
                [candidate, '--version'],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return candidate
        except FileNotFoundError:
            continue
        except (subprocess.TimeoutExpired, OSError):
            continue
    
    return None


def _parse_js_output(raw: str) -> Any:
    """
    Parse the raw stdout from a Node.js evaluation into a Python value.

    The function tries the following strategies in order:
      1. Parse as JSON (handles numbers, booleans, null, arrays, objects).
      2. Try to interpret as an integer.
      3. Try to interpret as a float.
      4. Fall back to a stripped string.

    Args:
        raw: The raw stdout string from the Node.js process.

    Returns:
        A Python value (int, float, str, list, dict, bool, or None).
    """
    raw = raw.strip()
    
    if not raw:
        return ''
    
    # 1. Try JSON parse (handles numbers, bools, null, arrays, objects)
    try:
        value = json.loads(raw)
        return value
    except (json.JSONDecodeError, ValueError):
        pass
    
    # 2. Try integer
    try:
        return int(raw)
    except ValueError:
        pass
    
    # 3. Try float
    try:
        return float(raw)
    except ValueError:
        pass
    
    # 4. Return as string
    return raw


def js_eval(js_code: str, node_modules_path: Optional[str] = None) -> Any:
    """
    Evaluate a JavaScript code string using Node.js and return the result.

    The JavaScript code is wrapped inside ``console.log(eval(...))`` so that
    the result of the expression is printed to stdout.  If the code contains
    ``require()`` calls, the ``NODE_PATH`` environment variable is set so
    that NPM packages installed by the SimPL package manager (under
    ``./libs/``) can be resolved.

    Args:
        js_code: A string of JavaScript code to evaluate.
        node_modules_path: Optional path to add to NODE_PATH for require()
            resolution.  Defaults to ``./libs/`` if not specified.

    Returns:
        The result of evaluating the JavaScript code, converted to a native
        Python type (int, float, str, list, dict, bool, or None).

    Raises:
        JSEvalError: If Node.js is not installed, if the JS code raises an
            error, or if the subprocess fails.
    """
    # 1. Check that Node.js is available
    node_bin = _find_node()
    if node_bin is None:
        raise JSBridgeError(
            "🛑 Error: NPM Bridge requires Node.js to be installed. "
            "💡 Tip: Download it from nodejs.org to use JS libraries!"
        )
    
    # 2. Build the NODE_PATH so require() can find installed NPM packages
    if node_modules_path is None:
        # Default: look in ./libs/ for npm_<package>/ directories
        # Each such directory has an index.js that Node can require.
        libs_dir = os.path.abspath('./libs')
        node_modules_path = libs_dir
    
    env = os.environ.copy()
    existing_node_path = env.get('NODE_PATH', '')
    if node_modules_path:
        if existing_node_path:
            env['NODE_PATH'] = f"{node_modules_path}{os.pathsep}{existing_node_path}"
        else:
            env['NODE_PATH'] = node_modules_path
    
    # 3. Build the Node.js command
    #    We use JSON.stringify inside Node to safely serialize the result.
    #    This ensures numbers stay numbers and objects stay objects.
    #
    #    The approach: wrap the user code in an IIFE so that:
    #      - The result is captured
    #      - It is JSON.stringified for clean parsing
    #      - If it fails, stderr is captured
    #
    #    We use subprocess with a heredoc-like approach via -e flag.
    
    # Escape single quotes in the JS code to safely embed it
    # We use double quotes for the outer JS string and escape internal ones
    escaped_code = js_code.replace('\\', '\\\\').replace("'", "\\'")
    
    node_script = (
        "try {"
        f"  var __result = eval('{escaped_code}');"
        "  if (typeof __result === 'object' && __result !== null) {"
        "    console.log(JSON.stringify(__result));"
        "  } else {"
        "    console.log(__result);"
        "  }"
        "} catch(__e) {"
        "  console.error(__e.message);"
        "  process.exit(1);"
        "}"
    )
    
    try:
        result = subprocess.run(
            [node_bin, '-e', node_script],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
    except FileNotFoundError:
        raise JSBridgeError(
            "🛑 Error: NPM Bridge requires Node.js to be installed. "
            "💡 Tip: Download it from nodejs.org to use JS libraries!"
        )
    except subprocess.TimeoutExpired:
        raise JSBridgeError(
            "🛑 Error: JavaScript execution timed out (30s limit). "
            "💡 Tip: Your JS code may have an infinite loop."
        )
    
    # 4. Check for errors
    if result.returncode != 0:
        error_msg = result.stderr.strip() if result.stderr else "Unknown JS error"
        raise JSBridgeError(
            f"🛑 JS Error: {error_msg}"
        )
    
    # 5. Parse the output
    raw_output = result.stdout
    return _parse_js_output(raw_output)


def js_eval_with_require(js_code: str, package_name: str) -> Any:
    """
    Evaluate JavaScript that requires an NPM package installed via the bridge.

    This is a convenience wrapper around :func:`js_eval` that automatically
    sets up the require path for an NPM package installed by SimPL.

    The installed package's JS file lives at
    ``./libs/npm_<package_name>/index.js``, so the require expression is
    constructed to point there.

    Args:
        js_code: JavaScript code to evaluate.  The variable ``pkg`` is
            pre-bound to ``require('./libs/npm_<package_name>/index.js')``
            so the code can reference it.
        package_name: The NPM package name (without ``npm:`` prefix).

    Returns:
        The result of evaluating the JavaScript code.
    """
    libs_dir = os.path.abspath('./libs')
    package_dir = os.path.join(libs_dir, f'npm_{package_name}')
    
    # Build a script that pre-requires the package
    require_stmt = f"var pkg = require('{package_dir}/index.js');"
    full_code = f"{require_stmt} {js_code}"
    
    return js_eval(full_code, node_modules_path=libs_dir)


def is_node_available() -> bool:
    """
    Check if Node.js is available on the system.

    Returns:
        True if Node.js is found, False otherwise.
    """
    return _find_node() is not None


def get_node_version() -> Optional[str]:
    """
    Get the installed Node.js version string.

    Returns:
        The version string (e.g. 'v18.17.0'), or None if Node.js is not found.
    """
    node_bin = _find_node()
    if node_bin is None:
        return None
    
    try:
        result = subprocess.run(
            [node_bin, '--version'],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        pass
    
    return None


# ---------------------------------------------------------------------------
# Module-level test
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print("=== SimPL JS Bridge Test ===\n")
    
    # Check if Node.js is available
    if is_node_available():
        print(f"Node.js found: {get_node_version()}")
        
        # Test simple evaluation
        print("\n--- Test 1: Simple math ---")
        result = js_eval("1 + 2")
        print(f"js_eval('1 + 2') = {result!r} (type: {type(result).__name__})")
        
        # Test string result
        print("\n--- Test 2: String result ---")
        result = js_eval("'Hello from JS!'")
        print(f"js_eval(\"'Hello from JS!'\") = {result!r}")
        
        # Test JSON object
        print("\n--- Test 3: JSON object ---")
        result = js_eval("({name: 'SimPL', version: 1})")
        print(f"js_eval('({{name: \"SimPL\", version: 1}})') = {result!r}")
        
        # Test array
        print("\n--- Test 4: Array ---")
        result = js_eval("[1, 2, 3]")
        print(f"js_eval('[1, 2, 3]') = {result!r}")
        
        # Test error handling
        print("\n--- Test 5: Error handling ---")
        try:
            js_eval("undefined_var")
        except JSBridgeError as e:
            print(f"Caught expected error: {e.message}")
        
    else:
        print("Node.js is NOT installed!")
        print("The NPM Bridge requires Node.js to execute JavaScript.")
        print("Download it from: https://nodejs.org")
