"""
SimPL Core Package

Exports the main components of the SimPL interpreter.
"""

from .lexer import Lexer, tokenize, Token, TokenType, FlavorNormalizer, MixedFlavorError
from .parser import (
    Parser, Interpreter, parse_and_execute,
    ParseError, RuntimeError as SimPLRuntimeError,
    FunctionCallNode, BreakSignal, ContinueSignal, ReturnSignal,
)
from .js_bridge import js_eval, JSBridgeError, is_node_available, get_node_version
from .helper import SmartHelper, handle_error, get_helper
