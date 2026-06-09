"""
SimPL Package Manager

Handles installation of packages from GitHub Issues in the SimPL-Libraries repo.
Also supports the NPM Bridge: install JavaScript packages from the NPM registry
and use them inside SimPL via the js_eval() built-in function.
Supports mock mode for testing without network access.

Uses curl via subprocess for all HTTP requests (no external Python deps required).
"""

import os
import re
import json
import io
import tarfile
import subprocess
import shutil
import tempfile
from pathlib import Path

# Try to import pyyaml, fall back to regex parser if not available
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# ---------------------------------------------------------------------------
# HTTP helpers using curl (no external deps!)
# ---------------------------------------------------------------------------

class NetworkError(Exception):
    """Exception for network/HTTP errors."""
    def __init__(self, message, status_code=None):
        self.status_code = status_code
        super().__init__(message)


def _curl_get(url, timeout=15, headers=None):
    """
    Perform an HTTP GET request using curl.

    Args:
        url: The URL to fetch.
        timeout: Timeout in seconds.
        headers: Optional dict of HTTP headers.

    Returns:
        dict with 'status_code' and 'text' keys.

    Raises:
        NetworkError: If curl fails or is not installed.
    """
    cmd = ['curl', '-sS', '-w', '\n%{http_code}', '--max-time', str(timeout)]

    # Always add a User-Agent header for GitHub API compatibility
    default_headers = {
        'User-Agent': 'SimPL-Package-Manager/0.8.0',
        'Accept': 'application/vnd.github.v3+json',
    }

    # Add PAT authentication (increases API rate limit from 60/hr to 5000/hr)
    # Set SIMPL_GITHUB_PAT environment variable to your GitHub Personal Access Token
    _pat = os.environ.get('SIMPL_GITHUB_PAT', '')
    if _pat:
        default_headers['Authorization'] = f'token {_pat}'

    if headers:
        default_headers.update(headers)

    for key, value in default_headers.items():
        cmd.extend(['-H', f'{key}: {value}'])

    cmd.append(url)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 5
        )
    except FileNotFoundError:
        raise NetworkError(
            "curl is not installed. Please install curl to use package management.\n"
            "   On Ubuntu/Debian: sudo apt install curl\n"
            "   On Termux: pkg install curl\n"
            "   On macOS: brew install curl\n"
            "   On Windows: curl is included by default"
        )
    except subprocess.TimeoutExpired:
        raise NetworkError(f"Request to {url} timed out after {timeout}s")

    output = result.stdout
    # The last line is the HTTP status code (added by -w)
    parts = output.rsplit('\n', 1)
    if len(parts) == 2:
        body, status_str = parts
        try:
            status_code = int(status_str.strip())
        except ValueError:
            body = output
            status_code = 0
    else:
        body = output
        status_code = 0

    if status_code == 0:
        raise NetworkError(f"Could not connect to {url}. Check your internet connection.")

    return {'status_code': status_code, 'text': body}


def _curl_download(url, output_path, timeout=30):
    """
    Download a file using curl.

    Args:
        url: The URL to download.
        output_path: Path to save the file.
        timeout: Timeout in seconds.

    Raises:
        NetworkError: If the download fails.
    """
    cmd = ['curl', '-sS', '-L', '--max-time', str(timeout), '-o', str(output_path), url]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
        if result.returncode != 0:
            raise NetworkError(f"Failed to download from {url}: {result.stderr.strip()}")
    except FileNotFoundError:
        raise NetworkError("curl is not installed. Please install curl to download packages.")
    except subprocess.TimeoutExpired:
        raise NetworkError(f"Download from {url} timed out after {timeout}s")


# ---------------------------------------------------------------------------
# YAML / Markdown helpers
# ---------------------------------------------------------------------------

def parse_yaml_frontmatter(text):
    """
    Parse YAML frontmatter from text.
    YAML is between --- markers at the start of the text.
    Returns dict with name, version, dependencies, or empty dict on failure.
    """
    if not text.startswith('---'):
        return {}
    
    # Find the closing ---
    match = re.match(r'^---\n(.*?)\n---\n', text, re.DOTALL)
    if not match:
        return {}
    
    yaml_content = match.group(1)
    
    if HAS_YAML:
        try:
            return yaml.safe_load(yaml_content) or {}
        except Exception:
            pass
    
    # Fallback: simple regex parser for basic YAML
    result = {}
    for line in yaml_content.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Handle key: value
        kv_match = re.match(r'^(\w+):\s*(.*)$', line)
        if kv_match:
            key = kv_match.group(1)
            value = kv_match.group(2).strip()
            
            # Remove quotes if present
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            
            # Handle dependencies list (simple format: - item1, - item2)
            if key == 'dependencies':
                result[key] = []
            else:
                result[key] = value
    
    # Parse dependencies if we found the key
    if 'dependencies' in result and isinstance(result['dependencies'], str):
        # If it's a string, try to parse as inline list
        deps = result['dependencies']
        if deps.startswith('[') and deps.endswith(']'):
            deps = deps[1:-1]
            result['dependencies'] = [d.strip().strip('"\'') for d in deps.split(',') if d.strip()]
        else:
            result['dependencies'] = [deps] if deps else []
    
    return result


