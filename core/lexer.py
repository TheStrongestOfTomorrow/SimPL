"""
SimPL Core Lexer - Tokenizer with Syntax Flavor Pack Normalizer

This module handles tokenization of SimPL source code into tokens
that can be parsed and executed by the interpreter.

Syntax Flavor Packs:
  The Lexer automatically detects and normalizes three syntax flavors:
    - Standard SimPL:  if x > 5 then ... end
    - C/JS Style:      if (x > 5) { ... }
    - Python Style:    if x > 5: \n    ...

  The normalizer runs BEFORE tokenization, converting all flavors into
  Standard SimPL so the Parser never sees anything unexpected.

Supported token types:
- Keywords: let, print, if, then, else, end, do, while, for, in,
            repeat, times, function, return, break, continue, elif, input,
            try, catch
- Literals: numbers, strings, booleans (true/false), identifiers
- Operators: +, -, *, /, %, ==, !=, <, >, <=, >=, and, or, not
- Delimiters: (, ), [, ], {, }, comma, colon, semicolon, dot
- Comments: # line, // line, /* block */
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum, auto


class TokenType(Enum):
    """Enumeration of all token types in SimPL."""
    # Keywords
    LET = auto()
    PRINT = auto()
    IF = auto()
    THEN = auto()
    ELSE = auto()
    ELIF = auto()
    END = auto()
    DO = auto()
    WHILE = auto()
    FOR = auto()
    IN = auto()
    REPEAT = auto()
    TIMES = auto()
    FUNCTION = auto()
    RETURN = auto()
    BREAK = auto()
    CONTINUE = auto()
    INPUT = auto()
    TRY = auto()
    CATCH = auto()

    # Literals
    NUMBER = auto()
    STRING = auto()
    BOOLEAN = auto()
    IDENTIFIER = auto()

    # Operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()        # modulo
    EQUALS = auto()
    EQUALS_EQUALS = auto()  # ==
    NOT_EQUALS = auto()     # !=
    LESS_THAN = auto()
    GREATER_THAN = auto()
    LESS_EQUALS = auto()
    GREATER_EQUALS = auto()
    AND = auto()
    OR = auto()
    NOT = auto()

    # Delimiters
    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()       # [
    RBRACKET = auto()       # ]
    COMMA = auto()
    COLON = auto()
    DOT = auto()            # .
    LBRACE = auto()         # {
    RBRACE = auto()         # }

    # Special
    NEWLINE = auto()
    EOF = auto()
    UNKNOWN = auto()


@dataclass
class Token:
    """Represents a single token from the source code."""
    type: TokenType
    value: str
    line: int
    column: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, line={self.line})"


# Keyword mapping
KEYWORDS = {
    'let': TokenType.LET,
    'print': TokenType.PRINT,
    'if': TokenType.IF,
    'then': TokenType.THEN,
    'else': TokenType.ELSE,
    'elif': TokenType.ELIF,
    'end': TokenType.END,
    'do': TokenType.DO,
    'while': TokenType.WHILE,
    'for': TokenType.FOR,
    'in': TokenType.IN,
    'repeat': TokenType.REPEAT,
    'times': TokenType.TIMES,
    'function': TokenType.FUNCTION,
    'return': TokenType.RETURN,
    'break': TokenType.BREAK,
    'continue': TokenType.CONTINUE,
    'input': TokenType.INPUT,
    'try': TokenType.TRY,
    'catch': TokenType.CATCH,
    'and': TokenType.AND,
    'or': TokenType.OR,
    'not': TokenType.NOT,
    'true': TokenType.BOOLEAN,
    'false': TokenType.BOOLEAN,
}


class LexerError(Exception):
    """Exception raised for lexer errors."""
    def __init__(self, message: str, line: int, column: int):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"Line {line}, Column {column}: {message}")


class MixedFlavorError(Exception):
    """Exception raised when mixed syntax flavors are detected."""
    def __init__(self, message: str, line: int = 0):
        self.message = message
        self.line = line
        super().__init__(message)


# ======================================================================
# Flavor Normalizer
# ======================================================================

class FlavorNormalizer:
    """
    Pre-processes source code to normalize C/JS and Python-style syntax
    into Standard SimPL before tokenization.

    Supported transformations:
      C/JS Flavor:
        - if (x > 5) { ... }  ->  if x > 5 then ... end
        - while (x) { ... }   ->  while x do ... end
        - Strip semicolons
        - Replace bare } with end

      Python Flavor:
        - if x > 5: ...       ->  if x > 5 then ... end
        - Indentation tracking: dedent injects 'end'

      Cross-flavor detection:
        - Opening with { but closing with 'end' triggers MixedFlavorError
        - Opening with : but closing with } triggers MixedFlavorError
    """

    # Regex to detect block-opening keywords
    _BLOCK_KEYWORDS_IF = {'if', 'elif'}
    _BLOCK_KEYWORDS_LOOP = {'while', 'for', 'repeat'}
    _BLOCK_KEYWORDS_FUNC = {'function'}
    _BLOCK_KEYWORDS_ELSE = {'else'}
    _BLOCK_KEYWORDS_TRY = {'try'}

    def __init__(self):
        self._flavor_stack = []  # Track which flavor opened each block: 'c', 'python', 'standard'

    def normalize(self, source: str) -> str:
        """
        Normalize source code by detecting and converting syntax flavors.

        Returns normalized Standard SimPL source code.

        Raises:
            MixedFlavorError: If conflicting flavors are detected within
                the same block.
        """
        self._flavor_stack = []

        # Step 0: Strip block comments /* ... */
        source = self._strip_block_comments(source)

        lines = source.split('\n')
        normalized = []

        # For Python-style indentation tracking
        indent_stack = [0]  # Stack of indentation levels
        in_python_block = False  # Whether we're inside a Python-style block

        for line_num_0, raw_line in enumerate(lines):
            line_num = line_num_0 + 1
            stripped = raw_line.rstrip()

            # Skip empty / comment-only lines (but preserve them)
            if not stripped or stripped.lstrip().startswith('#') or stripped.lstrip().startswith('//'):
                # For Python-style: empty lines don't change indentation
                # But we still need to check if next non-empty line dedents
                normalized.append(stripped)
                continue

            # Calculate current indentation (Python-style)
            current_indent = len(raw_line) - len(raw_line.lstrip())

            # ---- Python-style dedent detection ----
            # If we're tracking indentation and the indent decreased,
            # we need to inject 'end' tokens
            if in_python_block and current_indent < indent_stack[-1]:
                # Pop indent stack and inject ends
                while len(indent_stack) > 1 and indent_stack[-1] > current_indent:
                    indent_stack.pop()
                    if self._flavor_stack and self._flavor_stack[-1] == 'python':
                        self._flavor_stack.pop()
                        normalized.append('end')
                    else:
                        break
                if indent_stack and indent_stack[-1] == current_indent:
                    pass  # Correct level
                else:
                    indent_stack.append(current_indent)

            # ---- Detect flavor of this line ----
            line_flavor = self._detect_line_flavor(stripped)

            if line_flavor == 'c_open':
                # C-style block opener: line ends with {
                converted = self._convert_c_open(stripped)
                normalized.append(converted)
                self._flavor_stack.append('c')
                in_python_block = False

            elif line_flavor == 'c_close':
                # C-style block closer: line is just }
                # Check for mixed flavors
                if self._flavor_stack and self._flavor_stack[-1] == 'python':
                    raise MixedFlavorError(
                        f"🛑 Error: Mixed syntax flavors on line {line_num}. "
                        f"💡 Tip: You started a block with Python-style ':' "
                        f"but tried to close it with C-style '}}'. "
                        f"Stick to one flavor per block!",
                        line_num
                    )
                remaining = stripped[:-1].strip()
                if remaining:
                    normalized.append(remaining)
                if self._flavor_stack:
                    self._flavor_stack.pop()
                normalized.append('end')
                in_python_block = False

            elif line_flavor == 'python_open':
                # Python-style block opener: line ends with :
                converted = self._convert_python_open(stripped)
                normalized.append(converted)
                self._flavor_stack.append('python')
                indent_stack.append(current_indent + 4)  # Expect deeper indent
                in_python_block = True

            elif line_flavor == 'standard_end':
                # Standard SimPL 'end' keyword — check for mixed flavors
                if self._flavor_stack and self._flavor_stack[-1] == 'c':
                    raise MixedFlavorError(
                        f"🛑 Error: Mixed syntax flavors on line {line_num}. "
                        f"💡 Tip: You started a block with C-style '{{' "
                        f"but closed with Standard 'end'. Stick to one flavor per block!",
                        line_num
                    )
                normalized.append(stripped)
                if self._flavor_stack:
                    self._flavor_stack.pop()
                in_python_block = False

            else:
                # Standard SimPL line — just strip semicolons
                normalized.append(self._strip_semicolons(stripped))

        # Close any remaining Python-style blocks at EOF
        while self._flavor_stack and self._flavor_stack[-1] == 'python':
            self._flavor_stack.pop()
            normalized.append('end')

        return '\n'.join(normalized)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _detect_line_flavor(self, stripped: str) -> str:
        """
        Detect the syntax flavor of a single line.

        Returns:
            'c_open'      - line ends with {
            'c_close'     - line is (mostly) just }
            'python_open' - line ends with : (but isn't a dict or slice)
            'standard_end'- line is just 'end'
            'standard'    - normal SimPL line
        """
        # Check for C-style close: line is just } or } with whitespace
        if stripped == '}' or stripped == '};':
            return 'c_close'
        # Also handle } else { patterns — the } is a close
        if stripped.startswith('}') and len(stripped) <= 3:
            return 'c_close'

        # Check for C-style open: line ends with {
        if stripped.endswith('{'):
            return 'c_open'

        # Check for standard 'end'
        if stripped == 'end' or stripped == 'end;':
            return 'standard_end'

        # Check for Python-style open: line ends with :
        # But we need to be careful not to match:
        #   - dict literals: {key: value}
        #   - slice notation: arr[1:3]
        #   - ternary expressions (not implemented yet)
        if stripped.endswith(':') and not stripped.endswith('::'):
            # Ignore if inside brackets (dict or slice)
            bracket_depth = 0
            for ch in stripped[:-1]:
                if ch in '([{':
                    bracket_depth += 1
                elif ch in ')]}':
                    bracket_depth -= 1
            if bracket_depth == 0:
                # Additional check: make sure it looks like a block opener
                # (starts with a keyword or is an else: line)
                first_word = stripped.lstrip().split()[0].lower() if stripped.lstrip() else ''
                block_keywords = {'if', 'elif', 'else', 'while', 'for', 'repeat',
                                  'function', 'def', 'try', 'except', 'with', 'class'}
                if first_word.rstrip(':') in block_keywords:
                    return 'python_open'
                # Also handle bare "else:" which is common
                if first_word == 'else:':
                    return 'python_open'

        return 'standard'

    def _convert_c_open(self, stripped: str) -> str:
        """Convert a C-style block opener to Standard SimPL."""
        # Remove the trailing {
        line_content = stripped[:-1].rstrip()
        # Strip semicolons
        line_content = self._strip_semicolons(line_content)
        # Remove parens around if/while conditions
        line_content = self._strip_condition_parens(line_content)
        # Add appropriate keyword
        return self._add_block_keyword(line_content)

    def _convert_python_open(self, stripped: str) -> str:
        """Convert a Python-style block opener to Standard SimPL."""
        # Remove the trailing :
        line_content = stripped[:-1].rstrip()
        # Add appropriate keyword
        return self._add_block_keyword(line_content)

    def _add_block_keyword(self, line_content: str) -> str:
        """
        Add the correct block keyword (then/do) based on the statement type.
        If the line already ends with 'then' or 'do', don't add another.
        """
        # Check if keyword already present
        words = line_content.lower().split()
        if words and words[-1] in ('then', 'do'):
            return line_content  # Already has the keyword

        first_word = words[0] if words else ''

        if first_word in self._BLOCK_KEYWORDS_IF or first_word in self._BLOCK_KEYWORDS_ELSE:
            return line_content + ' then'
        elif first_word in self._BLOCK_KEYWORDS_LOOP:
            return line_content + ' do'
        elif first_word in self._BLOCK_KEYWORDS_FUNC:
            return line_content + ' then'  # function bodies use then/end
        elif first_word in self._BLOCK_KEYWORDS_TRY:
            return line_content + ' then'  # try blocks use then/end
        else:
            # Default to then for unknown patterns
            return line_content + ' then'

    def _strip_condition_parens(self, line: str) -> str:
        """
        Remove unnecessary parentheses from if/while conditions.

        Examples:
            if (x > 5)   ->  if x > 5
            while (x)    ->  while x
            if (a && b)  ->  if a and b   (partial — && is not yet a token)
        """
        # Match: if (...) or while (...)
        result = re.sub(
            r'\b(if|while|elif)\s*\((.+)\)\s*$',
            r'\1 \2',
            line
        )
        return result

    def _strip_semicolons(self, line: str) -> str:
        """Strip trailing semicolons from a line, and split inline semicolons."""
        # Handle inline semicolons: "let a = 5; let b = 10;" becomes two lines
        # But we must be careful not to split semicolons inside strings
        # Simple approach: split on semicolons that are not inside quotes
        parts = self._split_on_semicolons(line)
        if len(parts) > 1:
            return '\n'.join(p.rstrip(';').rstrip() for p in parts)
        return line.rstrip(';').rstrip()

    def _split_on_semicolons(self, line: str) -> List[str]:
        """Split a line on semicolons that are outside of strings."""
        parts = []
        current = ""
        in_string = False
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == '"' and (i == 0 or line[i-1] != '\\'):
                in_string = not in_string
                current += ch
            elif ch == ';' and not in_string:
                parts.append(current)
                current = ""
            else:
                current += ch
            i += 1
        if current:
            parts.append(current)
        return parts

    def _strip_block_comments(self, source: str) -> str:
        """
        Remove /* ... */ block comments from source code.
        Handles multi-line comments.
        """
        result = re.sub(r'/\*.*?\*/', '', source, flags=re.DOTALL)
        return result


# ======================================================================
# Lexer
# ======================================================================

class Lexer:
    """
    Tokenizer for SimPL source code.

    Pipeline: raw source -> FlavorNormalizer -> token stream

    The normalizer converts C/JS and Python-style syntax into Standard
    SimPL before tokenization, so the Parser only ever sees one syntax.
    """

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []

    def normalize_source(self) -> str:
        """
        Normalize source code using the Flavor Normalizer.
        Handles C/JS {}, Python :, semicolons, condition parens, and
        indentation-based blocks.
        """
        normalizer = FlavorNormalizer()
        return normalizer.normalize(self.source)

    def current_char(self) -> Optional[str]:
        """Get the current character or None if at end."""
        if self.pos >= len(self.source):
            return None
        return self.source[self.pos]

    def peek_char(self, offset: int = 1) -> Optional[str]:
        """Look ahead at characters without advancing."""
        peek_pos = self.pos + offset
        if peek_pos >= len(self.source):
            return None
        return self.source[peek_pos]

    def advance(self) -> Optional[str]:
        """Advance position and return the character that was passed."""
        char = self.current_char()
        if char is not None:
            self.pos += 1
            if char == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
        return char

    def skip_whitespace(self):
        """Skip whitespace characters except newlines."""
        while self.current_char() is not None and self.current_char() in ' \t\r':
            self.advance()

    def skip_comment(self):
        """Skip single-line comments starting with # or //."""
        if self.current_char() == '#' or (self.current_char() == '/' and self.peek_char() == '/'):
            self.advance()  # Skip # or first /
            if self.current_char() == '/':
                self.advance()  # Skip second /
            while self.current_char() is not None and self.current_char() != '\n':
                self.advance()

    def read_string(self) -> Token:
        """Read a string literal enclosed in double quotes."""
        start_line = self.line
        start_column = self.column
        self.advance()  # Skip opening quote

        value = ""
        while self.current_char() is not None and self.current_char() != '"':
            if self.current_char() == '\\':
                self.advance()  # Skip backslash
                escape_char = self.current_char()
                if escape_char == 'n':
                    value += '\n'
                elif escape_char == 't':
                    value += '\t'
                elif escape_char == '"':
                    value += '"'
                elif escape_char == '\\':
                    value += '\\'
                elif escape_char == '{':
                    value += '{'
                elif escape_char == '}':
                    value += '}'
                else:
                    value += escape_char
            else:
                value += self.current_char()
            self.advance()

        if self.current_char() is None:
            raise LexerError("Unterminated string", start_line, start_column)

        self.advance()  # Skip closing quote

        return Token(TokenType.STRING, value, start_line, start_column)

    def read_number(self) -> Token:
        """Read a number literal (integer or float)."""
        start_line = self.line
        start_column = self.column
        value = ""

        # Read integer part
        while self.current_char() is not None and self.current_char().isdigit():
            value += self.current_char()
            self.advance()

        # Check for decimal point
        if self.current_char() == '.' and self.peek_char() is not None and self.peek_char().isdigit():
            value += '.'
            self.advance()
            while self.current_char() is not None and self.current_char().isdigit():
                value += self.current_char()
                self.advance()

        return Token(TokenType.NUMBER, value, start_line, start_column)

    def read_identifier(self) -> Token:
        """Read an identifier or keyword."""
        start_line = self.line
        start_column = self.column
        value = ""

        while self.current_char() is not None and (self.current_char().isalnum() or self.current_char() == '_'):
            value += self.current_char()
            self.advance()

        # Check if it's a keyword
        lower_value = value.lower()
        token_type = KEYWORDS.get(lower_value, TokenType.IDENTIFIER)

        # Special handling for true/false as BOOLEAN tokens
        if lower_value == 'true':
            return Token(TokenType.BOOLEAN, 'true', start_line, start_column)
        elif lower_value == 'false':
            return Token(TokenType.BOOLEAN, 'false', start_line, start_column)
        elif lower_value == 'elif':
            return Token(TokenType.ELIF, value, start_line, start_column)

        return Token(token_type, value, start_line, start_column)

    def tokenize(self) -> List[Token]:
        """
        Convert source code into a list of tokens.

        Pipeline: normalize flavors -> tokenize Standard SimPL

        Returns:
            List of Token objects representing the source code.
        """
        # Normalize source first (handle flavor packs)
        normalized_source = self.normalize_source()
        self.source = normalized_source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens = []

        while self.current_char() is not None:
            # Skip whitespace
            if self.current_char() in ' \t\r':
                self.skip_whitespace()
                continue

            # Treat semicolons as statement separators (like newlines)
            if self.current_char() == ';':
                self.tokens.append(Token(TokenType.NEWLINE, '\n', self.line, self.column))
                self.advance()
                continue

            # Skip comments (# and //)
            if self.current_char() == '#' or (self.current_char() == '/' and self.peek_char() == '/'):
                self.skip_comment()
                continue

            # Newline
            if self.current_char() == '\n':
                self.tokens.append(Token(TokenType.NEWLINE, '\n', self.line, self.column))
                self.advance()
                continue

            # String literal
            if self.current_char() == '"':
                self.tokens.append(self.read_string())
                continue

            # Number literal
            if self.current_char().isdigit():
                self.tokens.append(self.read_number())
                continue

            # Identifier or keyword
            if self.current_char().isalpha() or self.current_char() == '_':
                self.tokens.append(self.read_identifier())
                continue

            # Two-character operators
            if self.current_char() == '=' and self.peek_char() == '=':
                self.tokens.append(Token(TokenType.EQUALS_EQUALS, '==', self.line, self.column))
                self.advance(); self.advance()
                continue

            if self.current_char() == '!' and self.peek_char() == '=':
                self.tokens.append(Token(TokenType.NOT_EQUALS, '!=', self.line, self.column))
                self.advance(); self.advance()
                continue

            if self.current_char() == '<' and self.peek_char() == '=':
                self.tokens.append(Token(TokenType.LESS_EQUALS, '<=', self.line, self.column))
                self.advance(); self.advance()
                continue

            if self.current_char() == '>' and self.peek_char() == '=':
                self.tokens.append(Token(TokenType.GREATER_EQUALS, '>=', self.line, self.column))
                self.advance(); self.advance()
                continue

            # Single-character operators and delimiters
            char = self.current_char()
            token_type_map = {
                '+': TokenType.PLUS,
                '-': TokenType.MINUS,
                '*': TokenType.STAR,
                '/': TokenType.SLASH,
                '%': TokenType.PERCENT,
                '=': TokenType.EQUALS,
                '<': TokenType.LESS_THAN,
                '>': TokenType.GREATER_THAN,
                '(': TokenType.LPAREN,
                ')': TokenType.RPAREN,
                '[': TokenType.LBRACKET,
                ']': TokenType.RBRACKET,
                ',': TokenType.COMMA,
                ':': TokenType.COLON,
                '.': TokenType.DOT,
                '{': TokenType.LBRACE,
                '}': TokenType.RBRACE,
            }

            if char in token_type_map:
                self.tokens.append(Token(token_type_map[char], char, self.line, self.column))
            else:
                # Unknown character
                self.tokens.append(Token(TokenType.UNKNOWN, char, self.line, self.column))

            self.advance()

        # Add EOF token
        self.tokens.append(Token(TokenType.EOF, '', self.line, self.column))

        return self.tokens

    def tokenize_to_string(self) -> str:
        """Tokenize and return a string representation of tokens."""
        tokens = self.tokenize()
        return '\n'.join(str(token) for token in tokens)


def tokenize(source: str) -> List[Token]:
    """
    Convenience function to tokenize source code.

    Args:
        source: The SimPL source code string.

    Returns:
        List of Token objects.
    """
    lexer = Lexer(source)
    return lexer.tokenize()


if __name__ == '__main__':
    # Test the lexer with all flavor packs
    print("=== SimPL Lexer Test - Flavor Packs ===\n")

    # Standard SimPL
    standard = '''
let x = 10
if x > 5 then
    print "Standard works"
end
'''
    print("--- Standard SimPL ---")
    lexer = Lexer(standard)
    for tok in lexer.tokenize():
        print(f"  {tok}")

    # C/JS Style
    c_style = '''
let y = 20;
if (y > 15) {
    print "C-style works";
}
'''
    print("\n--- C/JS Style ---")
    lexer = Lexer(c_style)
    for tok in lexer.tokenize():
        print(f"  {tok}")

    # Python Style
    python_style = '''
let z = 30
if z > 25:
    print "Python style works"
'''
    print("\n--- Python Style ---")
    lexer = Lexer(python_style)
    for tok in lexer.tokenize():
        print(f"  {tok}")

    # Boolean tokens
    bool_test = '''
let a = true
let b = false
print a and b
'''
    print("\n--- Boolean Tokens ---")
    lexer = Lexer(bool_test)
    for tok in lexer.tokenize():
        print(f"  {tok}")

    # Try/Catch
    try_catch = '''
try
    let x = 1 / 0
catch
    print "Error!"
end
'''
    print("\n--- Try/Catch ---")
    lexer = Lexer(try_catch)
    for tok in lexer.tokenize():
        print(f"  {tok}")

    print("\n=== All flavor tests complete ===")
