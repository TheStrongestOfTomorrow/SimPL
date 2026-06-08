"""
SimPL Core Parser - Parser and Interpreter for Standard SimPL Syntax

This module handles parsing tokens into an AST and executing the program.
It works with the lexer to provide a complete interpretation pipeline.

Supports:
- Variable declarations (let)
- Print statements
- Basic math operations (+, -, *, /)
- Comparison operators (==, !=, <, >, <=, >=)
- Logical operators (and, or, not)
- If/then/else/end conditionals
- While loops
- For loops
"""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum, auto

from .lexer import Token, TokenType, Lexer


class ParseError(Exception):
    """Exception raised for parser errors."""
    def __init__(self, message: str, token: Optional[Token] = None):
        self.message = message
        self.token = token
        if token:
            super().__init__(f"Line {token.line}, Column {token.column}: {message}")
        else:
            super().__init__(message)


class RuntimeError(Exception):
    """Exception raised for runtime errors."""
    def __init__(self, message: str, line: int = 0):
        self.message = message
        self.line = line
        super().__init__(f"Line {line}: {message}" if line else message)


# AST Node Types

@dataclass
class NumberNode:
    """AST node for number literals."""
    value: float


@dataclass
class StringNode:
    """AST node for string literals."""
    value: str


@dataclass
class IdentifierNode:
    """AST node for variable references."""
    name: str


@dataclass
class BinaryOpNode:
    """AST node for binary operations."""
    left: Any
    operator: str
    right: Any


@dataclass
class UnaryOpNode:
    """AST node for unary operations."""
    operator: str
    operand: Any


@dataclass
class LetNode:
    """AST node for variable declarations."""
    name: str
    value: Any


@dataclass
class PrintNode:
    """AST node for print statements."""
    value: Any


@dataclass
class IfNode:
    """AST node for if statements."""
    condition: Any
    then_block: List[Any]
    else_block: Optional[List[Any]] = None


@dataclass
class WhileNode:
    """AST node for while loops."""
    condition: Any
    body: List[Any]


@dataclass
class ForNode:
    """AST node for for loops."""
    variable: str
    iterable: Any
    body: List[Any]


@dataclass
class ProgramNode:
    """AST node for the entire program."""
    statements: List[Any]