def extract_code_block(text, language='simpl'):
    """
    Extract code block from markdown-style fenced code.
    Looks for ```language ... ``` patterns.
    """
    pattern = rf'```{re.escape(language)}\n(.*?)```'
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Fallback: try any code block
    pattern = r'```\n(.*?)```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    return None


def get_mock_issue(package_name):
    """
    Return mock issue data for testing when GitHub API is unavailable.
    """
    mock_issues = {
        'super-math': {
            'id': 99999,
            'title': 'super-math',
            'body': '''---
name: super_math
version: 2.0.0
dependencies: []
author: SimPL Team
description: Enhanced math functions - trig, stats, rounding, and more
---

```simpl
# Super Math Library for SimPL v2.0
# Provides enhanced mathematical operations

let super_math_version = "2.0.0"

function super_math_add(a, b)
    return a + b
end

function super_math_subtract(a, b)
    return a - b
end

function super_math_multiply(a, b)
    return a * b
end

function super_math_divide(a, b)
    if b == 0 then
        print "Error: Division by zero"
        return 0
    end
    return a / b
end

function super_math_power(base, exp)
    return pow(base, exp)
end

function super_math_max(a, b)
    if a > b then
        return a
    else
        return b
    end
end

function super_math_min(a, b)
    if a < b then
        return a
    else
        return b
    end
end

function super_math_abs(n)
    return abs(n)
end

function super_math_sqrt(n)
    return sqrt(n)
end

function super_math_floor(n)
    return floor(n)
end

function super_math_ceil(n)
    return ceil(n)
end

function super_math_round(n, places)
    if places then
        return round(n, places)
    end
    return round(n)
end

function super_math_average(lst)
    let total = 0
    for n in lst do
        total = total + n
    end
    return total / len(lst)
end

function super_math_sum(lst)
    let total = 0
    for n in lst do
        total = total + n
    end
    return total
end

function super_math_median(lst)
    let sorted_list = sort(lst)
    let n = len(sorted_list)
    if n % 2 == 1 then
        let mid = floor(n / 2)
        return sorted_list[mid]
    end
    let mid = floor(n / 2)
    return (sorted_list[mid - 1] + sorted_list[mid]) / 2
end

function super_math_clamp(val, lo, hi)
    if val < lo then
        return lo
    end
    if val > hi then
        return hi
    end
    return val
end

function super_math_lerp(a, b, t)
    return a + (b - a) * t
end

function super_math_factorial(n)
    if n <= 1 then
        return 1
    end
    return n * super_math_factorial(n - 1)
end
```
'''
        },
        'string-utils': {
            'id': 99998,
            'title': 'string-utils',
            'body': '''---
name: string_utils
version: 2.0.0
dependencies: []
author: SimPL Team
description: Comprehensive string utility functions
---

```simpl
# String Utilities Library v2.0
# Provides comprehensive string operations

let string_utils_version = "2.0.0"

function string_utils_uppercase(s)
    return upper(s)
end

function string_utils_lowercase(s)
    return lower(s)
end

function string_utils_length(s)
    return len(s)
end

function string_utils_capitalize(s)
    let first = upper(slice(s, 0, 1))
    let rest = lower(slice(s, 1, len(s)))
    return first + rest
end

function string_utils_reverse(s)
    let result = ""
    let i = len(s) - 1
    while i >= 0 do
        result = result + slice(s, i, i + 1)
        let i = i - 1
    end
    return result
end

function string_utils_contains(s, sub)
    return contains(s, sub)
end

function string_utils_starts_with(s, prefix)
    return starts_with(s, prefix)
end

function string_utils_ends_with(s, suffix)
    return ends_with(s, suffix)
end

function string_utils_trim(s)
    return trim(s)
end

function string_utils_replace(s, old, new)
    return replace(s, old, new)
end

function string_utils_repeat(s, n)
    let result = ""
    repeat n times
        result = result + s
    end
    return result
end

function string_utils_word_count(s)
    let words = split(s, " ")
    return len(words)
end
```
'''
        },
        'io-utils': {
            'id': 99997,
            'title': 'io-utils',
            'body': '''---
name: io_utils
version: 1.5.0
dependencies: []
author: SimPL Team
description: File I/O utilities - read, write, exists, size, copy, lines
---

```simpl
# I/O Utilities Library v1.5
# Provides file and directory operations

let io_utils_version = "1.5.0"

function io_utils_read(path)
    return read_file(path)
end

function io_utils_write(path, content)
    return write_file(path, content)
end

function io_utils_append(path, content)
    return append_file(path, content)
end

function io_utils_read_lines(path)
    let content = read_file(path)
    return split(content, "\\n")
end

function io_utils_write_lines(path, lines)
    let content = join("\\n", lines)
    return write_file(path, content)
end

function io_utils_copy(src, dst)
    let content = read_file(src)
    return write_file(dst, content)
end

function io_utils_file_size(path)
    let content = read_file(path)
    return len(content)
end
```
'''
        },
        'list-tools': {
            'id': 99996,
            'title': 'list-tools',
            'body': '''---
name: list_tools
version: 1.5.0
dependencies: []
author: SimPL Team
description: Advanced list operations - filter, map, flatten, unique, zip
---

```simpl
# List Tools Library v1.5
# Provides advanced list manipulation functions

let list_tools_version = "1.5.0"

function list_tools_reverse(lst)
    return reverse(lst)
end

function list_tools_sort(lst)
    return sort(lst)
end

function list_tools_contains(lst, val)
    return contains(lst, val)
end

function list_tools_index_of(lst, val)
    return index_of(lst, val)
end

function list_tools_unique(lst)
    let result = []
    for item in lst do
        if not contains(result, item) then
            push(result, item)
        end
    end
    return result
end

function list_tools_flatten(lst)
    let result = []
    for item in lst do
        if type(item) == "list" then
            let inner = list_tools_flatten(item)
            for sub in inner do
                push(result, sub)
            end
        else
            push(result, item)
        end
    end
    return result
end

function list_tools_chunk(lst, size)
    let result = []
    let i = 0
    while i < len(lst) do
        let chunk = slice(lst, i, i + size)
        push(result, chunk)
        let i = i + size
    end
    return result
end

function list_tools_take(lst, n)
    return slice(lst, 0, n)
end

function list_tools_drop(lst, n)
    return slice(lst, n, len(lst))
end
```
'''
        },
        'color-kit': {
            'id': 99995,
            'title': 'color-kit',
            'body': '''---
name: color_kit
version: 1.0.0
dependencies: []
author: SimPL Team
description: Terminal color output - red, green, blue, yellow, bold, underline
---

```simpl
# Color Kit Library v1.0
# Provides terminal color output functions

let color_kit_version = "1.0.0"

function color_kit_red(text)
    return "\\033[31m" + text + "\\033[0m"
end

function color_kit_green(text)
    return "\\033[32m" + text + "\\033[0m"
end

function color_kit_yellow(text)
    return "\\033[33m" + text + "\\033[0m"
end

function color_kit_blue(text)
    return "\\033[34m" + text + "\\033[0m"
end

function color_kit_magenta(text)
    return "\\033[35m" + text + "\\033[0m"
end

function color_kit_cyan(text)
    return "\\033[36m" + text + "\\033[0m"
end

function color_kit_bold(text)
    return "\\033[1m" + text + "\\033[0m"
end

function color_kit_underline(text)
    return "\\033[4m" + text + "\\033[0m"
end

function color_kit_dim(text)
    return "\\033[2m" + text + "\\033[0m"
end

function color_kit_rainbow(text)
    let colors = ["\\033[91m", "\\033[93m", "\\033[92m", "\\033[96m", "\\033[94m", "\\033[95m"]
    let result = ""
    let i = 0
    while i < len(text) do
        let color_idx = i % len(colors)
        let ch = slice(text, i, i + 1)
        result = result + colors[color_idx] + ch + "\\033[0m"
        let i = i + 1
    end
    return result
end
```
'''
        },
        'http-client': {
            'id': 99994,
            'title': 'http-client',
            'body': '''---
name: http_client
version: 1.0.0
dependencies: []
author: SimPL Team
description: HTTP client utilities - get_json, post_json, download, api helpers
---

```simpl
# HTTP Client Library v1.0
# Provides convenient HTTP request helpers

let http_client_version = "1.0.0"

function http_client_get_json(url)
    let response = get(url)
    if response["status"] == 200 then
        return response.json()
    end
    return {}
end

function http_client_post_json(url, data)
    let response = post(url, data)
    if response["status"] == 200 then
        return response.json()
    end
    return {}
end

function http_client_is_success(response)
    let code = response["status"]
    if code >= 200 then
        if code < 300 then
            return true
        end
    end
    return false
end

function http_client_status_ok(response)
    return response["status"] == 200
end

function http_client_status_not_found(response)
    return response["status"] == 404
end
```
'''
        },
        'json-tools': {
            'id': 99993,
            'title': 'json-tools',
            'body': '''---
name: json_tools
version: 1.0.0
dependencies: []
author: SimPL Team
description: JSON manipulation utilities - merge, pretty, get_path, set_path
---

```simpl
# JSON Tools Library v1.0
# Provides JSON manipulation helpers

let json_tools_version = "1.0.0"

function json_tools_parse(text)
    return parse_json(text)
end

function json_tools_stringify(obj)
    return to_json(obj, true)
end

function json_tools_compact(obj)
    return to_json(obj, false)
end

function json_tools_get_path(obj, key)
    if has_key(obj, key) then
        return obj[key]
    end
    return null
end

function json_tools_set_path(obj, key, value)
    obj[key] = value
    return obj
end

function json_tools_merge(a, b)
    let result = {}
    let a_keys = keys(a)
    for k in a_keys do
        result[k] = a[k]
    end
    let b_keys = keys(b)
    for k in b_keys do
        result[k] = b[k]
    end
    return result
end

function json_tools_save(obj, path)
    return write_file(path, to_json(obj, true))
end

function json_tools_load(path)
    let content = read_file(path)
    return parse_json(content)
end
```
'''
        },
    }

    return mock_issues.get(package_name)


