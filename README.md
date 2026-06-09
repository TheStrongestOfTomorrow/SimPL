<div align="center">

# SimPL

**The Simple Programming Language**

*Reads like English. Runs anywhere. Batteries included.*

[![Version](https://img.shields.io/badge/version-0.7.0-blue.svg)](https://github.com/TheStrongestOfTomorrow/SimPL)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-3776AB.svg)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/NPM%20Bridge-Node.js-339933.svg)](https://nodejs.org/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows%20%7C%20Termux-lightgrey.svg)](https://github.com/TheStrongestOfTomorrow/SimPL)

[Getting Started](#getting-started) · [TUI](#tui-terminal-user-interface) · [Examples](#examples) · [Language Reference](#language-reference) · [Architecture](#architecture) · [Contributing](#contributing)

</div>

---

SimPL is a beginner-friendly programming language designed to be as readable as English while remaining versatile enough for scripts, web projects, and games. It ships with built-in file, web, and math operations — no imports needed for the basics.

The interpreter is written in Python and supports **three syntax flavors** out of the box: Standard SimPL (English-like `then`/`end`), C/JavaScript-style (braces `{}` and semicolons `;`), and Python-style (colons `:` and indentation). You can even mix flavors across different blocks in the same program.

---

## Table of Contents

- [Why SimPL?](#why-simpl)
- [Getting Started](#getting-started)
  - [Installation](#installation)
  - [Hello, World!](#hello-world)
  - [Interactive REPL](#interactive-repl)
- [TUI (Terminal User Interface)](#tui-terminal-user-interface)
- [Examples](#examples)
  - [Variables and Math](#variables-and-math)
  - [Conditionals](#conditionals)
  - [Loops](#loops)
  - [Functions and Recursion](#functions-and-recursion)
  - [Lists](#lists)
  - [Dictionaries](#dictionaries)
  - [Try / Catch](#try--catch)
  - [File I/O](#file-io)
  - [Boolean Type](#boolean-type)
  - [NPM Bridge](#npm-bridge-javascript-interop)
- [Language Reference](#language-reference)
  - [Variables](#variables)
  - [Data Types](#data-types)
  - [Conditionals](#conditionals-1)
  - [Loops](#loops-1)
  - [Functions](#functions)
  - [Lists](#lists-1)
  - [Dictionaries](#dictionaries-1)
  - [Try / Catch](#try--catch-1)
  - [Built-in Functions](#built-in-functions)
  - [Syntax Flavor Packs](#syntax-flavor-packs)
- [Package Manager](#package-manager)
  - [SimPL-Libraries Registry](#simpl-libraries-registry)
  - [NPM Bridge](#npm-bridge)
  - [Managing Packages](#managing-packages)
- [Smart Helper](#smart-helper)
- [Project Structure](#project-structure)
- [Architecture](#architecture)
- [CLI Reference](#cli-reference)
- [Contributing](#contributing)
- [License](#license)

---

## Why SimPL?

| | SimPL |
|---|---|
| **Readable** | Syntax reads like natural English — `if x > 5 then ... end` |
| **Multi-flavor** | Write in Standard, C/JS, or Python style — all compile to the same AST |
| **Batteries Included** | 50+ built-in functions for math, strings, lists, files, HTTP, JSON, and I/O — no imports needed |
| **Dictionaries** | First-class dict literals — `let person = {"name": "Alice", "age": 30}` |
| **Error Handling** | `try` / `catch` blocks with `__error__` variable for robust programs |
| **NPM Bridge** | Use any JavaScript library from NPM directly inside SimPL via `js_eval()` |
| **Friendly Errors** | Smart Helper gives human-readable error messages with fix suggestions |
| **Package Manager** | Install community packages from GitHub Issues or NPM with one command |
| **TUI** | Interactive terminal UI — just type `simpl` to get started |
| **REPL** | Interactive mode for experimentation and learning |
| **Cross-Platform** | One-command install on Linux, macOS, Windows, and Termux (Android) |

---

## Getting Started

### Installation

| Platform | Command |
|----------|---------|
| **Linux / macOS** | `curl -sSL https://raw.githubusercontent.com/TheStrongestOfTomorrow/SimPL/main/install.sh \| bash` |
| **Windows (PowerShell)** | `irm https://raw.githubusercontent.com/TheStrongestOfTomorrow/SimPL/main/install.ps1 \| iex` |
| **Termux (Android)** | `curl -sSL https://raw.githubusercontent.com/TheStrongestOfTomorrow/SimPL/main/install.sh \| bash` |
| **From Source** | `git clone https://github.com/TheStrongestOfTomorrow/SimPL.git && cd SimPL && python setup.py` |

#### Prerequisites

- **Python 3.8+** (required — the interpreter is written in Python)
- **Node.js 14+** (optional — needed only for the NPM Bridge / `js_eval()`)

#### Install Details

**Linux / macOS / Termux** — The `install.sh` script clones SimPL to `~/.simpl`, creates a `simpl` launcher in your PATH, and verifies Python/Node.js availability.

**Windows** — The `install.ps1` script clones SimPL to `%USERPROFILE%\.simpl`, creates a `simpl.bat` launcher in `%APPDATA%\SimPL`, and adds it to your user PATH.

**From Source** — After `git clone`, run `python setup.py` to create the `simpl` launcher manually. Run `python setup.py --uninstall` to remove it.

> **Note:** If you just want to try SimPL without installing, you can run scripts directly with `python simpl.py run <script.simpl>` from the cloned directory.

### Hello, World!

Create a file called `hello.simpl`:

```simpl
print "Hello, World!"
```

Run it:

```bash
simpl run hello.simpl
```

Or, without the launcher:

```bash
python simpl.py run hello.simpl
```

### Interactive REPL

```bash
simpl --repl
```

```
SimPL Interactive v0.7.0
Type 'exit' or 'quit' to exit, 'help' for help.

simpl> let x = 42
simpl> print x
42
simpl> print "The answer is " + str(x)
The answer is 42
```

---

## TUI (Terminal User Interface)

Launch the TUI by simply typing `simpl` with no arguments:

```bash
simpl
```

```
  ███████╗██╗███╗   ███╗
  ██╔════╝██║████╗ ████║
  ███████╗██║██╔████╔██║
  ╚════██║██║██║╚██╔╝██║
  ███████║██║██║ ╚═╝ ██║
  ╚══════╝╚═╝╚═╝     ╚═╝

  The Simple Programming Language v0.7.0
  Platform: Linux | Python 3.12.0

  ┌──────────────────────────────────────┐
  │          SimPL Main Menu             │
  ├──────────────────────────────────────┤
  │  1. Run a .simpl script              │
  │  2. Interactive REPL                 │
  │  3. Install a package                │
  │  4. Uninstall a package              │
  │  5. List installed packages          │
  │  6. Check script for errors          │
  │  7. Show language reference          │
  │  8. Create a new .simpl file         │
  │  9. About SimPL                      │
  │  0. Exit                             │
  └──────────────────────────────────────┘

  simpl>
```

**Features:**

- **Full ANSI color support** on Linux, macOS, and Termux with automatic detection
- **Graceful degradation** on Windows — colors are enabled on Windows 10+ with VT100 support
- **Zero external dependencies** — built entirely with Python's standard library
- **Interactive workflow** — run scripts, manage packages, create files, and view the language reference without leaving the TUI
- **Platform-aware** — detects your OS and Python version automatically

You can also launch the TUI explicitly with `simpl --tui`.

---

## Examples

### Variables and Math

```simpl
let x = 10
let y = 20
let sum = x + y
print "Sum: " + str(sum)       # Sum: 30
print "Modulo: " + str(x % 3)  # Modulo: 1
```

### Conditionals

```simpl
let grade = 85
if grade >= 90 then
    print "A"
elif grade >= 80 then
    print "B"
elif grade >= 70 then
    print "C"
else
    print "F"
end
```

### Loops

```simpl
# While loop
let i = 0
while i < 5 do
    print i
    let i = i + 1
end

# For loop
for item in [10, 20, 30] do
    print item
end

# Repeat loop
repeat 3 times
    print "Hello!"
end
```

### Functions and Recursion

```simpl
function factorial(n)
    if n <= 1 then
        return 1
    end
    return n * factorial(n - 1)
end

print factorial(5)  # 120
```

### Lists

```simpl
let fruits = ["apple", "banana", "cherry"]
print fruits[0]              # apple
push(fruits, "date")
print len(fruits)            # 4
let last = pop(fruits)
print last                   # date

# Index assignment
let numbers = [1, 2, 3]
numbers[1] = 99
print numbers                # [1, 99, 3]

# List functions
let reversed = reverse(fruits)
let sorted = sort([3, 1, 2])
print contains(fruits, "apple")  # true
```

### Dictionaries

```simpl
# Create a dictionary
let person = {"name": "Alice", "age": 30}
print person["name"]         # Alice
print person["age"]          # 30

# Modify a dictionary
person["city"] = "Paris"
print person["city"]         # Paris

# Dict functions
print keys(person)           # ["name", "age", "city"]
print values(person)         # ["Alice", 30, "Paris"]
```

### Try / Catch

```simpl
# Basic error handling
try
    let result = 10 / 0
catch
    print "Cannot divide by zero!"
    print "Error: " + __error__
end

# Practical example
let data = {"key": "value"}
try
    print data["missing"]
catch
    print "Key not found: " + __error__
end
```

### File I/O

```simpl
# Write to a file
write_file("greeting.txt", "Hello from SimPL!")

# Append to a file
append_file("greeting.txt", "\nAnother line!")

# Read from a file
let content = read_file("greeting.txt")
print content
```

### Boolean Type

```simpl
let is_active = true
let is_deleted = false

if is_active then
    print "User is active"
end

# Booleans in expressions
print true                   # true
print false                  # false
print bool(1)                # true
print bool(0)                # false
```

### NPM Bridge (JavaScript Interop)

```simpl
# Run any JavaScript expression
let result = js_eval("2 ** 10")
print result  # 1024

# Use NPM packages (install first: simpl install npm:lodash)
# let _ = js_eval("require('lodash')")
```

### HTTP Requests

```simpl
# GET request
let response = get("https://api.github.com/repos/TheStrongestOfTomorrow/SimPL")
print "Status: " + str(response["status"])

# Parse JSON response
let data = response.json()
print "Stars: " + str(data["stargazers_count"])

# POST request
let result = post("https://httpbin.org/post", {"key": "value"})
```

### JSON Built-ins

```simpl
# Parse JSON string into SimPL dict
let obj = parse_json('{"name": "SimPL", "version": "0.7.0"}')
print obj["name"]  # SimPL

# Convert SimPL object to JSON string
let config = {"debug": true, "port": 8080}
let json_str = to_json(config, true)  # pretty-printed
write_file("config.json", json_str)
```

More examples are in the [`examples/`](examples/) directory:

| File | Description |
|------|-------------|
| [`hello.simpl`](examples/hello.simpl) | Basic hello world, variables, loops |
| [`full_demo.simpl`](examples/full_demo.simpl) | Complete feature tour — every built-in function |
| [`flavor_test.simpl`](examples/flavor_test.simpl) | All three syntax flavors in one program |
| [`test_npm.simpl`](examples/test_npm.simpl) | NPM Bridge / JavaScript interop |
| [`real_world.simpl`](examples/real_world.simpl) | Real API calls, JSON, dicts — production-ready demo |

---

## Language Reference

### Variables

Variables are declared with `let` and are dynamically typed. Re-declaring a variable with `let` overwrites the previous value.

```simpl
let name = "SimPL"
let version = 0.5
let is_cool = true
let items = [1, 2, 3]
let config = {"debug": true, "port": 8080}
```

### Data Types

| Type | Example | Description |
|------|---------|-------------|
| **Number** | `42`, `3.14` | Integers and floats (dynamic) |
| **String** | `"hello"`, `'world'` | Double or single quoted |
| **Boolean** | `true`, `false` | Proper boolean type (not numbers) |
| **List** | `[1, 2, 3]` | Ordered, mutable collection |
| **Dictionary** | `{"key": "val"}` | Key-value mapping |
| **Null** | `null` | Absence of value |

### Conditionals

SimPL supports `if` / `elif` / `else` / `end` blocks:

```simpl
if x > 100 then
    print "big"
elif x > 50 then
    print "medium"
else
    print "small"
end
```

### Loops

Three loop constructs are available:

| Syntax | Description |
|--------|-------------|
| `while <cond> do ... end` | Loop while condition is true |
| `for <var> in <iterable> do ... end` | Iterate over a list or range |
| `repeat <n> times ... end` | Repeat a block N times |

All loops support `break` and `continue`.

### Functions

Functions are defined with `function` and support parameters and `return`:

```simpl
function add(a, b)
    return a + b
end

print add(3, 4)  # 7
```

Functions support **recursion** with proper scope isolation — each call gets its own variable scope.

> **Note:** Bare function calls like `push(list, val)` do not print their return value — only explicit `print` statements produce output.

### Lists

Lists are created with square brackets and support zero-based indexing and index assignment:

```simpl
let colors = ["red", "green", "blue"]
print colors[1]    # green

# Index assignment
colors[1] = "yellow"
print colors[1]    # yellow
```

### Dictionaries

Dictionaries are created with curly braces and support string-keyed access:

```simpl
let person = {"name": "Alice", "age": 30}
print person["name"]    # Alice

# Assignment
person["email"] = "alice@example.com"

# Introspection
print keys(person)      # ["name", "age", "email"]
print values(person)    # ["Alice", 30, "alice@example.com"]
```

### Try / Catch

Error handling with `try` / `catch` blocks. The `__error__` variable is available inside the `catch` block:

```simpl
try
    let result = risky_operation()
catch
    print "Something went wrong: " + __error__
end
```

### Built-in Functions

SimPL includes 50+ built-in functions — no imports required:

| Category | Function | Signature | Description |
|----------|----------|-----------|-------------|
| **I/O** | `print` | `print(expr)` | Print a value to stdout |
| | `input` | `input(prompt)` | Read a line of input from stdin |
| **Type Conversion** | `str` | `str(x)` | Convert to string |
| | `int` | `int(x)` | Convert to integer |
| | `float` | `float(x)` | Convert to float |
| | `bool` | `bool(x)` | Convert to boolean |
| | `to_number` | `to_number(s)` | Parse a string to a number |
| | `type` | `type(x)` | Return type name as string |
| **Math** | `abs` | `abs(x)` | Absolute value |
| | `min` | `min(a, b, ...)` | Minimum value |
| | `max` | `max(a, b, ...)` | Maximum value |
| | `round` | `round(x, n)` | Round to n decimal places |
| | `floor` | `floor(x)` | Round down to integer |
| | `ceil` | `ceil(x)` | Round up to integer |
| | `sqrt` | `sqrt(x)` | Square root |
| | `pow` | `pow(x, y)` | Exponentiation (xʸ) |
| | `random` | `random()` | Random float in [0, 1) |
| **Lists** | `len` | `len(x)` | Length of list, string, or dict |
| | `push` | `push(list, val)` | Append value to list |
| | `pop` | `pop(list)` | Remove and return last element |
| | `range` | `range(n)` / `range(a, b)` | Generate a list of numbers |
| | `reverse` | `reverse(list)` | Return reversed list |
| | `sort` | `sort(list)` | Return sorted list |
| | `contains` | `contains(list, val)` | Check if list/string contains value |
| | `slice` | `slice(x, start, end)` | Extract a sublist/substring |
| | `index_of` | `index_of(list, val)` | Find index of value (-1 if not found) |
| **Strings** | `upper` | `upper(s)` | Convert to uppercase |
| | `lower` | `lower(s)` | Convert to lowercase |
| | `trim` | `trim(s)` | Strip leading/trailing whitespace |
| | `split` | `split(s, sep)` | Split string by separator |
| | `join` | `join(list, sep)` | Join list with separator |
| | `replace` | `replace(s, old, new)` | Replace occurrences in string |
| | `starts_with` | `starts_with(s, prefix)` | Check if string starts with prefix |
| | `ends_with` | `ends_with(s, suffix)` | Check if string ends with suffix |
| **Dictionaries** | `keys` | `keys(dict)` | Return list of keys |
| | `values` | `values(dict)` | Return list of values |
| **File I/O** | `read_file` | `read_file(path)` | Read entire file as string |
| | `write_file` | `write_file(path, content)` | Write content to file (overwrite) |
| | `append_file` | `append_file(path, content)` | Append content to file |
| **System** | `time` | `time()` | Current Unix timestamp (seconds) |
| | `sleep` | `sleep(seconds)` | Pause execution for N seconds |
| | `env` | `env(name)` | Get environment variable |
| | `shell` | `shell(cmd)` | Execute shell command, return output |
| **HTTP** | `get` | `get(url, headers?)` | HTTP GET request, returns response object |
| | `post` | `post(url, data, headers?)` | HTTP POST request, returns response object |
| **JSON** | `parse_json` | `parse_json(string)` | Parse JSON string into SimPL dict/list |
| | `to_json` | `to_json(obj, pretty?)` | Convert SimPL object to JSON string |
| **Dictionaries** | `has_key` | `has_key(dict, key)` | Check if dict contains key |
| | `remove` | `remove(dict, key)` | Remove a key from dict |
| **Interop** | `js_eval` | `js_eval(code)` | Execute JavaScript via Node.js |

> **Aliases:** `number` is an alias for `int`, and `string` is an alias for `str`.

### Syntax Flavor Packs

SimPL's Lexer automatically detects and normalizes three syntax flavors into a unified token stream before parsing. This means you can write in whichever style feels most natural:

#### Standard SimPL (Default)

```simpl
if x > 5 then
    print "Standard"
end
```

#### C / JavaScript Style

```simpl
if (x > 5) {
    print "C-style";
}
```

The normalizer:
- Strips parentheses from conditions: `if (x > 5)` → `if x > 5`
- Replaces `{` with `then` or `do`
- Replaces `}` with `end`
- Strips trailing semicolons

#### Python Style

```simpl
if x > 5:
    print "Python-style"
```

The normalizer:
- Replaces trailing `:` with `then` or `do`
- Tracks indentation levels and injects `end` on dedent

#### Mixed Flavors

You can use different flavors for different blocks in the same program:

```simpl
# Standard block
if x > 5 then
    print "Standard"
end

# C-style block
if (y > 10) {
    print "C-style";
}
```

However, **mixing flavors within a single block** is not allowed and triggers a `MixedFlavorError`:

```simpl
# WRONG: opened with { but closed with end
if (x > 5) {
    print "broken"
end
```

---

## Package Manager

SimPL has a dual-source package manager: community packages from the **SimPL-Libraries** registry (GitHub Issues) and **NPM packages** via the JS Bridge.

### SimPL-Libraries Registry

Community packages are hosted as GitHub Issues in [SimPL-Libraries](https://github.com/TheStrongestOfTomorrow/SimPL-Libraries):

```bash
# Install a community package
simpl install super-math

# Use it in your code
import super-math
```

### NPM Bridge

Install JavaScript packages from the NPM registry and use them via `js_eval()`:

```bash
# Install an NPM package
simpl install npm:moment

# Use it in SimPL
import npm:moment
let year = js_eval("require('moment')().format('YYYY')")
print "Year: " + str(year)
```

### Managing Packages

```bash
simpl list                    # List installed packages
simpl uninstall super-math    # Remove a SimPL package
simpl uninstall npm:moment    # Remove an NPM package
```

---

## Smart Helper

Instead of raw stack traces, SimPL provides friendly, human-readable error messages through its **Smart Helper** system:

```
╔════════════════════════════════════════╗
║       SimPL Error Report              ║
╚════════════════════════════════════════╝

📁 Category: Syntax Error

❗ Something unexpected was found here.

💡 Missing 'then' keyword
   In SimPL, every 'if' statement needs a 'then' keyword after the condition.
   → Add 'then' after your if condition.
   Example: if x > 5 then print "x is big" end
```

The Smart Helper:
- **Proactive checking** — catches common mistakes like missing `then`, unclosed strings, and unbalanced parentheses *before* execution
- **Pattern-matched tips** — recognizes 10+ error categories and suggests specific fixes
- **Mixed flavor detection** — warns when you mix C-style `{}` with Standard `end` in the same block
- **Quick reference** — type `help` in the REPL for a built-in cheat sheet

---

## Project Structure

```
SimPL/
├── simpl.py               # Main entry point / CLI runner
├── setup.py               # Manual install script (creates `simpl` launcher)
├── install.sh             # One-command installer for Linux/macOS/Termux
├── install.ps1            # One-command installer for Windows (PowerShell)
├── package_manager.py     # Dual-source package manager (SimPL + NPM)
├── core/
│   ├── __init__.py        # Package init
│   ├── lexer.py           # Tokenizer + Syntax Flavor Pack normalizer
│   ├── parser.py          # Recursive-descent parser + tree-walk interpreter
│   ├── helper.py          # Smart Helper (friendly error messages)
│   ├── tui.py             # Terminal User Interface (interactive menu)
│   └── js_bridge.py       # NPM Bridge (Node.js subprocess execution)
├── examples/
│   ├── hello.simpl        # Basic hello world
│   ├── full_demo.simpl    # Complete feature tour
│   ├── flavor_test.simpl  # Syntax Flavor Pack demo
│   ├── test_npm.simpl     # NPM Bridge demo
│   └── test_install.simpl # Package install demo
└── README.md
```

---

## Architecture

The SimPL interpreter follows a classic **three-stage pipeline**:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Source Code  │────▶│    Lexer     │────▶│    Parser    │────▶│  Interpreter │
│  (.simpl)     │     │ + FlavorNorm │     │  (AST gen)   │     │  (execution) │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                        │                                            │
                        │  normalize_flavors()                       │
                        │  • C/JS  { } → then/end                   │
                        │  • Python :  → then/end                   │
                        │  • Strip ; and ( )                         │
                        │                                            │
                        │  tokenize()                                │  Built-in
                        │  • Keywords, literals, operators           │  Functions
                        │  • BOOLEAN token (true/false)             │  (40+)
                        │  • Dict literals {"k": v}                 │
                        │  • try/catch keywords                      │
                                                                     │
                                                                     │  js_eval()
                                                                     │  ↕ Node.js
                                                                     │
                                                                     │  TUI
                                                                     │  (core/tui.py)
```

**Flavor Normalizer** — Before tokenization, the `FlavorNormalizer` class converts all three syntax flavors into Standard SimPL. This means the Parser and Interpreter only ever see one syntax, keeping the core logic simple and consistent.

**Recursive-Descent Parser** — The parser converts the normalized token stream into an AST using recursive descent with proper operator precedence (logical → comparison → additive → multiplicative → unary → postfix → primary). AST nodes include support for `DictNode`, `TryCatchNode`, `BooleanLiteral`, and `IndexAssignNode`.

**Tree-Walk Interpreter** — The interpreter walks the AST and executes statements directly. Functions get proper scope isolation (save/restore variable and function state on call/return), enabling safe recursion. The `try`/`catch` mechanism captures runtime errors and stores the message in the `__error__` variable.

**NPM Bridge** — The `js_eval()` built-in spawns a `node -e` subprocess, wraps the code in a try/catch with `JSON.stringify`, captures stdout, and parses the result back into native Python types. The `NODE_PATH` environment variable is set to `./libs/` so `require()` can resolve installed NPM packages.

**TUI** — The Terminal User Interface (`core/tui.py`) provides an interactive menu-driven experience with ANSI color support, platform detection, and launcher integration. Zero external dependencies — built entirely on Python's standard library.

---

## CLI Reference

```
simpl <command> [options]

Commands:
  run <script.simpl>              Run a SimPL script
  install <package>               Install a SimPL-Libraries package
  install npm:<package>           Install an NPM package (JS Bridge)
  uninstall <package>             Uninstall a package
  list                            List installed packages

Options:
  --tui                           Launch Terminal User Interface
  --check <script.simpl>          Check script for errors without running
  --tokens <script.simpl>         Show tokens from the lexer (debug)
  --repl                          Run in interactive REPL mode
  --version, -v                   Show version
  --help                          Show help message
  --mock                          Use mock data for package install (testing)

Default:
  (no arguments)                  Launch the TUI (interactive mode)
```

---

## Contributing

We welcome contributions! Here's how to get started:

1. **Fork** the repository
2. **Create a feature branch**: `git checkout -b feature/my-feature`
3. **Make your changes** and test them with the example scripts
4. **Submit a pull request** with a clear description

### Adding a Community Package

Packages live in the [SimPL-Libraries](https://github.com/TheStrongestOfTomorrow/SimPL-Libraries) repo as GitHub Issues. To publish a package:

1. Open a new Issue in SimPL-Libraries with the **package name as the title**
2. Add YAML frontmatter and a fenced code block:

```markdown
---
name: my-package
version: 1.0.0
dependencies: []
author: YourName
description: What your package does
---

\`\`\`simpl
# Your SimPL package code here
function my-package.hello()
    return "Hello from my-package!"
end
\`\`\`
```

3. Users can then install it with `simpl install my-package`

### Reporting Bugs

Open an Issue on the [SimPL repo](https://github.com/TheStrongestOfTomorrow/SimPL/issues) with:
- What you expected to happen
- What actually happened
- The SimPL code that triggered the bug
- Your Python and Node.js versions

---

## License

SimPL is released under the [MIT License](LICENSE).

Copyright (c) 2024-2026 TheStrongestOfTomorrow
