"""
SimPL Core Lexer - Tokenizer for Standard SimPL Syntax

This module handles tokenization of SimPL source code into tokens
that can be parsed and executed by the interpreter.

Supports:
- Variables (let keyword)
- Print statements
- Basic math operations (+, -, *, /)
- Strings (double quotes)
- Numbers (integers and floats)
- Keywords: let, print, if, then, else, end, do, while, for, in
- Identifiers and operators
"""

import re
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum, auto


class TokenType(Enum):
    """Enumeration of all token types in SimPL."""
    # Keywords
    LET = auto()
    PRINT = auto()
    IF = auto()
    THEN = auto()
    ELSE = auto()
    END = auto()
    DO = auto()
    WHILE = auto()
    FOR = auto()
    IN = auto()
    
    # Literals
    NUMBER = auto()
    STRING = auto()
    IDENTIFIER = auto()
    
    # Operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    EQUALS = auto()
    EQUALS_EQUALS = auto()  # == for comparison
    NOT_EQUALS = auto()     # != for comparison
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
    COMMA = auto()
    COLON = auto()
    
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
    'end': TokenType.END,
    'do': TokenType.DO,
    'while': TokenType.WHILE,
    'for': TokenType.FOR,
    'in': TokenType.IN,
    'and': TokenType.AND,
    'or': TokenType.OR,
    'not': TokenType.NOT,
}


class LexerError(Exception):
    """Exception raised for lexer errors."""
    def __init__(self, message: str, line: int, column: int):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"Line {line}, Column {column}: {message}")


class Lexer:
    """
    Tokenizer for SimPL source code.
    
    Converts source code string into a list of Token objects.
    Designed to be extensible for different syntax flavor packs.
    """
    
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
    
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
        token_type = KEYWORDS.get(value.lower(), TokenType.IDENTIFIER)
        
        return Token(token_type, value, start_line, start_column)
    
    def make_token(self, token_type: TokenType, value: str) -> Token:
        """Create a token with current position info."""
        token = Token(token_type, value, self.line, self.column)
        self.advance()
        return token
    
    def tokenize(self) -> List[Token]:
        """
        Convert source code into a list of tokens.
        
        Returns:
            List of Token objects representing the source code.
        """
        self.tokens = []
        
        while self.current_char() is not None:
            # Skip whitespace
            if self.current_char() in ' \t\r':
                self.skip_whitespace()
                continue
            
            # Skip comments
            if self.current_char() == '#' or self.current_char() == '/':
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
                self.advance()
                self.advance()
                continue
            
            if self.current_char() == '!' and self.peek_char() == '=':
                self.tokens.append(Token(TokenType.NOT_EQUALS, '!=', self.line, self.column))
                self.advance()
                self.advance()
                continue
            
            if self.current_char() == '<' and self.peek_char() == '=':
                self.tokens.append(Token(TokenType.LESS_EQUALS, '<=', self.line, self.column))
                self.advance()
                self.advance()
                continue
            
            if self.current_char() == '>' and self.peek_char() == '=':
                self.tokens.append(Token(TokenType.GREATER_EQUALS, '>=', self.line, self.column))
                self.advance()
                self.advance()
                continue
            
            # Single-character operators and delimiters
            char = self.current_char()
            if char == '+':
                self.tokens.append(Token(TokenType.PLUS, '+', self.line, self.column))
            elif char == '-':
                self.tokens.append(Token(TokenType.MINUS, '-', self.line, self.column))
            elif char == '*':
                self.tokens.append(Token(TokenType.STAR, '*', self.line, self.column))
            elif char == '/':
                self.tokens.append(Token(TokenType.SLASH, '/', self.line, self.column))
            elif char == '=':
                self.tokens.append(Token(TokenType.EQUALS, '=', self.line, self.column))
            elif char == '<':
                self.tokens.append(Token(TokenType.LESS_THAN, '<', self.line, self.column))
            elif char == '>':
                self.tokens.append(Token(TokenType.GREATER_THAN, '>', self.line, self.column))
            elif char == '(':
                self.tokens.append(Token(TokenType.LPAREN, '(', self.line, self.column))
            elif char == ')':
                self.tokens.append(Token(TokenType.RPAREN, ')', self.line, self.column))
            elif char == ',':
                self.tokens.append(Token(TokenType.COMMA, ',', self.line, self.column))
            elif char == ':':
                self.tokens.append(Token(TokenType.COLON, ':', self.line, self.column))
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
    # Test the lexer
    test_code = '''
let x = 10
let y = 20
print "Hello, World!"
print x + y
'''
    
    lexer = Lexer(test_code)
    tokens = lexer.tokenize()
    
    print("Tokens:")
    for token in tokens:
        print(f"  {token}")