# ---------------------------------------------------------------------------
# NPM Bridge helpers
# ---------------------------------------------------------------------------

def _fetch_npm_metadata(package_name):
    """
    Fetch package metadata from the NPM registry API using curl.

    Args:
        package_name: The NPM package name (without the npm: prefix).

    Returns:
        dict with at least 'version', 'tarball', and 'main' keys, or None on 404.

    Raises:
        NetworkError: on network / HTTP errors.
    """
    registry_url = f"https://registry.npmjs.org/{package_name}/latest"
    
    try:
        response = _curl_get(registry_url, timeout=15)
    except NetworkError as e:
        raise NetworkError(f"Could not reach the NPM registry: {e}")
    
    if response['status_code'] == 404:
        return None  # Package not found
    
    if response['status_code'] != 200:
        raise NetworkError(
            f"NPM registry returned HTTP {response['status_code']} for '{package_name}'"
        )
    
    try:
        data = json.loads(response['text'])
    except json.JSONDecodeError:
        raise NetworkError(f"Invalid JSON response from NPM registry for '{package_name}'")
    
    version = data.get('version', '0.0.0')
    main_field = data.get('main', 'index.js')
    tarball_url = data.get('dist', {}).get('tarball', '')
    
    return {
        'name': data.get('name', package_name),
        'version': version,
        'main': main_field,
        'tarball': tarball_url,
        'description': data.get('description', ''),
    }


