"""
SimPL Package Manager

Handles installation of packages from GitHub Issues in the SimPL-Libraries repo.
Also supports the NPM Bridge: install JavaScript packages from the NPM registry
and use them inside SimPL via the js_eval() built-in function.
Supports mock mode for testing without network access.
"""

import os
import re
import json
import io
import tarfile
import requests
from pathlib import Path

# Try to import pyyaml, fall back to regex parser if not available
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# ---------------------------------------------------------------------------
# YAML / Markdown helpers (unchanged)
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
name: super-math
version: 1.0.0
dependencies: []
author: SimPL Team
description: Enhanced math functions for SimPL
---

```simpl
# Super Math Library for SimPL
# Provides enhanced mathematical operations

let super-math.version = "1.0.0"

function super-math.add(a, b)
    return a + b
end

function super-math.subtract(a, b)
    return a - b
end

function super-math.multiply(a, b)
    return a * b
end

function super-math.divide(a, b)
    if b == 0 then
        print "Error: Division by zero"
        return 0
    end
    return a / b
end

function super-math.power(base, exp)
    let result = 1
    repeat exp times
        result = result * base
    end
    return result
end

function super-math.max(a, b)
    if a > b then
        return a
    else
        return b
    end
end

function super-math.min(a, b)
    if a < b then
        return a
    else
        return b
    end
end
```
'''
        },
        'string-utils': {
            'id': 99998,
            'title': 'string-utils',
            'body': '''---
name: string-utils
version: 0.5.0
dependencies: []
---

