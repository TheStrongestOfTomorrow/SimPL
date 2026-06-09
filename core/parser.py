"""
SimPL Core Parser - Parser and Interpreter for Standard SimPL Syntax

This module handles parsing tokens into an AST and executing the program.
It works with the lexer to provide a complete interpretation pipeline.

Supports:
- Variable declarations (let)
- Print statements
- Basic math operations (+, -, *, /, %)
- Comparison operators (==, !=, <, >, <=, >=)
- Logical operators (and, or, not)
- If/then/else/end conditionals + elif chains
- While loops with break/continue
- For loops
- Repeat/times loops
- Function definitions with parameters and return
- Function calls (built-in and user-defined)
- List literals [1, 2, 3] and indexing arr[0]
- Dict literals {"key": "value"} and indexing dict["key"]
- Index assignment arr[i] = val
- Boolean literals (true, false)
- Try/catch blocks
- Input function
- String concatenation with +
- NPM Bridge via js_eval()
- Many built-in functions for I/O, string, list, and system operations
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


class BreakSignal(Exception):
    """Signal for break statement in loops."""
    pass


class ContinueSignal(Exception):
    """Signal for continue statement in loops."""
    pass


class ReturnSignal(Exception):
    """Signal for return statement in functions."""
    def __init__(self, value: Any = None):
        self.value = value


# ======================================================================
# AST Node Types
# ======================================================================

@dataclass
class NumberNode:
    """AST node for number literals."""
    value: float


@dataclass
class BooleanNode:
    """AST node for boolean literals: true, false."""
    value: bool


@dataclass
class StringNode:
    """AST node for string literals."""
    value: str


@dataclass
class ListNode:
    """AST node for list literals: [1, 2, 3]"""
    elements: List[Any]


@dataclass
class DictNode:
    """AST node for dict literals: {"key": "value"}"""
    pairs: List[Any]  # List of (key_node, value_node) tuples


@dataclass
class IdentifierNode:
    """AST node for variable references."""
    name: str


@dataclass
class IndexNode:
    """AST node for indexing: expr[index]"""
    obj: Any
    index: Any


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
class FunctionCallNode:
    """AST node for function calls: name(arg1, arg2, ...)"""
    name: str
    arguments: List[Any]


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
class InputNode:
    """AST node for input statements: input("prompt")"""
    prompt: Any


@dataclass
class IfNode:
    """AST node for if statements with elif chains."""
    condition: Any
    then_block: List[Any]
    else_block: Optional[List[Any]] = None
    elif_chains: Optional[List[tuple]] = None  # List of (condition, block)


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
class RepeatNode:
    """AST node for repeat loops: repeat N times ... end"""
    count: Any
    body: List[Any]


@dataclass
class FunctionDefNode:
    """AST node for function definitions."""
    name: str
    parameters: List[str]
    body: List[Any]


@dataclass
class ReturnNode:
    """AST node for return statements."""
    value: Any


@dataclass
class BreakNode:
    """AST node for break statements."""
    pass


@dataclass
class ContinueNode:
    """AST node for continue statements."""
    pass


@dataclass
class TryCatchNode:
    """AST node for try/catch blocks: try ... catch ... end"""
    try_block: List[Any]
    catch_block: List[Any]


@dataclass
class ProgramNode:
    """AST node for the entire program."""
    statements: List[Any]


# ======================================================================
# Parser
# ======================================================================

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
            return self.tokens[-1]
        return self.tokens[self.pos]

    def peek_token(self, offset: int = 1) -> Token:
        """Look ahead at tokens without advancing."""
        peek_pos = self.pos + offset
        if peek_pos >= len(self.tokens):
            return self.tokens[-1]
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
        elif token.type == TokenType.REPEAT:
            return self.parse_repeat()
        elif token.type == TokenType.FUNCTION:
            return self.parse_function_def()
        elif token.type == TokenType.RETURN:
            return self.parse_return()
        elif token.type == TokenType.BREAK:
            self.advance()
            return BreakNode()
        elif token.type == TokenType.CONTINUE:
            self.advance()
            return ContinueNode()
        elif token.type == TokenType.INPUT:
            return self.parse_input()
        elif token.type == TokenType.TRY:
            return self.parse_try_catch()
        elif token.type == TokenType.IDENTIFIER:
            return self.parse_assignment_or_call()
        else:
            raise ParseError(f"Unexpected token: {token.type.name}", token)

    # ------------------------------------------------------------------
    # Statement parsers
    # ------------------------------------------------------------------

    def parse_assignment_or_call(self):
        """Parse an assignment or function call statement."""
        name_token = self.current_token()
        name = name_token.value
        self.advance()

        # Check for indexing assignment: name[expr] = value
        if self.current_token().type == TokenType.LBRACKET:
            self.advance()  # Skip [
            index = self.parse_expression()
            self.expect(TokenType.RBRACKET, "Expected ']' after index")
            if self.current_token().type == TokenType.EQUALS:
                self.advance()
                self.skip_newlines()
                value = self.parse_expression()
                # Store both index and RHS value in the LetNode
                # Use ListNode to hold [index, value] so interpreter can evaluate both
                return LetNode(f"__setindex__:{name}", ListNode([index, value]))
            # Otherwise it's just an indexed expression used as a statement
            raise ParseError("Indexed expression used as statement without assignment", name_token)

        # Check for function call: name(args)
        if self.current_token() and self.current_token().type == TokenType.LPAREN:
            args = self._parse_function_args()
            call_node = FunctionCallNode(name, args)
            # Return FunctionCallNode directly — don't wrap in PrintNode
            # The interpreter will execute the function (which handles
            # built-in functions that modify state like push())
            return call_node

        # Check for assignment: name = expression
        if self.current_token() and self.current_token().type == TokenType.EQUALS:
            self.advance()
            self.skip_newlines()
            value = self.parse_expression()
            return LetNode(name, value)

        raise ParseError(f"Unexpected identifier: {name}", name_token)

    def parse_let(self) -> LetNode:
        """Parse: let <name> = <expression>"""
        self.advance()  # Skip 'let'
        name_token = self.expect(TokenType.IDENTIFIER, "Expected variable name after 'let'")
        name = name_token.value
        self.skip_newlines()
        self.expect(TokenType.EQUALS, "Expected '=' after variable name")
        self.skip_newlines()
        value = self.parse_expression()
        return LetNode(name, value)

    def parse_print(self) -> PrintNode:
        """Parse: print <expression>"""
        self.advance()
        self.skip_newlines()
        value = self.parse_expression()
        return PrintNode(value)

    def parse_input(self) -> LetNode:
        """Parse: input("prompt") -> stores result in a variable or uses directly."""
        self.advance()  # Skip 'input'
        # This is handled as a built-in function call in expressions
        # But if used as a statement like: input("Name: ")
        # we parse it as a function call
        if self.current_token().type == TokenType.LPAREN:
            args = self._parse_function_args()
            return PrintNode(FunctionCallNode('input', args))
        raise ParseError("input() requires parentheses with a prompt string")

    def parse_if(self) -> IfNode:
        """Parse: if <condition> then ... elif <condition> then ... else ... end"""
        self.advance()  # Skip 'if'
        self.skip_newlines()
        condition = self.parse_expression()
        self.skip_newlines()
        self.expect(TokenType.THEN, "Expected 'then' after condition")
        self.skip_newlines()
        then_block = self.parse_block()
        self.skip_newlines()

        elif_chains = []
        else_block = None

        # Handle elif chains
        while self.current_token().type == TokenType.ELIF:
            self.advance()  # Skip 'elif'
            self.skip_newlines()
            elif_condition = self.parse_expression()
            self.skip_newlines()
            self.expect(TokenType.THEN, "Expected 'then' after elif condition")
            self.skip_newlines()
            elif_block = self.parse_block()
            self.skip_newlines()
            elif_chains.append((elif_condition, elif_block))

        # Handle else
        if self.current_token().type == TokenType.ELSE:
            self.advance()
            self.skip_newlines()
            else_block = self.parse_block()
            self.skip_newlines()

        self.expect(TokenType.END, "Expected 'end' to close if statement")
        return IfNode(condition, then_block, else_block, elif_chains)

    def parse_while(self) -> WhileNode:
        """Parse: while <condition> do ... end"""
        self.advance()
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
        """Parse: for <var> in <iterable> do ... end"""
        self.advance()
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

    def parse_repeat(self) -> RepeatNode:
        """Parse: repeat <number> times ... end"""
        self.advance()
        self.skip_newlines()
        count = self.parse_expression()
        self.skip_newlines()
        self.expect(TokenType.TIMES, "Expected 'times' after repeat count")
        self.skip_newlines()
        body = self.parse_block()
        self.skip_newlines()
        self.expect(TokenType.END, "Expected 'end' to close repeat loop")
        return RepeatNode(count, body)

    def parse_function_def(self) -> FunctionDefNode:
        """Parse: function <name>(<params>) ... end"""
        self.advance()  # Skip 'function'
        self.skip_newlines()
        name_token = self.expect(TokenType.IDENTIFIER, "Expected function name")
        name = name_token.value

        # Parse parameters
        params = []
        if self.current_token().type == TokenType.LPAREN:
            self.advance()  # Skip (
            self.skip_newlines()
            if self.current_token().type != TokenType.RPAREN:
                param_token = self.expect(TokenType.IDENTIFIER, "Expected parameter name")
                params.append(param_token.value)
                while self.current_token().type == TokenType.COMMA:
                    self.advance()
                    self.skip_newlines()
                    param_token = self.expect(TokenType.IDENTIFIER, "Expected parameter name")
                    params.append(param_token.value)
            self.expect(TokenType.RPAREN, "Expected ')' after parameters")

        self.skip_newlines()
        # Block keyword (then or just body)
        if self.current_token().type == TokenType.THEN:
            self.advance()

        self.skip_newlines()
        body = self.parse_block()
        self.skip_newlines()
        self.expect(TokenType.END, "Expected 'end' to close function definition")

        return FunctionDefNode(name, params, body)

    def parse_return(self) -> ReturnNode:
        """Parse: return <expression>"""
        self.advance()  # Skip 'return'
        self.skip_newlines()
        # Return may or may not have a value
        if self.current_token().type in (TokenType.NEWLINE, TokenType.END, TokenType.EOF):
            return ReturnNode(None)
        value = self.parse_expression()
        return ReturnNode(value)

    def parse_try_catch(self) -> TryCatchNode:
        """Parse: try ... catch ... end"""
        self.advance()  # Skip 'try'
        self.skip_newlines()
        try_block = self.parse_block()
        self.skip_newlines()
        self.expect(TokenType.CATCH, "Expected 'catch' after try block")
        self.skip_newlines()
        catch_block = self.parse_block()
        self.skip_newlines()
        self.expect(TokenType.END, "Expected 'end' to close try/catch")
        return TryCatchNode(try_block, catch_block)

    def parse_block(self) -> List[Any]:
        """Parse a block of statements until 'end', 'else', 'elif', 'catch', or EOF."""
        statements = []
        while self.current_token().type not in (
            TokenType.END, TokenType.ELSE, TokenType.ELIF, TokenType.CATCH, TokenType.EOF
        ):
            self.skip_newlines()
            if self.current_token().type in (TokenType.END, TokenType.ELSE, TokenType.ELIF, TokenType.CATCH, TokenType.EOF):
                break
            stmt = self.parse_statement()
            if stmt is not None:
                statements.append(stmt)
        return statements

    def _parse_function_args(self) -> List[Any]:
        """Parse function call arguments: (arg1, arg2, ...)"""
        self.expect(TokenType.LPAREN, "Expected '(' to start function arguments")
        args = []
        self.skip_newlines()
        if self.current_token().type == TokenType.RPAREN:
            self.advance()
            return args
        args.append(self.parse_expression())
        self.skip_newlines()
        while self.current_token().type == TokenType.COMMA:
            self.advance()
            self.skip_newlines()
            args.append(self.parse_expression())
            self.skip_newlines()
        self.expect(TokenType.RPAREN, "Expected ')' after function arguments")
        return args

    # ------------------------------------------------------------------
    # Expression parsers (operator precedence)
    # ------------------------------------------------------------------

    def parse_expression(self) -> Any:
        return self.parse_or()

    def parse_or(self) -> Any:
        left = self.parse_and()
        while self.current_token().type == TokenType.OR:
            self.advance()
            right = self.parse_and()
            left = BinaryOpNode(left, 'or', right)
        return left

    def parse_and(self) -> Any:
        left = self.parse_comparison()
        while self.current_token().type == TokenType.AND:
            self.advance()
            right = self.parse_comparison()
            left = BinaryOpNode(left, 'and', right)
        return left

    def parse_comparison(self) -> Any:
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
        left = self.parse_multiplicative()
        while self.current_token().type in (TokenType.PLUS, TokenType.MINUS):
            op_token = self.advance()
            op = '+' if op_token.type == TokenType.PLUS else '-'
            right = self.parse_multiplicative()
            left = BinaryOpNode(left, op, right)
        return left

    def parse_multiplicative(self) -> Any:
        left = self.parse_unary()
        while self.current_token().type in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op_token = self.advance()
            op_map = {TokenType.STAR: '*', TokenType.SLASH: '/', TokenType.PERCENT: '%'}
            op = op_map[op_token.type]
            right = self.parse_unary()
            left = BinaryOpNode(left, op, right)
        return left

    def parse_unary(self) -> Any:
        if self.current_token().type == TokenType.NOT:
            self.advance()
            operand = self.parse_unary()
            return UnaryOpNode('not', operand)
        if self.current_token().type == TokenType.MINUS:
            self.advance()
            operand = self.parse_unary()
            return UnaryOpNode('-', operand)
        return self.parse_postfix()

    def parse_postfix(self) -> Any:
        """Parse postfix operations: indexing [i] and function calls (args)."""
        expr = self.parse_primary()

        while True:
            if self.current_token().type == TokenType.LBRACKET:
                self.advance()  # Skip [
                index = self.parse_expression()
                self.expect(TokenType.RBRACKET, "Expected ']' after index")
                expr = IndexNode(expr, index)
            elif self.current_token().type == TokenType.LPAREN and isinstance(expr, IdentifierNode):
                # Function call on an identifier
                args = self._parse_function_args()
                expr = FunctionCallNode(expr.name, args)
            elif self.current_token().type == TokenType.DOT:
                # Dot access: obj.method(args) -> function call
                self.advance()  # Skip .
                method_token = self.expect(TokenType.IDENTIFIER, "Expected method name after '.'")
                if self.current_token().type == TokenType.LPAREN:
                    args = self._parse_function_args()
                    # Convert to a method call: __method__(obj, args...)
                    expr = FunctionCallNode(f"__method__:{method_token.value}", [expr] + args)
                else:
                    # Property access -> treat as index
                    expr = IndexNode(expr, StringNode(method_token.value))
            else:
                break

        return expr

    def parse_primary(self) -> Any:
        """Parse primary expressions."""
        token = self.current_token()

        if token.type == TokenType.NUMBER:
            self.advance()
            value = float(token.value)
            if value == int(value):
                value = int(value)
            return NumberNode(value)

        if token.type == TokenType.BOOLEAN:
            self.advance()
            return BooleanNode(token.value == 'true')

        if token.type == TokenType.STRING:
            self.advance()
            return StringNode(token.value)

        if token.type == TokenType.LBRACKET:
            return self.parse_list_literal()

        if token.type == TokenType.LBRACE:
            return self.parse_dict_literal()

        if token.type == TokenType.IDENTIFIER:
            self.advance()
            return IdentifierNode(token.value)

        if token.type == TokenType.LPAREN:
            self.advance()
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN, "Expected ')' after expression")
            return expr

        if token.type in (TokenType.INPUT,):
            # input() as expression
            self.advance()
            if self.current_token().type == TokenType.LPAREN:
                args = self._parse_function_args()
                return FunctionCallNode('input', args)
            return FunctionCallNode('input', [])

        if token.type == TokenType.FUNCTION:
            # Anonymous function as expression
            return self.parse_function_def()

        raise ParseError(f"Unexpected token: {token.type.name}", token)

    def parse_list_literal(self) -> ListNode:
        """Parse a list literal: [1, 2, 3]"""
        self.advance()  # Skip [
        elements = []
        self.skip_newlines()

        if self.current_token().type == TokenType.RBRACKET:
            self.advance()
            return ListNode(elements)

        elements.append(self.parse_expression())
        self.skip_newlines()

        while self.current_token().type == TokenType.COMMA:
            self.advance()
            self.skip_newlines()
            elements.append(self.parse_expression())
            self.skip_newlines()

        self.expect(TokenType.RBRACKET, "Expected ']' after list elements")
        return ListNode(elements)

    def parse_dict_literal(self) -> DictNode:
        """Parse a dict literal: {"key": "value", "key2": 42}"""
        self.advance()  # Skip {
        pairs = []
        self.skip_newlines()

        if self.current_token().type == TokenType.RBRACE:
            self.advance()
            return DictNode(pairs)

        # Parse first pair
        key = self.parse_expression()
        self.expect(TokenType.COLON, "Expected ':' after dict key")
        self.skip_newlines()
        value = self.parse_expression()
        pairs.append((key, value))
        self.skip_newlines()

        # Parse remaining pairs
        while self.current_token().type == TokenType.COMMA:
            self.advance()
            self.skip_newlines()
            key = self.parse_expression()
            self.expect(TokenType.COLON, "Expected ':' after dict key")
            self.skip_newlines()
            value = self.parse_expression()
            pairs.append((key, value))
            self.skip_newlines()

        self.expect(TokenType.RBRACE, "Expected '}' after dict entries")
        return DictNode(pairs)


# ======================================================================
# Interpreter
# ======================================================================

class Interpreter:
    """
    Interpreter for SimPL AST.

    Executes the AST and manages the program state (variables, functions).
    Includes built-in functions and the NPM Bridge via js_eval.
    """

    # Signal exceptions for control flow
    _BreakSignal = BreakSignal
    _ContinueSignal = ContinueSignal
    _ReturnSignal = ReturnSignal

    def __init__(self):
        self.variables: Dict[str, Any] = {}
        self.output: List[str] = []
        self._functions: Dict[str, FunctionDefNode] = {}

    def interpret(self, ast: ProgramNode) -> List[str]:
        """Execute the AST and return the output."""
        self.variables = {}
        self.output = []
        self._functions = {}

        for stmt in ast.statements:
            self.execute(stmt)

        return self.output

    # ------------------------------------------------------------------
    # Statement execution
    # ------------------------------------------------------------------

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
        elif isinstance(node, RepeatNode):
            self.execute_repeat(node)
        elif isinstance(node, FunctionDefNode):
            self._functions[node.name] = node
        elif isinstance(node, ReturnNode):
            value = self.evaluate(node.value) if node.value else None
            raise ReturnSignal(value)
        elif isinstance(node, BreakNode):
            raise BreakSignal()
        elif isinstance(node, ContinueNode):
            raise ContinueSignal()
        elif isinstance(node, TryCatchNode):
            self.execute_try_catch(node)
        elif isinstance(node, FunctionCallNode):
            # Bare function call as a statement (e.g., push(list, val))
            self.evaluate_function_call(node)
        else:
            raise RuntimeError(f"Unknown statement type: {type(node).__name__}")

    def execute_let(self, node: LetNode):
        """Execute a let statement."""
        # Check for special __setindex__ pattern (index assignment: arr[i] = val)
        if node.name.startswith("__setindex__:"):
            var_name = node.name.split(":", 1)[1]
            if var_name not in self.variables:
                raise RuntimeError(f"Undefined variable: {var_name}")
            # node.value is a ListNode containing [index, value] AST nodes
            pair = self.evaluate(node.value)
            index_val = pair[0]
            value_val = pair[1]
            try:
                self.variables[var_name][index_val] = value_val
            except (IndexError, KeyError, TypeError) as e:
                raise RuntimeError(f"Index error: cannot set [{index_val}] on {var_name}")
            return
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
            self.output.append('null')
        elif isinstance(value, list):
            self.output.append(self._format_list(value))
        elif isinstance(value, dict):
            self.output.append(self._format_dict(value))
        else:
            self.output.append(str(value))

    def _format_list(self, lst: list) -> str:
        """Format a list for printing."""
        items = []
        for item in lst:
            if isinstance(item, str):
                items.append(item)
            elif isinstance(item, bool):
                items.append('true' if item else 'false')
            elif isinstance(item, list):
                items.append(self._format_list(item))
            elif isinstance(item, dict):
                items.append(self._format_dict(item))
            else:
                items.append(str(item))
        return '[' + ', '.join(items) + ']'

    def _format_dict(self, d: dict) -> str:
        """Format a dict for printing."""
        import json
        return json.dumps(d, default=str)

    def execute_if(self, node: IfNode):
        """Execute an if/elif/else statement."""
        if self.evaluate(node.condition):
            for stmt in node.then_block:
                self.execute(stmt)
            return

        # Try elif chains
        if node.elif_chains:
            for elif_cond, elif_block in node.elif_chains:
                if self.evaluate(elif_cond):
                    for stmt in elif_block:
                        self.execute(stmt)
                    return

        # Try else
        if node.else_block:
            for stmt in node.else_block:
                self.execute(stmt)

    def execute_while(self, node: WhileNode):
        """Execute a while loop with break/continue support."""
        while self.evaluate(node.condition):
            try:
                for stmt in node.body:
                    self.execute(stmt)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def execute_for(self, node: ForNode):
        """Execute a for loop with break/continue."""
        iterable = self.evaluate(node.iterable)

        if isinstance(iterable, (int, float)):
            items = list(range(int(iterable)))
        elif isinstance(iterable, (list, tuple)):
            items = iterable
        elif isinstance(iterable, str):
            items = list(iterable)
        else:
            raise RuntimeError(f"Cannot iterate over {type(iterable).__name__}")

        for item in items:
            self.variables[node.variable] = item
            try:
                for stmt in node.body:
                    self.execute(stmt)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def execute_repeat(self, node: RepeatNode):
        """Execute a repeat loop with break/continue."""
        count = int(self.evaluate(node.count))
        for _ in range(count):
            try:
                for stmt in node.body:
                    self.execute(stmt)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def execute_try_catch(self, node: TryCatchNode):
        """Execute a try/catch block."""
        try:
            for stmt in node.try_block:
                self.execute(stmt)
        except (BreakSignal, ContinueSignal, ReturnSignal):
            raise  # Re-raise control flow signals
        except Exception as e:
            # Store the error message in a special variable
            self.variables['__error__'] = str(e)
            for stmt in node.catch_block:
                self.execute(stmt)

    # ------------------------------------------------------------------
    # Expression evaluation
    # ------------------------------------------------------------------

    def evaluate(self, node: Any) -> Any:
        """Evaluate an expression node and return its value."""
        if isinstance(node, NumberNode):
            return node.value

        if isinstance(node, BooleanNode):
            return node.value

        if isinstance(node, StringNode):
            return node.value

        if isinstance(node, ListNode):
            return [self.evaluate(el) for el in node.elements]

        if isinstance(node, DictNode):
            result = {}
            for key_node, value_node in node.pairs:
                key = self.evaluate(key_node)
                value = self.evaluate(value_node)
                result[key] = value
            return result

        if isinstance(node, IdentifierNode):
            if node.name in self._functions:
                return node.name  # Return function name as callable reference
            if node.name not in self.variables:
                raise RuntimeError(f"Undefined variable: {node.name}")
            return self.variables[node.name]

        if isinstance(node, IndexNode):
            obj = self.evaluate(node.obj)
            index = self.evaluate(node.index)
            try:
                if isinstance(obj, dict):
                    return obj.get(index, obj.get(str(index)))
                return obj[index]
            except (IndexError, KeyError, TypeError):
                raise RuntimeError(f"Index error: cannot access [{index}]")

        if isinstance(node, BinaryOpNode):
            return self.evaluate_binary_op(node)

        if isinstance(node, UnaryOpNode):
            return self.evaluate_unary_op(node)

        if isinstance(node, FunctionCallNode):
            return self.evaluate_function_call(node)

        raise RuntimeError(f"Unknown expression type: {type(node).__name__}")

    def evaluate_binary_op(self, node: BinaryOpNode) -> Any:
        """Evaluate a binary operation."""
        left = self.evaluate(node.left)

        if node.operator == 'and':
            return bool(left and self.evaluate(node.right))
        if node.operator == 'or':
            return bool(left or self.evaluate(node.right))

        right = self.evaluate(node.right)

        if node.operator == '+':
            if isinstance(left, str) or isinstance(right, str):
                return str(left) + str(right)
            return left + right
        elif node.operator == '-':
            return left - right
        elif node.operator == '*':
            return left * right
        elif node.operator == '/':
            if right == 0:
                raise RuntimeError("Division by zero")
            result = left / right
            if isinstance(result, float) and result == int(result):
                return int(result)
            return result
        elif node.operator == '%':
            if right == 0:
                raise RuntimeError("Modulo by zero")
            return left % right
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
        raise RuntimeError(f"Unknown unary operator: {node.operator}")

    # ------------------------------------------------------------------
    # Function evaluation
    # ------------------------------------------------------------------

    def evaluate_function_call(self, node: FunctionCallNode) -> Any:
        """Evaluate a function call (built-in or user-defined)."""
        func_name = node.name
        args = [self.evaluate(arg) for arg in node.arguments]

        # Built-in functions
        builtin_map = {
            'js_eval': self._builtin_js_eval,
            'str': self._builtin_str,
            'int': self._builtin_int,
            'float': self._builtin_float,
            'len': self._builtin_len,
            'type': self._builtin_type,
            'abs': self._builtin_abs,
            'min': self._builtin_min,
            'max': self._builtin_max,
            'round': self._builtin_round,
            'input': self._builtin_input,
            'push': self._builtin_push,
            'pop': self._builtin_pop,
            'range': self._builtin_range,
            'keys': self._builtin_keys,
            'values': self._builtin_values,
            'split': self._builtin_split,
            'join': self._builtin_join,
            'replace': self._builtin_replace,
            'upper': self._builtin_upper,
            'lower': self._builtin_lower,
            'trim': self._builtin_trim,
            'number': self._builtin_int,
            'string': self._builtin_str,
            'floor': self._builtin_floor,
            'ceil': self._builtin_ceil,
            'sqrt': self._builtin_sqrt,
            'pow': self._builtin_pow,
            'random': self._builtin_random,
            # New built-in functions
            'read_file': self._builtin_read_file,
            'write_file': self._builtin_write_file,
            'append_file': self._builtin_append_file,
            'reverse': self._builtin_reverse,
            'sort': self._builtin_sort,
            'contains': self._builtin_contains,
            'sleep': self._builtin_sleep,
            'time': self._builtin_time,
            'env': self._builtin_env,
            'shell': self._builtin_shell,
            'bool': self._builtin_bool,
            'starts_with': self._builtin_starts_with,
            'ends_with': self._builtin_ends_with,
            'slice': self._builtin_slice,
            'index_of': self._builtin_index_of,
            'to_number': self._builtin_to_number,
        }

        # Method calls (__method__:name pattern)
        if func_name.startswith("__method__:"):
            method_name = func_name.split(":", 1)[1]
            method_map = {
                'upper': self._builtin_upper,
                'lower': self._builtin_lower,
                'trim': self._builtin_trim,
                'split': self._builtin_split,
                'replace': self._builtin_replace,
                'push': self._builtin_push,
                'pop': self._builtin_pop,
                'join': self._builtin_join,
                'keys': self._builtin_keys,
                'values': self._builtin_values,
                'contains': self._builtin_contains,
                'reverse': self._builtin_reverse,
                'sort': self._builtin_sort,
                'starts_with': self._builtin_starts_with,
                'ends_with': self._builtin_ends_with,
                'index_of': self._builtin_index_of,
            }
            if method_name in method_map:
                return method_map[method_name](args)
            raise RuntimeError(f"Unknown method: {method_name}")

        if func_name in builtin_map:
            return builtin_map[func_name](args)

        # User-defined functions
        if func_name in self._functions:
            func_def = self._functions[func_name]

            # Validate argument count
            if len(args) != len(func_def.parameters):
                raise RuntimeError(
                    f"Function '{func_name}' expects {len(func_def.parameters)} "
                    f"arguments, got {len(args)}"
                )

            # --- Proper scoping: save/restore the entire variable + function state ---
            # This is essential for recursion: each call gets its own scope.
            saved_vars = self.variables.copy()
            saved_funcs = dict(self._functions)

            # Bind parameters in a fresh scope (inherit outer vars but params take priority)
            for param, arg_val in zip(func_def.parameters, args):
                self.variables[param] = arg_val

            # Execute function body
            result = None
            try:
                for stmt in func_def.body:
                    self.execute(stmt)
            except ReturnSignal as ret:
                result = ret.value

            # Restore the caller's scope
            self.variables = saved_vars
            self._functions = saved_funcs

            return result

        raise RuntimeError(f"Undefined function: {func_name}")

    # ------------------------------------------------------------------
    # Built-in functions
    # ------------------------------------------------------------------

    def _builtin_js_eval(self, args):
        if len(args) != 1:
            raise RuntimeError("js_eval() expects exactly 1 argument")
        if not isinstance(args[0], str):
            raise RuntimeError("js_eval() argument must be a string")
        from .js_bridge import js_eval as _js_eval, JSBridgeError
        try:
            return _js_eval(args[0])
        except JSBridgeError as e:
            raise RuntimeError(e.message)
        except FileNotFoundError:
            raise RuntimeError(
                "🛑 Error: NPM Bridge requires Node.js to be installed. "
                "💡 Tip: Download it from nodejs.org to use JS libraries!"
            )

    def _builtin_str(self, args):
        if len(args) != 1:
            raise RuntimeError("str() expects exactly 1 argument")
        v = args[0]
        if isinstance(v, bool):
            return 'true' if v else 'false'
        if isinstance(v, list):
            return self._format_list(v)
        if isinstance(v, dict):
            return self._format_dict(v)
        return str(v)

    def _builtin_int(self, args):
        if len(args) != 1:
            raise RuntimeError("int() expects exactly 1 argument")
        try:
            return int(float(args[0])) if isinstance(args[0], str) else int(args[0])
        except (ValueError, TypeError):
            raise RuntimeError(f"Cannot convert to int: {args[0]!r}")

    def _builtin_float(self, args):
        if len(args) != 1:
            raise RuntimeError("float() expects exactly 1 argument")
        try:
            return float(args[0])
        except (ValueError, TypeError):
            raise RuntimeError(f"Cannot convert to float: {args[0]!r}")

    def _builtin_len(self, args):
        if len(args) != 1:
            raise RuntimeError("len() expects exactly 1 argument")
        try:
            return len(args[0])
        except TypeError:
            raise RuntimeError(f"Cannot get length of {type(args[0]).__name__}")

    def _builtin_type(self, args):
        if len(args) != 1:
            raise RuntimeError("type() expects exactly 1 argument")
        v = args[0]
        if isinstance(v, bool): return 'boolean'
        if isinstance(v, int): return 'number'
        if isinstance(v, float): return 'number'
        if isinstance(v, str): return 'string'
        if isinstance(v, list): return 'list'
        if isinstance(v, dict): return 'object'
        if v is None: return 'null'
        return type(v).__name__

    def _builtin_abs(self, args):
        if len(args) != 1: raise RuntimeError("abs() expects 1 argument")
        return abs(args[0])

    def _builtin_min(self, args):
        if len(args) < 1: raise RuntimeError("min() expects at least 1 argument")
        if len(args) == 1 and isinstance(args[0], list):
            return min(args[0])
        return min(args)

    def _builtin_max(self, args):
        if len(args) < 1: raise RuntimeError("max() expects at least 1 argument")
        if len(args) == 1 and isinstance(args[0], list):
            return max(args[0])
        return max(args)

    def _builtin_round(self, args):
        if len(args) < 1 or len(args) > 2:
            raise RuntimeError("round() expects 1 or 2 arguments")
        if len(args) == 2:
            return round(args[0], int(args[1]))
        return round(args[0])

    def _builtin_input(self, args):
        """Read input from the user."""
        prompt = ""
        if len(args) >= 1:
            prompt = str(args[0])
        try:
            return input(prompt)
        except EOFError:
            return ""

    def _builtin_push(self, args):
        """push(list, value) - add value to end of list."""
        if len(args) != 2:
            raise RuntimeError("push() expects 2 arguments: push(list, value)")
        lst, val = args
        if not isinstance(lst, list):
            raise RuntimeError("push() first argument must be a list")
        lst.append(val)
        return lst

    def _builtin_pop(self, args):
        """pop(list) - remove and return last element."""
        if len(args) != 1:
            raise RuntimeError("pop() expects 1 argument")
        if not isinstance(args[0], list):
            raise RuntimeError("pop() argument must be a list")
        if not args[0]:
            raise RuntimeError("pop() on empty list")
        return args[0].pop()

    def _builtin_range(self, args):
        """range(n) or range(start, end) or range(start, end, step)."""
        if len(args) == 1:
            return list(range(int(args[0])))
        elif len(args) == 2:
            return list(range(int(args[0]), int(args[1])))
        elif len(args) == 3:
            return list(range(int(args[0]), int(args[1]), int(args[2])))
        raise RuntimeError("range() expects 1-3 arguments")

    def _builtin_keys(self, args):
        if len(args) != 1: raise RuntimeError("keys() expects 1 argument")
        if isinstance(args[0], dict):
            return list(args[0].keys())
        raise RuntimeError("keys() argument must be an object")

    def _builtin_values(self, args):
        if len(args) != 1: raise RuntimeError("values() expects 1 argument")
        if isinstance(args[0], dict):
            return list(args[0].values())
        raise RuntimeError("values() argument must be an object")

    def _builtin_split(self, args):
        if len(args) == 1:
            return args[0].split()
        elif len(args) == 2:
            return args[0].split(args[1])
        raise RuntimeError("split() expects 1-2 arguments")

    def _builtin_join(self, args):
        if len(args) == 2:
            return args[0].join([str(x) for x in args[1]])
        raise RuntimeError("join() expects 2 arguments: join(separator, list)")

    def _builtin_replace(self, args):
        if len(args) == 3:
            return args[0].replace(args[1], args[2])
        raise RuntimeError("replace() expects 3 arguments: replace(string, old, new)")

    def _builtin_upper(self, args):
        if len(args) != 1: raise RuntimeError("upper() expects 1 argument")
        return str(args[0]).upper()

    def _builtin_lower(self, args):
        if len(args) != 1: raise RuntimeError("lower() expects 1 argument")
        return str(args[0]).lower()

    def _builtin_trim(self, args):
        if len(args) != 1: raise RuntimeError("trim() expects 1 argument")
        return str(args[0]).strip()

    def _builtin_floor(self, args):
        if len(args) != 1: raise RuntimeError("floor() expects 1 argument")
        import math
        return int(math.floor(float(args[0])))

    def _builtin_ceil(self, args):
        if len(args) != 1: raise RuntimeError("ceil() expects 1 argument")
        import math
        return int(math.ceil(float(args[0])))

    def _builtin_sqrt(self, args):
        if len(args) != 1: raise RuntimeError("sqrt() expects 1 argument")
        import math
        return math.sqrt(float(args[0]))

    def _builtin_pow(self, args):
        if len(args) != 2: raise RuntimeError("pow() expects 2 arguments")
        return args[0] ** args[1]

    def _builtin_random(self, args):
        """random() or random(max) or random(min, max)."""
        import random as _random
        if len(args) == 0:
            return _random.random()
        elif len(args) == 1:
            return _random.randint(0, int(args[0]) - 1)
        elif len(args) == 2:
            return _random.randint(int(args[0]), int(args[1]))
        raise RuntimeError("random() expects 0-2 arguments")

    # ------------------------------------------------------------------
    # New built-in functions
    # ------------------------------------------------------------------

    def _builtin_read_file(self, args):
        """read_file(path) - reads a file and returns its content as string."""
        if len(args) != 1:
            raise RuntimeError("read_file() expects 1 argument")
        try:
            with open(args[0], 'r') as f:
                return f.read()
        except FileNotFoundError:
            raise RuntimeError(f"File not found: {args[0]}")
        except IOError as e:
            raise RuntimeError(f"Error reading file: {e}")

    def _builtin_write_file(self, args):
        """write_file(path, content) - writes content to a file."""
        if len(args) != 2:
            raise RuntimeError("write_file() expects 2 arguments: write_file(path, content)")
        try:
            with open(args[0], 'w') as f:
                f.write(str(args[1]))
            return True
        except IOError as e:
            raise RuntimeError(f"Error writing file: {e}")

    def _builtin_append_file(self, args):
        """append_file(path, content) - appends content to a file."""
        if len(args) != 2:
            raise RuntimeError("append_file() expects 2 arguments: append_file(path, content)")
        try:
            with open(args[0], 'a') as f:
                f.write(str(args[1]))
            return True
        except IOError as e:
            raise RuntimeError(f"Error appending to file: {e}")

    def _builtin_reverse(self, args):
        """reverse(list_or_string) - reverses a list or string."""
        if len(args) != 1:
            raise RuntimeError("reverse() expects 1 argument")
        if isinstance(args[0], list):
            return list(reversed(args[0]))
        elif isinstance(args[0], str):
            return args[0][::-1]
        raise RuntimeError("reverse() argument must be a list or string")

    def _builtin_sort(self, args):
        """sort(list) - sorts a list."""
        if len(args) != 1:
            raise RuntimeError("sort() expects 1 argument")
        if isinstance(args[0], list):
            try:
                return sorted(args[0])
            except TypeError:
                raise RuntimeError("sort() list elements must be comparable")
        raise RuntimeError("sort() argument must be a list")

    def _builtin_contains(self, args):
        """contains(list_or_string, item) - checks if item exists."""
        if len(args) != 2:
            raise RuntimeError("contains() expects 2 arguments: contains(collection, item)")
        return args[1] in args[0]

    def _builtin_sleep(self, args):
        """sleep(seconds) - pauses execution."""
        if len(args) != 1:
            raise RuntimeError("sleep() expects 1 argument")
        import time as _time
        _time.sleep(float(args[0]))
        return None

    def _builtin_time(self, args):
        """time() - returns current unix timestamp."""
        if len(args) != 0:
            raise RuntimeError("time() expects 0 arguments")
        import time as _time
        return _time.time()

    def _builtin_env(self, args):
        """env(name) - gets environment variable."""
        if len(args) != 1:
            raise RuntimeError("env() expects 1 argument")
        import os
        return os.environ.get(args[0], '')

    def _builtin_shell(self, args):
        """shell(command) - runs a shell command and returns output."""
        if len(args) != 1:
            raise RuntimeError("shell() expects 1 argument")
        import subprocess
        try:
            result = subprocess.run(
                args[0], shell=True, capture_output=True, text=True, timeout=30
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            raise RuntimeError("shell() command timed out")
        except Exception as e:
            raise RuntimeError(f"shell() error: {e}")

    def _builtin_bool(self, args):
        """bool(value) - converts to boolean."""
        if len(args) != 1:
            raise RuntimeError("bool() expects 1 argument")
        return bool(args[0])

    def _builtin_starts_with(self, args):
        """starts_with(s, prefix) - checks if string starts with prefix."""
        if len(args) != 2:
            raise RuntimeError("starts_with() expects 2 arguments: starts_with(string, prefix)")
        return str(args[0]).startswith(str(args[1]))

    def _builtin_ends_with(self, args):
        """ends_with(s, suffix) - checks if string ends with suffix."""
        if len(args) != 2:
            raise RuntimeError("ends_with() expects 2 arguments: ends_with(string, suffix)")
        return str(args[0]).endswith(str(args[1]))

    def _builtin_slice(self, args):
        """slice(list_or_string, start, end) - slices a list or string."""
        if len(args) < 2 or len(args) > 3:
            raise RuntimeError("slice() expects 2-3 arguments: slice(collection, start, end)")
        obj = args[0]
        start = int(args[1])
        end = int(args[2]) if len(args) == 3 else len(obj)
        try:
            return obj[start:end]
        except (TypeError, IndexError):
            raise RuntimeError("slice() cannot slice the given collection")

    def _builtin_index_of(self, args):
        """index_of(list_or_string, item) - finds index of item."""
        if len(args) != 2:
            raise RuntimeError("index_of() expects 2 arguments: index_of(collection, item)")
        try:
            return args[0].index(args[1])
        except ValueError:
            return -1
        except AttributeError:
            raise RuntimeError("index_of() argument must be a list or string")

    def _builtin_to_number(self, args):
        """to_number(s) - converts string to number (int or float)."""
        if len(args) != 1:
            raise RuntimeError("to_number() expects 1 argument")
        val = args[0]
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return val
        try:
            # Try int first, then float
            int_val = int(val)
            return int_val
        except (ValueError, TypeError):
            pass
        try:
            return float(val)
        except (ValueError, TypeError):
            raise RuntimeError(f"Cannot convert to number: {val!r}")


# ======================================================================
# Convenience
# ======================================================================

def parse_and_execute(source: str) -> List[str]:
    """
    Convenience function to parse and execute SimPL source code.

    Creates a Lexer, Parser, and Interpreter pipeline and returns
    the output lines from execution.

    Args:
        source: The SimPL source code string.

    Returns:
        List of output strings from the program execution.
    """
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    interpreter = Interpreter()
    return interpreter.interpret(ast)


if __name__ == '__main__':
    test_code = '''
let x = 10
let y = 20
print "Hello, World!"
print x + y

# Test boolean
let flag = true
print flag

# Test dict
let d = {"name": "SimPL", "version": 1}
print d

# Test list index assignment
let arr = [1, 2, 3]
arr[0] = 99
print arr

# Test try/catch
try
    let z = 1 / 0
catch
    print "Caught an error!"
end
'''
    output = parse_and_execute(test_code)
    print("Output:")
    for line in output:
        print(f"  {line}")
