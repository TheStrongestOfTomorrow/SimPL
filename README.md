<div align="center">

# SimPL

**The Simple Programming Language**

*Reads like English. Runs anywhere. Batteries included.*

[![Version](https://img.shields.io/badge/version-0.4.0-blue.svg)](https://github.com/thestrongestoftomorrow/SimPL)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-3776AB.svg)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/NPM%20Bridge-Node.js-339933.svg)](https://nodejs.org/)

[Getting Started](#getting-started) · [Examples](#examples) · [Language Reference](#language-reference) · [Package Manager](#package-manager) · [Contributing](#contributing)

</div>

---

SimPL is a beginner-friendly programming language designed to be as readable as English while remaining versatile enough for scripts, web projects, and games. It ships with built-in file, web, and math operations — no imports needed for the basics.

The interpreter is written in Python and supports **three syntax flavors** out of the box: Standard SimPL (English-like `then`/`end`), C/JavaScript-style (braces `{}` and semicolons `;`), and Python-style (colons `:` and indentation). You can even mix flavors across different blocks in the same program.

---

## Table of Contents

- [Why SimPL?](#why-simpl)
- [Getting Started](#getting-started)
- [Examples](#examples)
- [Language Reference](#language-reference)
  - [Variables](#variables)
  - [Conditionals](#conditionals)
  - [Loops](#loops)
  - [Functions](#functions)
  - [Lists](#lists)
  - [Built-in Functions](#built-in-functions)
  - [Syntax Flavor Packs](#syntax-flavor-packs)
- [Package Manager](#package-manager)
  - [SimPL-Libraries Registry](#simpl-libraries-registry)
  - [NPM Bridge](#npm-bridge)
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
| **Batteries Included** | 25+ built-in functions for math, strings, lists, and I/O — no imports needed |
| **NPM Bridge** | Use any JavaScript library from NPM directly inside SimPL via `js_eval()` |
| **Friendly Errors** | Smart Helper gives human-readable error messages with fix suggestions |
| **Package Manager** | Install community packages from GitHub Issues or NPM with one command |
| **REPL** | Interactive mode for experimentation and learning |

---

## Getting Started

### Prerequisites

- **Python 3.8+** (required — the interpreter is written in Python)
- **Node.js 14+** (optional — needed only for the NPM Bridge / `js_eval()`)

### Installation

```bash
git clone https://github.com/thestrongestoftomorrow/SimPL.git
cd SimPL
```

That's it. No `pip install`, no build step — just Python.

### Hello, World!

Create a file called `hello.simpl`:

```simpl
print "Hello, World!"
```

Run it:

```bash
python simpl.py run hello.simpl
```

### Interactive REPL

```bash
python simpl.py --repl
```

```
SimPL Interactive v0.4.0
Type 'exit' or 'quit' to exit, 'help' for help.

simpl> let x = 42
simpl> print x
42
simpl> print "The answer is " + str(x)
The answer is 42
```

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

### Conditionals with elif/else

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

### Lists and Built-ins

```simpl
let fruits = ["apple", "banana", "cherry"]
print fruits[0]              # apple
push(fruits, "date")
print len(fruits)            # 4
let last = pop(fruits)
print last                   # date
```

### NPM Bridge (JavaScript Interop)

```simpl
# Run any JavaScript expression
let result = js_eval("2 ** 10")
print result  # 1024

# Use NPM packages (install first: simpl install npm:lodash)
# let _ = js_eval("require('lodash')")
```

More examples are in the [`examples/`](examples/) directory:

| File | Description |
|------|-------------|
| [`hello.simpl`](examples/hello.simpl) | Basic hello world, variables, loops |
| [`full_demo.simpl`](examples/full_demo.simpl) | Complete feature tour — every built-in function |
| [`flavor_test.simpl`](examples/flavor_test.simpl) | All three syntax flavors in one program |
| [`test_npm.simpl`](examples/test_npm.simpl) | NPM Bridge / JavaScript interop |

---

## Language Reference

### Variables

Variables are declared with `let` and are dynamically typed. Re-declaring a variable with `let` overwrites the previous value.

```simpl
let name = "SimPL"
let version = 0.4
let is_cool = true
```

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

### Lists

Lists are created with square brackets and support indexing from 0:

```simpl
let colors = ["red", "green", "blue"]
print colors[1]  # green
```

### Built-in Functions

SimPL includes 25+ built-in functions — no imports required:

| Category | Functions |
|----------|-----------|
| **Type Conversion** | `str(x)`, `int(x)`, `float(x)`, `type(x)` |
| **Math** | `abs(x)`, `min(...)`, `max(...)`, `round(x, n)`, `floor(x)`, `ceil(x)`, `sqrt(x)`, `pow(x, y)`, `random()` |
| **Lists** | `len(x)`, `push(list, val)`, `pop(list)`, `range(n)`, `range(a, b)` |
| **Strings** | `upper(s)`, `lower(s)`, `trim(s)`, `split(s, sep)`, `join(list, sep)`, `replace(s, old, new)` |
| **Dictionaries** | `keys(dict)`, `values(dict)` |
| **I/O** | `input(prompt)`, `print(expr)` |
| **Interop** | `js_eval(code)` — execute JavaScript via Node.js |

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

Community packages are hosted as GitHub Issues in [SimPL-Libraries](https://github.com/thestrongestoftomorrow/SimPL-Libraries):

```bash
# Install a community package
python simpl.py install super-math

# Use it in your code
import super-math
```

### NPM Bridge

Install JavaScript packages from the NPM registry and use them via `js_eval()`:

```bash
# Install an NPM package
python simpl.py install npm:moment

# Use it in SimPL
import npm:moment
let year = js_eval("require('moment')().format('YYYY')")
print "Year: " + str(year)
```

### Managing Packages

```bash
python simpl.py list                    # List installed packages
python simpl.py uninstall super-math    # Remove a SimPL package
python simpl.py uninstall npm:moment    # Remove an NPM package
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
├── package_manager.py     # Dual-source package manager (SimPL + NPM)
├── core/
│   ├── __init__.py        # Package init
│   ├── lexer.py           # Tokenizer + Syntax Flavor Pack normalizer
│   ├── parser.py          # Recursive-descent parser + tree-walk interpreter
│   ├── helper.py          # Smart Helper (friendly error messages)
│   └── js_bridge.py       # NPM Bridge (Node.js subprocess execution)
├── examples/
│   ├── hello.simpl        # Basic hello world
│   ├── full_demo.simpl    # Complete feature tour
│   ├── flavor_test.simpl  # Syntax Flavor Pack demo
│   └── test_npm.simpl     # NPM Bridge demo
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
                        │  • 30+ token types                         │  (25+)
                                                                     │
                                                                     │  js_eval()
                                                                     │  ↕ Node.js
```

**Flavor Normalizer** — Before tokenization, the `FlavorNormalizer` class converts all three syntax flavors into Standard SimPL. This means the Parser and Interpreter only ever see one syntax, keeping the core logic simple and consistent.

**Recursive-Descent Parser** — The parser converts the normalized token stream into an AST using recursive descent with proper operator precedence (logical → comparison → additive → multiplicative → unary → postfix → primary).

**Tree-Walk Interpreter** — The interpreter walks the AST and executes statements directly. Functions get proper scope isolation (save/restore variable and function state on call/return), enabling safe recursion.

**NPM Bridge** — The `js_eval()` built-in spawns a `node -e` subprocess, wraps the code in a try/catch with `JSON.stringify`, captures stdout, and parses the result back into native Python types. The `NODE_PATH` environment variable is set to `./libs/` so `require()` can resolve installed NPM packages.

---

## CLI Reference

```
python simpl.py <command> [options]

Commands:
  run <script.simpl>              Run a SimPL script
  install <package>               Install a SimPL-Libraries package
  install npm:<package>           Install an NPM package (JS Bridge)
  uninstall <package>             Uninstall a package
  list                            List installed packages

Options:
  --check <script.simpl>          Check script for errors without running
  --tokens <script.simpl>         Show tokens from the lexer (debug)
  --repl                          Run in interactive REPL mode
  --version, -v                   Show version
  --help                          Show help message
  --mock                          Use mock data for package install (testing)
```

---

## Contributing

We welcome contributions! Here's how to get started:

1. **Fork** the repository
2. **Create a feature branch**: `git checkout -b feature/my-feature`
3. **Make your changes** and test them with the example scripts
4. **Submit a pull request** with a clear description

### Adding a Community Package

Packages live in the [SimPL-Libraries](https://github.com/thestrongestoftomorrow/SimPL-Libraries) repo as GitHub Issues. To publish a package:

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

3. Users can then install it with `python simpl.py install my-package`

### Reporting Bugs

Open an Issue on the [SimPL repo](https://github.com/thestrongestoftomorrow/SimPL/issues) with:
- What you expected to happen
- What actually happened
- The SimPL code that triggered the bug
- Your Python and Node.js versions

---

## License

SimPL is released under the [MIT License](LICENSE).

Copyright (c) 2024-2026 TheStrongestOfTomorrow