```simpl
# String Utilities Library

function string-utils.uppercase(str)
    # Placeholder - would need actual implementation
    return str
end

function string-utils.lowercase(str)
    return str
end

function string-utils.length(str)
    return 0
end
```
'''
        }
    }
    
    return mock_issues.get(package_name)


# ---------------------------------------------------------------------------
# NPM Bridge helpers
# ---------------------------------------------------------------------------

def _fetch_npm_metadata(package_name):
    """
    Fetch package metadata from the NPM registry API.

    Args:
        package_name: The NPM package name (without the npm: prefix).

    Returns:
        dict with at least 'version', 'tarball', and 'main' keys.

    Raises:
        requests.HTTPError: on network / HTTP errors (including 404).
    """
    registry_url = f"https://registry.npmjs.org/{package_name}/latest"
    response = requests.get(registry_url, timeout=15)
    
    if response.status_code == 404:
        return None  # Signal: package not found
    
    response.raise_for_status()
    data = response.json()
    
    version = data.get('version', '0.0.0')
    main_field = data.get('main', 'index.js')
    # The tarball URL lives under dist.tarball
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
    Download an NPM .tgz tarball and extract the main JS file.

    NPM tarballs always contain a top-level ``package/`` directory.  The
    *main_field* is resolved relative to that directory.

    Args:
        tarball_url: URL of the .tgz file.
        package_name: Used for the local directory name.
        main_field: The ``main`` entry from package.json (default ``index.js``).

    Returns:
        str - The extracted JavaScript source code.
    """
    response = requests.get(tarball_url, timeout=30, stream=True)
    response.raise_for_status()
    
    # Read the whole body into a BytesIO so tarfile can seek
    tgz_bytes = io.BytesIO(response.content)
    
    js_code = None
    
    with tarfile.open(fileobj=tgz_bytes, mode='r:gz') as tar:
        # NPM tarballs always have a 'package/' prefix
        # Build the expected path inside the tarball
        main_path_candidates = [
            f'package/{main_field}',
            f'package/index.js',       # fallback
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
                    # Prepend candidates with the real main from package.json
                    if real_main != main_field:
                        main_path_candidates.insert(0, f'package/{real_main}')
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass  # Fall through to existing candidates
        
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
        print(f"⚠️  npm:{package_name} is already installed "
              f"(v{installed_packages[lock_key].get('version', 'unknown')})")
        print("   Run 'simpl uninstall npm:{}' first to reinstall.".format(package_name))
        return None
    
    # 1. Fetch NPM metadata
    print(f"📦 Fetching metadata for '{package_name}' from NPM registry...")
    try:
        metadata = _fetch_npm_metadata(package_name)
    except requests.RequestException as e:
        print(f"🛑 Error: Could not reach the NPM registry.")
        print(f"   💡 Tip: Check your internet connection and try again.")
        print(f"   Details: {e}")
        return None
    
    if metadata is None:
        # 404 - package not found
        print(f"🛑 Error: NPM package '{package_name}' not found.")
        print(f"   💡 Tip: Check the spelling or search npmjs.com.")
        return None
    
    version = metadata['version']
    tarball_url = metadata['tarball']
    main_field = metadata.get('main', 'index.js')
    
    if not tarball_url:
        print(f"🛑 Error: Could not find a tarball URL for '{package_name}'.")
        print(f"   💡 Tip: The package may be empty or unpublished.")
        return None
    
    # 2. Download and extract the tarball
    print(f"📦 Downloading {package_name}@{version}...")
    try:
        js_code = _download_and_extract_tarball(tarball_url, package_name, main_field)
    except requests.RequestException as e:
        print(f"🛑 Error: Failed to download tarball for '{package_name}'.")
        print(f"   💡 Tip: Check your internet connection and try again.")
        print(f"   Details: {e}")
        return None
    
    if js_code is None:
        print(f"🛑 Error: Could not extract a main JS file from the tarball.")
        print(f"   💡 Tip: The package may not contain a standard entry point.")
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
    
    print(f"✅ Installed npm:{package_name} (JS Bridge Active)")
    
    return {
        'name': package_name,
        'version': version,
        'js_path': str(js_file),
        'wrapper_path': str(wrapper_file),
    }


# ---------------------------------------------------------------------------
# Original install_package (SimPL-Libraries via GitHub Issues)
# ---------------------------------------------------------------------------

def install_package(package_name, repo_owner="SimPL-Language", repo_name="SimPL-Libraries", mock=False):
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
            print("🛑 Error: No package name specified after 'npm:'.")
            print("   💡 Tip: Use 'simpl install npm:<package_name>' (e.g. npm:lodash).")
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
        print(f"⚠️  {package_name} is already installed (v{installed_packages[package_name].get('version', 'unknown')})")
        print("   Run 'simpl uninstall {package_name}' first to reinstall.")
        return None
    
    # Get issue data
    issue_data = None
    
    if not mock:
        try:
            # Search for open issues with matching title
            search_url = f"https://api.github.com/search/issues"
            params = {
                'q': f'repo:{repo_owner}/{repo_name} type:issue state:open "{package_name}" in:title'
            }
            
            response = requests.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('total_count', 0) == 0:
                print(f"❌ No package named '{package_name}' found in {repo_owner}/{repo_name}")
                print("   Trying mock mode...")
                issue_data = get_mock_issue(package_name)
                if not issue_data:
                    print(f"   No mock data available for '{package_name}' either.")
                    return None
                mock = True  # Switch to mock mode
            else:
                # Get the first matching issue
                issue = data['items'][0]
                issue_data = {
                    'id': issue['id'],
                    'title': issue['title'],
                    'body': issue['body']
                }
        except requests.RequestException as e:
            print(f"⚠️  Could not connect to GitHub API: {e}")
            print("   Falling back to mock mode...")
            issue_data = get_mock_issue(package_name)
            if not issue_data:
                print(f"   No mock data available for '{package_name}'.")
                return None
            mock = True
    else:
        issue_data = get_mock_issue(package_name)
        if not issue_data:
            print(f"❌ No mock data available for '{package_name}'.")
            return None
    
    if mock:
        print("📦 Using mock data for testing")
    
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
        print(f"❌ No SimPL code block found in the issue for '{package_name}'")
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
        print(f"📦 Installing dependencies for {package_name}...")
        for dep in dependencies:
            dep_name = dep if isinstance(dep, str) else dep.get('name', dep)
            if dep_name and dep_name not in installed_packages:
                install_package(dep_name, repo_owner, repo_name, mock)
    
    print(f"✅ Installed {package_name}@{version}")
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
        print(f"❌ Package '{package_name}' is not installed")
        return False
    
    # Remove package directory
    if package_dir.exists():
        import shutil
        shutil.rmtree(package_dir)
    
    # Update lock file
    del installed_packages[lock_key]
    
    with open(lock_file, 'w') as f:
        json.dump(installed_packages, f, indent=2)
    
    print(f"✅ Uninstalled {package_name}")
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


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python package_manager.py <command> [args]")
        print("Commands:")
        print("  install <package-name>  - Install a SimPL package")
        print("  install npm:<name>      - Install an NPM package (JS Bridge)")
        print("  uninstall <package-name> - Uninstall a package")
        print("  list                    - List installed packages")
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
    elif command == 'mock' and len(sys.argv) >= 3:
        install_package(sys.argv[2], mock=True)
    else:
        print(f"Unknown command or missing arguments: {command}")
        sys.exit(1)