def _download_and_extract_tarball(tarball_url, package_name, main_field='index.js'):
    """
    Download an NPM .tgz tarball using curl and extract the main JS file.

    NPM tarballs always contain a top-level ``package/`` directory.  The
    *main_field* is resolved relative to that directory.

    Args:
        tarball_url: URL of the .tgz file.
        package_name: Used for the local directory name.
        main_field: The ``main`` entry from package.json (default ``index.js``).

    Returns:
        str - The extracted JavaScript source code, or None if not found.
    """
    # Download to a temp file using curl
    with tempfile.NamedTemporaryFile(suffix='.tgz', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        _curl_download(tarball_url, tmp_path, timeout=30)
    except NetworkError:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    js_code = None

    try:
        with tarfile.open(tmp_path, mode='r:gz') as tar:
            # NPM tarballs always have a 'package/' prefix
            main_path_candidates = [
                f'package/{main_field}',
                f'package/index.js',
            ]

            # Also try to read package.json to find the real main field
            pkg_json_member = None
            for member in tar.getmembers():
                if member.name == 'package/package.json':
                    pkg_json_member = member
                    break

            if pkg_json_member is not None:
                try:
                    pkg_json_file = tar.extractfile(pkg_json_member)
                    if pkg_json_file is not None:
                        pkg_json_data = json.loads(pkg_json_file.read().decode('utf-8'))
                        real_main = pkg_json_data.get('main', main_field)
                        if real_main != main_field:
                            main_path_candidates.insert(0, f'package/{real_main}')
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass

            # Try each candidate path
            for candidate in main_path_candidates:
                for member in tar.getmembers():
                    if member.name == candidate:
                        f = tar.extractfile(member)
                        if f is not None:
                            js_code = f.read().decode('utf-8', errors='replace')
                            break
                if js_code is not None:
                    break

            # If still not found, try to find *any* .js file at the root of package/
            if js_code is None:
                for member in tar.getmembers():
                    if (member.name.startswith('package/') and
                            member.name.count('/') == 1 and
                            member.name.endswith('.js') and
                            member.isfile()):
                        f = tar.extractfile(member)
                        if f is not None:
                            js_code = f.read().decode('utf-8', errors='replace')
                            break
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return js_code


def _generate_simpl_wrapper(package_name):
    """
    Generate a SimPL wrapper file that exposes the NPM package through js_eval.

    The wrapper defines a convenience function ``run_js(code)`` that delegates
    to the built-in ``js_eval(code)`` interpreter function.

    Args:
        package_name: The NPM package name (used in the function names).

    Returns:
        str - The SimPL wrapper source code.
    """
    # Sanitize the package name for use as a SimPL identifier
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', package_name)
    
    wrapper = f'''# SimPL NPM Bridge Wrapper for {package_name}
# Auto-generated by the SimPL Package Manager
# This wrapper lets you call JavaScript code from SimPL using js_eval()

# run_js: Execute arbitrary JavaScript code and return the result.
# Usage: let result = run_js("1 + 2")
function run_js(code)
    return js_eval(code)
end

# Convenience: require the NPM module and evaluate an expression.
# Usage: let result = npm_{safe_name}("require('{package_name}').someMethod()")
function npm_{safe_name}(expr)
    return js_eval(expr)
end
'''
    return wrapper


def install_npm_package(package_name):
    """
    Install an NPM package via the NPM Bridge.

    This function:
      1. Fetches metadata from the NPM registry API.
      2. Downloads the tarball (.tgz).
      3. Extracts the main JS file.
      4. Saves the JS code to ``./libs/npm_<package_name>/index.js``.
      5. Auto-generates a SimPL wrapper at ``./libs/npm_<package_name>/npm_<package_name>.simpl``.
      6. Updates ``simpl.lock``.

    Args:
        package_name: The NPM package name (without the ``npm:`` prefix).

    Returns:
        dict with installation result, or None on failure.
    """
    libs_dir = Path('./libs')
    libs_dir.mkdir(exist_ok=True)
    
    # Directory for this NPM package: libs/npm_<name>
    npm_dir_name = f'npm_{package_name}'
    npm_dir = libs_dir / npm_dir_name
    lock_file = Path('./simpl.lock')
    
    # Load existing lock file
    installed_packages = {}
    if lock_file.exists():
        try:
            with open(lock_file, 'r') as f:
                installed_packages = json.load(f)
        except (json.JSONDecodeError, IOError):
            installed_packages = {}
    
    # Check if already installed
    lock_key = f'npm:{package_name}'
    if lock_key in installed_packages:
        print(f"npm:{package_name} is already installed "
              f"(v{installed_packages[lock_key].get('version', 'unknown')})")
        print(f"   Run 'simpl uninstall npm:{package_name}' first to reinstall.")
        return None
    
    # 1. Fetch NPM metadata
    print(f"Fetching metadata for '{package_name}' from NPM registry...")
    try:
        metadata = _fetch_npm_metadata(package_name)
    except NetworkError as e:
        print(f"Error: Could not reach the NPM registry.")
        print(f"   Tip: Check your internet connection and try again.")
        print(f"   Details: {e}")
        return None
    
    if metadata is None:
        # 404 - package not found
        print(f"Error: NPM package '{package_name}' not found.")
        print(f"   Tip: Check the spelling or search npmjs.com.")
        return None
    
    version = metadata['version']
    tarball_url = metadata['tarball']
    main_field = metadata.get('main', 'index.js')
    
    if not tarball_url:
        print(f"Error: Could not find a tarball URL for '{package_name}'.")
        print(f"   Tip: The package may be empty or unpublished.")
        return None
    
    # 2. Download and extract the tarball
    print(f"Downloading {package_name}@{version}...")
    try:
        js_code = _download_and_extract_tarball(tarball_url, package_name, main_field)
    except NetworkError as e:
        print(f"Error: Failed to download tarball for '{package_name}'.")
        print(f"   Tip: Check your internet connection and try again.")
        print(f"   Details: {e}")
        return None
    
    if js_code is None:
        print(f"Error: Could not extract a main JS file from the tarball.")
        print(f"   Tip: The package may not contain a standard entry point.")
        return None
    
    # 3. Save the JS file
    npm_dir.mkdir(exist_ok=True)
    js_file = npm_dir / 'index.js'
    with open(js_file, 'w', encoding='utf-8') as f:
        f.write(js_code)
    
    # 4. Generate and save the SimPL wrapper
    wrapper_code = _generate_simpl_wrapper(package_name)
    wrapper_file = npm_dir / f'{npm_dir_name}.simpl'
    with open(wrapper_file, 'w', encoding='utf-8') as f:
        f.write(wrapper_code)
    
    # 5. Update simpl.lock
    installed_packages[lock_key] = {
        'name': package_name,
        'version': version,
        'source': 'npm',
        'main': main_field,
        'tarball': tarball_url,
        'description': metadata.get('description', ''),
        'js_path': str(js_file),
        'wrapper_path': str(wrapper_file),
    }
    
    with open(lock_file, 'w') as f:
        json.dump(installed_packages, f, indent=2)
    
    print(f"Installed npm:{package_name} (JS Bridge Active)")
    
    return {
        'name': package_name,
        'version': version,
        'js_path': str(js_file),
        'wrapper_path': str(wrapper_file),
    }


# ---------------------------------------------------------------------------
# Original install_package (SimPL-Libraries via GitHub Issues)
# ---------------------------------------------------------------------------

def install_package(package_name, repo_owner="TheStrongestOfTomorrow", repo_name="SimPL-Libraries", mock=False):
    """
    Install a package from GitHub Issues or the NPM registry.

    If the package name starts with ``npm:``, the NPM Bridge is used instead
    of the GitHub Issues flow.

    Args:
        package_name: Name of the package to install.  Prefix with ``npm:``
            to install from the NPM registry.
        repo_owner: GitHub username/organization owning the repo
        repo_name: Name of the GitHub repository
        mock: If True, use mock data instead of calling GitHub API
    
    Returns:
        dict with installation result, or None on failure
    """
    # ------------------------------------------------------------------
    # NPM Bridge: detect npm: prefix and delegate
    # ------------------------------------------------------------------
    if package_name.startswith('npm:'):
        npm_name = package_name[4:]  # Strip the 'npm:' prefix
        if not npm_name:
            print("Error: No package name specified after 'npm:'.")
            print("   Tip: Use 'simpl install npm:<package_name>' (e.g. npm:lodash).")
            return None
        return install_npm_package(npm_name)
    
    # ------------------------------------------------------------------
    # Original GitHub Issues flow
    # ------------------------------------------------------------------
    libs_dir = Path('./libs')
    libs_dir.mkdir(exist_ok=True)
    
    package_dir = libs_dir / package_name
    package_file = package_dir / f'{package_name}.simpl'
    lock_file = Path('./simpl.lock')
    
    # Load existing lock file
    installed_packages = {}
    if lock_file.exists():
        try:
            with open(lock_file, 'r') as f:
                installed_packages = json.load(f)
        except (json.JSONDecodeError, IOError):
            installed_packages = {}
    
    # Check if already installed
    if package_name in installed_packages:
        print(f"{package_name} is already installed (v{installed_packages[package_name].get('version', 'unknown')})")
        print(f"   Run 'simpl uninstall {package_name}' first to reinstall.")
        return None
    
    # Get issue data
    issue_data = None
    
    if not mock:
        try:
            # Search for open issues with matching title using curl
            search_url = (
                f"https://api.github.com/search/issues"
                f"?q=repo%3A{repo_owner}%2F{repo_name}+type%3Aissue+state%3Aopen"
                f"+%22{package_name}%22+in%3Atitle"
            )
            
            response = _curl_get(search_url, timeout=10)
            
            if response['status_code'] == 422:
                # GitHub API validation error - likely a bad query
                print(f"Warning: GitHub API returned 422. Falling back to mock mode...")
                issue_data = get_mock_issue(package_name)
                if not issue_data:
                    print(f"   No mock data available for '{package_name}'.")
                    return None
                mock = True
            elif response['status_code'] != 200:
                print(f"Warning: Could not connect to GitHub API (HTTP {response['status_code']}).")
                print("   Falling back to mock mode...")
                issue_data = get_mock_issue(package_name)
                if not issue_data:
                    print(f"   No mock data available for '{package_name}'.")
                    return None
                mock = True
            else:
                try:
                    data = json.loads(response['text'])
                except json.JSONDecodeError:
                    print("Warning: Invalid response from GitHub API. Falling back to mock mode...")
                    issue_data = get_mock_issue(package_name)
                    if not issue_data:
                        print(f"   No mock data available for '{package_name}'.")
                        return None
                    mock = True
                    data = None
                
                if data is not None:
                    if data.get('total_count', 0) == 0:
                        print(f"No package named '{package_name}' found in {repo_owner}/{repo_name}")
                        print("   Trying mock mode...")
                        issue_data = get_mock_issue(package_name)
                        if not issue_data:
                            print(f"   No mock data available for '{package_name}' either.")
                            return None
                        mock = True
                    else:
                        # Get the first matching issue
                        issue = data['items'][0]
                        issue_data = {
                            'id': issue['id'],
                            'title': issue['title'],
                            'body': issue['body']
                        }
        except NetworkError as e:
            print(f"Warning: Could not connect to GitHub API: {e}")
            print("   Falling back to mock mode...")
            issue_data = get_mock_issue(package_name)
            if not issue_data:
                print(f"   No mock data available for '{package_name}'.")
                return None
            mock = True
    else:
        issue_data = get_mock_issue(package_name)
        if not issue_data:
            print(f"No mock data available for '{package_name}'.")
            return None
    
    if mock:
        print("Using mock data for testing")
    
    # Parse the issue body
    body = issue_data['body']
    
    # Extract YAML frontmatter
    metadata = parse_yaml_frontmatter(body)
    
    if not metadata.get('name'):
        metadata['name'] = package_name
    
    version = metadata.get('version', '0.0.0')
    dependencies = metadata.get('dependencies', [])
    
    # Extract code block
    code = extract_code_block(body)
    
    if not code:
        print(f"No SimPL code block found in the issue for '{package_name}'")
        return None
    
    # Create package directory and save code
    package_dir.mkdir(exist_ok=True)
    
    with open(package_file, 'w') as f:
        f.write(code)
    
    # Update lock file
    installed_packages[package_name] = {
        'name': metadata.get('name', package_name),
        'version': version,
        'issue_id': issue_data['id'],
        'dependencies': dependencies,
        'source': f'{repo_owner}/{repo_name}',
        'mock': mock
    }
    
    with open(lock_file, 'w') as f:
        json.dump(installed_packages, f, indent=2)
    
    # Install dependencies
    if dependencies:
        print(f"Installing dependencies for {package_name}...")
        for dep in dependencies:
            dep_name = dep if isinstance(dep, str) else dep.get('name', dep)
            if dep_name and dep_name not in installed_packages:
                install_package(dep_name, repo_owner, repo_name, mock)
    
    print(f"Installed {package_name}@{version}")
    if mock:
        print("   (Mock mode - connect to GitHub for real packages)")
    
    return {
        'name': package_name,
        'version': version,
        'path': str(package_file),
        'dependencies': dependencies
    }


def uninstall_package(package_name):
    """
    Uninstall a package (works for both SimPL-Libraries and NPM packages).

    For NPM packages, the lock key is ``npm:<name>`` and the directory is
    ``./libs/npm_<name>``.

    Args:
        package_name: Name of the package to uninstall.  Can be a plain name
            (SimPL-Libraries) or ``npm:<name>`` (NPM Bridge).
    
    Returns:
        True on success, False on failure
    """
    lock_file = Path('./simpl.lock')
    
    # Determine lock key and directory based on whether this is an NPM package
    if package_name.startswith('npm:'):
        lock_key = package_name
        npm_name = package_name[4:]
        package_dir = Path('./libs') / f'npm_{npm_name}'
    else:
        lock_key = package_name
        package_dir = Path('./libs') / package_name
    
    # Load lock file
    installed_packages = {}
    if lock_file.exists():
        try:
            with open(lock_file, 'r') as f:
                installed_packages = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    if lock_key not in installed_packages:
        print(f"Package '{package_name}' is not installed")
        return False
    
    # Remove package directory
    if package_dir.exists():
        shutil.rmtree(package_dir)
    
    # Update lock file
    del installed_packages[lock_key]
    
    with open(lock_file, 'w') as f:
        json.dump(installed_packages, f, indent=2)
    
    print(f"Uninstalled {package_name}")
    return True


def list_installed_packages():
    """
    List all installed packages.
    
    Returns:
        dict of installed packages
    """
    lock_file = Path('./simpl.lock')
    
    if not lock_file.exists():
        return {}
    
    try:
        with open(lock_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def list_available_packages():
    """
    List available packages from the SimPL-Libraries registry.
    
    First tries the GitHub API, then falls back to the built-in mock catalog.
    
    Returns:
        list of dicts with 'name', 'version', 'description' keys
    """
    packages = []
    
    # Try GitHub API first
    try:
        search_url = (
            f"https://api.github.com/repos/TheStrongestOfTomorrow/SimPL-Libraries/issues"
            f"?state=open&per_page=100"
        )
        response = _curl_get(search_url, timeout=10)
        
        if response['status_code'] == 200:
            issues = json.loads(response['text'])
            for issue in issues:
                title = issue.get('title', '')
                body = issue.get('body', '') or ''
                metadata = parse_yaml_frontmatter(body)
                packages.append({
                    'name': title,
                    'version': metadata.get('version', '0.0.0'),
                    'description': metadata.get('description', ''),
                    'author': metadata.get('author', ''),
                })
            return packages
    except Exception:
        pass
    
    # Fallback: use mock catalog
    mock_catalog = {
        'super-math': {'version': '2.0.0', 'description': 'Enhanced math functions - trig, stats, rounding, and more', 'author': 'SimPL Team'},
        'string-utils': {'version': '2.0.0', 'description': 'Comprehensive string utility functions', 'author': 'SimPL Team'},
        'io-utils': {'version': '1.5.0', 'description': 'File I/O utilities - read, write, exists, size, copy, lines', 'author': 'SimPL Team'},
        'list-tools': {'version': '1.5.0', 'description': 'Advanced list operations - filter, map, flatten, unique, zip', 'author': 'SimPL Team'},
        'color-kit': {'version': '1.0.0', 'description': 'Terminal color output - red, green, blue, yellow, bold, underline', 'author': 'SimPL Team'},
        'http-client': {'version': '1.0.0', 'description': 'HTTP client utilities - get_json, post_json, download, api helpers', 'author': 'SimPL Team'},
        'json-tools': {'version': '1.0.0', 'description': 'JSON manipulation utilities - merge, pretty, get_path, set_path', 'author': 'SimPL Team'},
    }
    
    for name, info in mock_catalog.items():
        packages.append({
            'name': name,
            'version': info['version'],
            'description': info['description'],
            'author': info.get('author', ''),
        })
    
    return packages


# ---------------------------------------------------------------------------
# Auto Package Installer / Dependency Checker
# ---------------------------------------------------------------------------

def check_python_available():
    """Check if Python is available (always true since SimPL IS Python)."""
    import sys
    return True, f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def check_node_available():
    """Check if Node.js is available for NPM Bridge."""
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return True, result.stdout.strip()
    except Exception:
        pass
    return False, None


def check_curl_available():
    """Check if curl is available for HTTP and package management."""
    try:
        result = subprocess.run(['curl', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            first_line = result.stdout.split('\n')[0]
            version = first_line.split()[1] if len(first_line.split()) > 1 else 'unknown'
            return True, version
    except Exception:
        pass
    return False, None


def check_git_available():
    """Check if git is available for cloning/updating."""
    try:
        result = subprocess.run(['git', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.strip().split()[-1]
            return True, version
    except Exception:
        pass
    return False, None


def get_dependency_status():
    """
    Get the status of all SimPL dependencies.
    
    Returns:
        dict with dependency info:
          python: (available, version)
          node: (available, version)
          curl: (available, version)
          git: (available, version)
    """
    py_avail, py_ver = check_python_available()
    node_avail, node_ver = check_node_available()
    curl_avail, curl_ver = check_curl_available()
    git_avail, git_ver = check_git_available()
    
    return {
        'python': {'available': py_avail, 'version': py_ver, 'required': True, 'label': 'Python (Required)'},
        'node': {'available': node_avail, 'version': node_ver, 'required': False, 'label': 'Node.js (NPM Bridge)'},
        'curl': {'available': curl_avail, 'version': curl_ver, 'required': True, 'label': 'curl (Required)'},
        'git': {'available': git_avail, 'version': git_ver, 'required': False, 'label': 'git (Updates)'},
    }


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python package_manager.py <command> [args]")
        print("Commands:")
        print("  install <package-name>  - Install a SimPL package")
        print("  install npm:<name>      - Install an NPM package (JS Bridge)")
        print("  uninstall <package-name> - Uninstall a package")
        print("  list                    - List installed packages")
        print("  available               - List available packages")
        print("  deps                    - Check dependency status")
        print("  mock <package-name>     - Install using mock data")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'install' and len(sys.argv) >= 3:
        install_package(sys.argv[2])
    elif command == 'uninstall' and len(sys.argv) >= 3:
        uninstall_package(sys.argv[2])
    elif command == 'list':
        packages = list_installed_packages()
        if packages:
            print("Installed packages:")
            for name, info in packages.items():
                source = info.get('source', 'unknown')
                if source == 'npm':
                    source_tag = " [npm]"
                elif info.get('mock'):
                    source_tag = " (mock)"
                else:
                    source_tag = f" [{source}]" if source != 'unknown' else ""
                print(f"  - {name}@{info.get('version', 'unknown')}{source_tag}")
        else:
            print("No packages installed yet.")
    elif command == 'available':
        packages = list_available_packages()
        if packages:
            print("Available packages:")
            for pkg in packages:
                print(f"  - {pkg['name']}@{pkg['version']} - {pkg['description']}")
        else:
            print("No packages found.")
    elif command == 'deps':
        deps = get_dependency_status()
        print("SimPL Dependency Status:")
        for name, info in deps.items():
            status = "OK" if info['available'] else "MISSING"
            req = "Required" if info['required'] else "Optional"
            ver = info['version'] or 'N/A'
            print(f"  {info['label']}: {status} ({ver}) [{req}]")
    elif command == 'mock' and len(sys.argv) >= 3:
        install_package(sys.argv[2], mock=True)
    else:
        print(f"Unknown command or missing arguments: {command}")
        sys.exit(1)
