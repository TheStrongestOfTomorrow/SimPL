"""
SimPL Package Manager

Handles installation of packages from GitHub Issues in the SimPL-Libraries repo.
Supports mock mode for testing without network access.
"""

import os
import re
import json
import requests
from pathlib import Path

# Try to import pyyaml, fall back to regex parser if not available
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


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


def install_package(package_name, repo_owner="SimPL-Language", repo_name="SimPL-Libraries", mock=False):
    """
    Install a package from GitHub Issues.
    
    Args:
        package_name: Name of the package to install
        repo_owner: GitHub username/organization owning the repo
        repo_name: Name of the GitHub repository
        mock: If True, use mock data instead of calling GitHub API
    
    Returns:
        dict with installation result, or None on failure
    """
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
    Uninstall a package.
    
    Args:
        package_name: Name of the package to uninstall
    
    Returns:
        True on success, False on failure
    """
    lock_file = Path('./simpl.lock')
    package_dir = Path('./libs') / package_name
    
    # Load lock file
    installed_packages = {}
    if lock_file.exists():
        try:
            with open(lock_file, 'r') as f:
                installed_packages = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    if package_name not in installed_packages:
        print(f"❌ Package '{package_name}' is not installed")
        return False
    
    # Remove package directory
    if package_dir.exists():
        import shutil
        shutil.rmtree(package_dir)
    
    # Update lock file
    del installed_packages[package_name]
    
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
        print("  install <package-name>  - Install a package")
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
                mock_tag = " (mock)" if info.get('mock') else ""
                print(f"  - {name}@{info.get('version', 'unknown')}{mock_tag}")
        else:
            print("No packages installed yet.")
    elif command == 'mock' and len(sys.argv) >= 3:
        install_package(sys.argv[2], mock=True)
    else:
        print(f"Unknown command or missing arguments: {command}")
        sys.exit(1)