class Parser:
    """
    Parser for SimPL source code.
    
    Converts a list of tokens into an Abstract Syntax Tree (AST).
    Uses recursive descent parsing approach.
    """
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
    
    def current_token(self) -> Token:
        """Get the current token."""
        if self.pos >= len(self.tokens):
            return self.tokens[-1]  # Return EOF
        return self.tokens[self.pos]
    
    def peek_token(self, offset: int = 1) -> Token:
        """Look ahead at tokens without advancing."""
        peek_pos = self.pos + offset
        if peek_pos >= len(self.tokens):
            return self.tokens[-1]  # Return EOF
        return self.tokens[peek_pos]
    
    def advance(self) -> Token:
        """Advance to the next token and return the current one."""
        token = self.current_token()
        self.pos += 1
        return token
    
    def expect(self, token_type: TokenType, message: str = None) -> Token:
        """Expect a specific token type and advance."""
        token = self.current_token()
        if token.type != token_type:
            msg = message or f"Expected {token_type.name}, got {token.type.name}"
            raise ParseError(msg, token)
        return self.advance()
    
    def skip_newlines(self):
        """Skip newline tokens."""
        while self.current_token().type == TokenType.NEWLINE:
            self.advance()
    
    def parse(self) -> ProgramNode:
        """Parse the token stream into an AST."""
        statements = []
        
        while self.current_token().type != TokenType.EOF:
            self.skip_newlines()
            
            if self.current_token().type == TokenType.EOF:
                break
            
            stmt = self.parse_statement()
            if stmt is not None:
                statements.append(stmt)
            
            self.skip_newlines()
        
        return ProgramNode(statements)
    
    def parse_statement(self) -> Any:
        """Parse a single statement."""
        token = self.current_token()
        
        if token.type == TokenType.LET:
            return self.parse_let()
        elif token.type == TokenType.PRINT:
            return self.parse_print()
        elif token.type == TokenType.IF:
            return self.parse_if()
        elif token.type == TokenType.WHILE:
            return self.parse_while()
        elif token.type == TokenType.FOR:
            return self.parse_for()
        else:
            raise ParseError(f"Unexpected token: {token.type.name}", token)
    
    def parse_let(self) -> LetNode:
        """Parse a let statement: let <name> = <expression>"""
        self.advance()  # Skip 'let'
        
        name_token = self.expect(TokenType.IDENTIFIER, "Expected variable name after 'let'")
        name = name_token.value
        
        self.skip_newlines()
        self.expect(TokenType.EQUALS, "Expected '=' after variable name")
        
        self.skip_newlines()
        value = self.parse_expression()
        
        return LetNode(name, value)
    
    def parse_print(self) -> PrintNode:
        """Parse a print statement: print <expression>"""
        self.advance()  # Skip 'print'
        
        self.skip_newlines()
        value = self.parse_expression()
        
        return PrintNode(value)
    
    def parse_if(self) -> IfNode:
        """Parse an if statement: if <condition> then ... else ... end"""
        self.advance()  # Skip 'if'
        
        self.skip_newlines()
        condition = self.parse_expression()
        
        self.skip_newlines()
        self.expect(TokenType.THEN, "Expected 'then' after condition")
        
        self.skip_newlines()
        then_block = self.parse_block()
        
        self.skip_newlines()
        else_block = None
        
        if self.current_token().type == TokenType.ELSE:
            self.advance()  # Skip 'else'
            self.skip_newlines()
            else_block = self.parse_block()
            self.skip_newlines()
        
        self.expect(TokenType.END, "Expected 'end' to close if statement")
        
        return IfNode(condition, then_block, else_block)
    
    def parse_while(self) -> WhileNode:
        """Parse a while loop: while <condition> do ... end"""
        self.advance()  # Skip 'while'
        
        self.skip_newlines()
        condition = self.parse_expression()
        
        self.skip_newlines()
        self.expect(TokenType.DO, "Expected 'do' after while condition")
        
        self.skip_newlines()
        body = self.parse_block()
        
        self.skip_newlines()
        self.expect(TokenType.END, "Expected 'end' to close while loop")
        
        return WhileNode(condition, body)
    
    def parse_for(self) -> ForNode:
        """Parse a for loop: for <var> in <iterable> do ... end"""
        self.advance()  # Skip 'for'
        
        self.skip_newlines()
        var_token = self.expect(TokenType.IDENTIFIER, "Expected variable name after 'for'")
        
        self.skip_newlines()
        self.expect(TokenType.IN, "Expected 'in' after for variable")
        
        self.skip_newlines()
        iterable = self.parse_expression()
        
        self.skip_newlines()
        self.expect(TokenType.DO, "Expected 'do' after for iterable")
        
        self.skip_newlines()
        body = self.parse_block()
        
        self.skip_newlines()
        self.expect(TokenType.END, "Expected 'end' to close for loop")
        
        return ForNode(var_token.value, iterable, body)
    
    def parse_block(self) -> List[Any]:
        """Parse a block of statements until 'end', 'else', or EOF."""
        statements = []
        
        while self.current_token().type not in (
            TokenType.END, TokenType.ELSE, TokenType.EOF
        ):
            self.skip_newlines()
            
            if self.current_token().type in (TokenType.END, TokenType.ELSE, TokenType.EOF):
                break
            
            stmt = self.parse_statement()
            if stmt is not None:
                statements.append(stmt)
        
        return statements
    
    def parse_expression(self) -> Any:
        """Parse an expression (handles operator precedence)."""
        return self.parse_or()
    
    def parse_or(self) -> Any:
        """Parse OR expressions."""
        left = self.parse_and()
        
        while self.current_token().type == TokenType.OR:
            op_token = self.advance()
            right = self.parse_and()
            left = BinaryOpNode(left, 'or', right)
        
        return left
    
    def parse_and(self) -> Any:
        """Parse AND expressions."""
        left = self.parse_comparison()
        
        while self.current_token().type == TokenType.AND:
            op_token = self.advance()
            right = self.parse_comparison()
            left = BinaryOpNode(left, 'and', right)
        
        return left
    
    def parse_comparison(self) -> Any:
        """Parse comparison expressions."""
        left = self.parse_additive()
        
        comparison_ops = {
            TokenType.EQUALS_EQUALS: '==',
            TokenType.NOT_EQUALS: '!=',
            TokenType.LESS_THAN: '<',
            TokenType.GREATER_THAN: '>',
            TokenType.LESS_EQUALS: '<=',
            TokenType.GREATER_EQUALS: '>=',
        }
        
        while self.current_token().type in comparison_ops:
            op_token = self.advance()
            op = comparison_ops[op_token.type]
            right = self.parse_additive()
            left = BinaryOpNode(left, op, right)
        
        return left
    
    def parse_additive(self) -> Any:
        """Parse additive expressions (+, -)."""
        left = self.parse_multiplicative()
        
        while self.current_token().type in (TokenType.PLUS, TokenType.MINUS):
            op_token = self.advance()
            op = '+' if op_token.type == TokenType.PLUS else '-'
            right = self.parse_multiplicative()
            left = BinaryOpNode(left, op, right)
        
        return left
    
    def parse_multiplicative(self) -> Any:
        """Parse multiplicative expressions (*, /)."""
        left = self.parse_unary()
        
        while self.current_token().type in (TokenType.STAR, TokenType.SLASH):
            op_token = self.advance()
            op = '*' if op_token.type == TokenType.STAR else '/'
            right = self.parse_unary()
            left = BinaryOpNode(left, op, right)
        
        return left
    
    def parse_unary(self) -> Any:
        """Parse unary expressions (not, -)."""
        if self.current_token().type == TokenType.NOT:
            op_token = self.advance()
            operand = self.parse_unary()
            return UnaryOpNode('not', operand)
        
        if self.current_token().type == TokenType.MINUS:
            op_token = self.advance()
            operand = self.parse_unary()
            return UnaryOpNode('-', operand)
        
        return self.parse_primary()
    
    def parse_primary(self) -> Any:
        """Parse primary expressions (numbers, strings, identifiers, parenthesized expressions)."""
        token = self.current_token()
        
        if token.type == TokenType.NUMBER:
            self.advance()
            # Convert to float or int
            value = float(token.value)
            if value == int(value):
                value = int(value)
            return NumberNode(value)
        
        if token.type == TokenType.STRING:
            self.advance()
            return StringNode(token.value)
        
        if token.type == TokenType.IDENTIFIER:
            self.advance()
            return IdentifierNode(token.value)
        
        if token.type == TokenType.LPAREN:
            self.advance()  # Skip '('
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN, "Expected ')' after expression")
            return expr
        
        if token.type == TokenType.TRUE:
            self.advance()
            return NumberNode(1)
        
        if token.type == TokenType.FALSE:
            self.advance()
            return NumberNode(0)
        
        raise ParseError(f"Unexpected token: {token.type.name}", token)


