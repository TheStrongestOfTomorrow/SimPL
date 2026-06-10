# SimPL

A simple, powerful programming language. Built with Rust. Single binary, no dependencies.

```
  ____                  _ _____
 / ___|  ___  _ __  __| |_   _| __ __ _  ___
 \___ \ / _ \| '_ \/ _` | | || '__/ _` |/ _ \
  ___) | (_) | | | (_| | | || | | (_| |  __/
 |____/ \___/|_|  \__,_| |_||_|  \__,_|\___|
```

## Install

**Linux / macOS / Termux:**
```bash
curl -sSL https://raw.githubusercontent.com/TheStrongestOfTomorrow/SimPL/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/TheStrongestOfTomorrow/SimPL/main/install.ps1 | iex
```

**From Source:**
```bash
git clone https://github.com/TheStrongestOfTomorrow/SimPL.git
cd SimPL
cargo build --release
# Binary at target/release/simpl
```

## Quick Start

```simpl
# Hello World
say "Hello, World!"

# Variables
set name = "SimPL"
set version = 1.0
say name + " v" + str(version)

# Lists
set fruits = ["apple", "banana", "cherry"]
for fruit in fruits {
  say "I like " + fruit
}

# Dicts
set person = {name: "Alice", age: 30}
say person.name
say person["age"]

# Functions
func greet(name) {
  say "Hello, " + name + "!"
}
greet("World")

# Conditions
set score = 85
if score >= 90 {
  say "A"
} elif score >= 80 {
  say "B"
} else {
  say "C"
}

# While loops
set i = 0
while i < 5 {
  say i
  set i = i + 1
}

# Try/catch
try {
  raise "oops"
} catch err {
  say "Caught: " + err
}
```

## CLI Commands

```bash
simpl run <file>       # Run a .simpl file
simpl repl             # Interactive REPL
simpl studio           # SimPL Studio (TUI IDE)
simpl install <pkg>    # Install a package
simpl update [pkg]     # Update package(s)
simpl remove <pkg>     # Remove a package
simpl list             # List installed packages
simpl search <query>   # Search packages
simpl version          # Show version
```

## Language Features

### Types
- **Number**: `42`, `3.14`, `-7`
- **String**: `"hello"`, `'world'`
- **Bool**: `true`, `false`
- **Null**: `null`
- **List**: `[1, 2, 3]`
- **Dict**: `{key: "value"}`

### Operators
| Operator | Description |
|----------|-------------|
| `+`, `-`, `*`, `/`, `%` | Arithmetic |
| `**` | Power |
| `//` | Floor division |
| `==`, `!=`, `<`, `>`, `<=`, `>=` | Comparison |
| `and`, `or`, `not` | Logical |
| `+=`, `-=`, `*=`, `/=` | Augmented assignment |

### Control Flow
```simpl
if condition { ... }
elif condition { ... }
else { ... }

for item in iterable { ... }
while condition { ... }

break
continue
return value
```

### Error Handling
```simpl
try {
  raise "Something went wrong"
} catch err {
  say "Error: " + err
}
```

### Built-in Functions

| Function | Description |
|----------|-------------|
| `say(value)` | Print a value |
| `input(prompt)` | Read user input |
| `type(value)` | Get type name |
| `len(value)` | Get length |
| `str(value)` | Convert to string |
| `num(value)` | Convert to number |
| `int(value)` | Convert to integer |
| `bool(value)` | Convert to boolean |
| `range(n)` | Create number range |
| `abs(n)` | Absolute value |
| `sqrt(n)` | Square root |
| `pow(a, b)` | Power |
| `floor(n)`, `ceil(n)`, `round(n)` | Rounding |
| `min(list)`, `max(list)` | Min/Max |
| `random()` | Random number |

### String Methods
```simpl
"Hello".upper()           # "HELLO"
"Hello".lower()           # "hello"
"  hi  ".trim()           # "hi"
"a,b,c".split(",")        # ["a", "b", "c"]
"hello".replace("l", "r") # "herro"
"hello".contains("ell")   # true
"hello".starts_with("he") # true
"hello".ends_with("lo")   # true
"hello".reverse()         # "olleh"
```

### List Methods
```simpl
[1,2,3].push(4)      # [1,2,3,4]
[1,2,3].pop()        # 3
[1,2,3].reverse()    # [3,2,1]
[3,1,2].sort()       # [1,2,3]
[1,2,3].join("-")    # "1-2-3"
[1,2,3].contains(2)  # true
[1,2,3].slice(1,3)   # [2,3]
```

### Dict Methods
```simpl
{a:1}.keys()          # ["a"]
{a:1}.values()        # [1]
{a:1}.has("a")        # true
{a:1}.remove("a")     # {}
{a:1}.merge({b:2})   # {a:1, b:2}
```

### HTTP Built-ins
```simpl
set resp = http_get("https://api.github.com")
say resp.status
say resp.body
say resp.ok()

set resp = http_post("https://api.example.com/data", json_stringify({name: "test"}))
```

### JSON Built-ins
```simpl
set data = json_parse('{"name": "Alice", "age": 30}')
say data.name
say json_stringify(data)
```

### Syntax Flavor Packs
Write SimPL in the style of other languages:

```simpl
# Python flavor: simpl run --flavor python file.simpl
print("Hello")
def greet(name):
  print("Hello, " + name)

# Rust flavor: simpl run --flavor rust file.simpl
println("Hello")
fn greet(name) {
  println("Hello, " + name)
}

# JavaScript flavor: simpl run --flavor js file.simpl
console.log("Hello")
function greet(name) {
  console.log("Hello, " + name)
}
```

## Package Manager

```bash
simpl install math-utils     # Install from registry
simpl update                  # Update all packages
simpl update math-utils       # Update specific package
simpl remove math-utils       # Remove package
simpl list                    # List installed
simpl search math             # Search registry
```

Packages are hosted via [GitHub Issues](https://github.com/TheStrongestOfTomorrow/SimPL-Libraries).

## SimPL Studio

Launch the TUI-based IDE:
```bash
simpl studio
```

## Platform Support

| Platform | Architecture | Binary |
|----------|-------------|--------|
| Linux | x86_64 | simpl-linux-x86_64 |
| Linux | ARM64 | simpl-linux-arm64 |
| macOS | x86_64 | simpl-macos-x86_64 |
| macOS | Apple Silicon | simpl-macos-arm64 |
| Windows | x86_64 | simpl-windows-x86_64.exe |
| Termux | ARM64 | simpl-linux-arm64 |

## Architecture

SimPL uses a 3-phase pipeline:
1. **Lexer** → Tokenizes source code into tokens
2. **Parser** → Builds an Abstract Syntax Tree (AST) from tokens
3. **Interpreter** → Walks the AST and evaluates expressions

Built with Rust for performance and reliability. Single binary, no runtime dependencies.

## License

MIT
