# SimPL - The Simple Programming Language

**SimPL** is the easiest programming language to learn. It reads like English, is versatile enough for scripts/web/games, and comes with "batteries included" — no imports needed for basic file, web, or math operations.

## Core Philosophy

- **Easy to Learn**: Syntax that reads like natural English
- **Versatile**: Built for scripts, but capable of web and games
- **Batteries Included**: No imports needed for basic operations

## Key Features

### 1. Syntax Flavor Packs
Choose your preferred syntax style:
- **Standard (Default)**: English-like, uses `then/end` or `do/end`. No strict indentation rules.
- **Python Flavor**: Uses indentation and colons `:`.
- **C/JS Flavor**: Uses braces `{}` and semicolons `;`.

### 2. GitHub Issues Package Manager
Packages are hosted as GitHub Issues in a central community repo:
```bash
simpl install <package-name>
```

### 3. NPM Bridge
Use JavaScript libraries natively:
```bash
simpl install npm:<package-name>
```

### 4. Smart Helper
Local rule-based error detection with friendly, human-readable hints instead of stack traces.

### 5. Multiple Runtimes
- CLI (Terminal)
- Web (Wasm/JS)
- Desktop (Tauri/Native)

### 6. SimPL Studio IDE
Lightweight 3-pane design: Library Hub, Code Canvas, Live Stage.

## Installation

```bash
git clone https://github.com/your-org/simpl.git
cd simpl
python simpl.py examples/hello.simpl
```

## Quick Start

Create a file `hello.simpl`:
```
print "Hello, World!"
let x = 10
let y = 20
print x + y
```

Run it:
```bash
python simpl.py hello.simpl
```

## Project Structure

```
simpl/
├── simpl.py          # Main entry point / CLI runner
├── core/
│   ├── __init__.py
│   ├── lexer.py      # Tokenizer
│   ├── parser.py     # Parser and interpreter
│   └── helper.py     # Smart Helper for error messages
├── examples/
│   └── hello.simpl   # Example script
└── README.md
```

## License

MIT License