class Interpreter:
    """
    Interpreter for SimPL AST.
    
    Executes the AST and manages the program state (variables, etc.).
    """
    
    def __init__(self):
        self.variables: Dict[str, Any] = {}
        self.output: List[str] = []
    
    def interpret(self, ast: ProgramNode) -> List[str]:
        """Execute the AST and return the output."""
        self.variables = {}
        self.output = []
        
        for stmt in ast.statements:
            self.execute(stmt)
        
        return self.output
    
    def execute(self, node: Any):
        """Execute a single AST node."""
        if isinstance(node, LetNode):
            self.execute_let(node)
        elif isinstance(node, PrintNode):
            self.execute_print(node)
        elif isinstance(node, IfNode):
            self.execute_if(node)
        elif isinstance(node, WhileNode):
            self.execute_while(node)
        elif isinstance(node, ForNode):
            self.execute_for(node)
        else:
            raise RuntimeError(f"Unknown statement type: {type(node).__name__}")
    
    def execute_let(self, node: LetNode):
        """Execute a let statement."""
        value = self.evaluate(node.value)
        self.variables[node.name] = value
    
    def execute_print(self, node: PrintNode):
        """Execute a print statement."""
        value = self.evaluate(node.value)
        if isinstance(value, str):
            self.output.append(value)
        elif isinstance(value, bool):
            self.output.append('true' if value else 'false')
        elif value is None:
            self.output.append('')
        else:
            self.output.append(str(value))
    
    def execute_if(self, node: IfNode):
        """Execute an if statement."""
        condition = self.evaluate(node.condition)
        
        if condition:
            for stmt in node.then_block:
                self.execute(stmt)
        elif node.else_block:
            for stmt in node.else_block:
                self.execute(stmt)
    
    def execute_while(self, node: WhileNode):
        """Execute a while loop."""
        while self.evaluate(node.condition):
            for stmt in node.body:
                self.execute(stmt)
    
    def execute_for(self, node: ForNode):
        """Execute a for loop."""
        iterable = self.evaluate(node.iterable)
        
        # Handle range-like iteration (for i in 1 to 10)
        if isinstance(iterable, (int, float)):
            # Simple case: for i in 5 means iterate 0 to 4
            for i in range(int(iterable)):
                self.variables[node.variable] = i
                for stmt in node.body:
                    self.execute(stmt)
        elif isinstance(iterable, (list, tuple)):
            for item in iterable:
                self.variables[node.variable] = item
                for stmt in node.body:
                    self.execute(stmt)
        else:
            raise RuntimeError(f"Cannot iterate over {type(iterable).__name__}")
    
    def evaluate(self, node: Any) -> Any:
        """Evaluate an expression node and return its value."""
        if isinstance(node, NumberNode):
            return node.value
        
        if isinstance(node, StringNode):
            return node.value
        
        if isinstance(node, IdentifierNode):
            if node.name not in self.variables:
                raise RuntimeError(f"Undefined variable: {node.name}")
            return self.variables[node.name]
        
        if isinstance(node, BinaryOpNode):
            return self.evaluate_binary_op(node)
        
        if isinstance(node, UnaryOpNode):
            return self.evaluate_unary_op(node)
        
        raise RuntimeError(f"Unknown expression type: {type(node).__name__}")
    
    def evaluate_binary_op(self, node: BinaryOpNode) -> Any:
        """Evaluate a binary operation."""
        left = self.evaluate(node.left)
        
        # Short-circuit evaluation for logical operators
        if node.operator == 'and':
            if not left:
                return False
            return bool(self.evaluate(node.right))
        
        if node.operator == 'or':
            if left:
                return True
            return bool(self.evaluate(node.right))
        
        right = self.evaluate(node.right)
        
        if node.operator == '+':
            return left + right
        elif node.operator == '-':
            return left - right
        elif node.operator == '*':
            return left * right
        elif node.operator == '/':
            if right == 0:
                raise RuntimeError("Division by zero")
            result = left / right
            # Return int if result is whole number
            if isinstance(result, float) and result == int(result):
                return int(result)
            return result
        elif node.operator == '==':
            return left == right
        elif node.operator == '!=':
            return left != right
        elif node.operator == '<':
            return left < right
        elif node.operator == '>':
            return left > right
        elif node.operator == '<=':
            return left <= right
        elif node.operator == '>=':
            return left >= right
        else:
            raise RuntimeError(f"Unknown operator: {node.operator}")
    
    def evaluate_unary_op(self, node: UnaryOpNode) -> Any:
        """Evaluate a unary operation."""
        operand = self.evaluate(node.operand)
        
        if node.operator == 'not':
            return not operand
        elif node.operator == '-':
            return -operand
        else:
            raise RuntimeError(f"Unknown unary operator: {node.operator}")


def parse_and_execute(source: str) -> List[str]:
    """
    Convenience function to parse and execute SimPL source code.
    
    Args:
        source: The SimPL source code string.
    
    Returns:
        List of output strings from print statements.
    """
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    
    parser = Parser(tokens)
    ast = parser.parse()
    
    interpreter = Interpreter()
    return interpreter.interpret(ast)


if __name__ == '__main__':
    # Test the parser and interpreter
    test_code = '''
let x = 10
let y = 20
print "Hello, World!"
print x + y
print x * y
'''
    
    output = parse_and_execute(test_code)
    
    print("Output:")
    for line in output:
        print(f"  {line}")
