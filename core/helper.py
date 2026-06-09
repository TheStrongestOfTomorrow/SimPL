"""
SimPL Smart Helper - Local Rule-Based Error Detection

This module provides friendly, human-readable error messages and hints
instead of raw stack traces. It uses a rule-based system to detect
common programming mistakes and provide helpful suggestions.

Features:
- Catches common syntax errors
- Provides type mismatch hints
- Suggests fixes for undefined variables
- Detects potential logic errors
"""

import re
from typing import Any, Dict, List, Optional, Tuple


class ErrorCategory:
    """Categories of errors for better organization."""
    SYNTAX = "Syntax Error"
    TYPE_MISMATCH = "Type Mismatch"
    UNDEFINED_VARIABLE = "Undefined Variable"
    DIVISION_ERROR = "Division Error"
    LOGIC_ERROR = "Logic Error"
    RUNTIME_ERROR = "Runtime Error"
    FLAVOR_ERROR = "Flavor Mix Error"
    UNKNOWN = "Unknown Error"


class HelpfulTip:
    """Represents a helpful tip for fixing an error."""
    
    def __init__(self, title: str, explanation: str, suggestion: str, example: str = None):
        self.title = title
        self.explanation = explanation
        self.suggestion = suggestion
        self.example = example
    
    def __str__(self) -> str:
        result = f"💡 {self.title}\n"
        result += f"   {self.explanation}\n"
        result += f"   → {self.suggestion}"
        if self.example:
            result += f"\n   Example: {self.example}"
        return result


class SmartHelper:
    """
    Smart Helper for SimPL - Provides friendly error messages.
    
    Uses pattern matching and rule-based detection to identify
    common programming mistakes and provide helpful suggestions.
    """
    
    # Pattern rules for detecting specific error types
    ERROR_PATTERNS = {
        'missing_then': [
            r"Expected.*then.*got",
            r"if.*condition.*missing.*then",
        ],
        'missing_end': [
            r"Expected.*end",
            r"block.*not.*closed",
        ],
        'missing_equals': [
            r"Expected.*=.*after",
            r"let.*missing.*=",
        ],
        'undefined_variable': [
            r"Undefined variable",
            r"variable.*not.*defined",
        ],
        'type_mismatch_add': [
            r"can.*only.*concatenate.*str.*not",
            r"unsupported operand type.*\+.*int.*str",
        ],
        'type_mismatch_math': [
            r"unsupported operand type.*[-*/].*str",
        ],
        'division_by_zero': [
            r"[Dd]ivision by zero",
            r"[Dd]ivide by zero",
        ],
        'invalid_syntax': [
            r"invalid syntax",
            r"unexpected token",
        ],
        'missing_parenthesis': [
            r"expected.*\)",
            r"unclosed.*parenthesis",
        ],
        'string_quotes': [
            r"unterminated string",
            r"mismatched quotes",
        ],
        'mixed_flavors': [
            r"Mixed syntax flavors",
            r"mixed.*flavor",
            r"started.*with.*C-style.*closed.*with.*end",
            r"started.*with.*Python.*closed.*with.*}",
        ],
    }
    
    # Helpful tips for each error category
    TIPS = {
        'mixed_flavors': HelpfulTip(
            "Mixed syntax flavors detected",
            "You mixed C-style '{...}' with Standard 'end' or Python-style ':' with '}'. "
            "SimPL supports all three flavors, but you must stick to one per block.",
            "Pick ONE flavor per block and use it consistently.",
            "# Standard:  if x > 5 then ... end\n"
            "# C-style:   if (x > 5) { ... }\n"
            "# Python:    if x > 5:\n"
            "#               ..."
        ),
        'missing_then': HelpfulTip(
            "Missing 'then' keyword",
            "In SimPL, every 'if' statement needs a 'then' keyword after the condition.",
            "Add 'then' after your if condition.",
            "if x > 5 then print \"x is big\" end"
        ),
        'missing_end': HelpfulTip(
            "Missing 'end' keyword",
            "Blocks in SimPL (if/while/for) must be closed with 'end'.",
            "Add 'end' at the end of your block.",
            "if x > 5 then\n    print x\nend"
        ),
        'missing_equals': HelpfulTip(
            "Missing '=' in variable declaration",
            "When using 'let', you need '=' to assign a value.",
            "Make sure to include '=' between the variable name and value.",
            "let x = 10"
        ),
        'undefined_variable': HelpfulTip(
            "Using a variable before defining it",
            "You tried to use a variable that hasn't been created yet.",
            "Use 'let' to define the variable before using it, or check for typos.",
            "let score = 0\nprint score"
        ),
        'type_mismatch_add': HelpfulTip(
            "Mixing text and numbers",
            "You can't directly add text (strings) and numbers together.",
            "Convert numbers to text using string formatting, or use only numbers for math.",
            'let age = 25\nprint "I am " + age + " years old"  # Wrong!\nprint "I am " + age + " years old"  # Convert age first'
        ),
        'type_mismatch_math': HelpfulTip(
            "Math on text doesn't work",
            "You can only do math (+, -, *, /) with numbers, not text.",
            "Make sure both values are numbers before doing math.",
            "let x = 10\nlet y = 20\nprint x * y  # Works!"
        ),
        'division_by_zero': HelpfulTip(
            "Can't divide by zero",
            "Dividing by zero is mathematically undefined and causes an error.",
            "Check that the divisor is not zero before dividing.",
            "if divisor != 0 then\n    result = dividend / divisor\nend"
        ),
        'invalid_syntax': HelpfulTip(
            "Syntax error detected",
            "The code doesn't follow SimPL's grammar rules.",
            "Check for typos, missing keywords, or incorrect order of elements.",
            "let x = 5  # Correct\nx = 5  # Wrong - missing 'let'"
        ),
        'missing_parenthesis': HelpfulTip(
            "Missing closing parenthesis",
            "Every opening '(' needs a matching ')'.",
            "Count your parentheses and make sure they're balanced.",
            "print (x + y) * z"
        ),
        'string_quotes': HelpfulTip(
            "String not properly closed",
            "Strings must start and end with double quotes (\").",
            "Make sure every string has both opening and closing quotes.",
            'print "Hello, World!"'
        ),
    }
    
    def __init__(self):
        self.error_history: List[Dict[str, Any]] = []
    
    def analyze_error(self, error_message: str, context: str = None) -> Dict[str, Any]:
        """
        Analyze an error message and provide helpful information.
        
        Args:
            error_message: The raw error message from the interpreter.
            context: Optional source code context where the error occurred.
        
        Returns:
            Dictionary containing error analysis and suggestions.
        """
        result = {
            'original_error': error_message,
            'category': ErrorCategory.UNKNOWN,
            'friendly_message': self._get_friendly_message(error_message),
            'tip': None,
            'context': context,
        }
        
        # Detect error type using patterns
        detected_type = self._detect_error_type(error_message)
        
        if detected_type and detected_type in self.TIPS:
            result['tip'] = str(self.TIPS[detected_type])
            result['category'] = self._get_category_for_type(detected_type)
        
        # Store in history
        self.error_history.append(result)
        
        return result
    
    def _detect_error_type(self, error_message: str) -> Optional[str]:
        """Detect the type of error based on pattern matching."""
        error_lower = error_message.lower()
        
        for error_type, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, error_lower):
                    return error_type
        
        return None
    
    def _get_category_for_type(self, error_type: str) -> str:
        """Map error type to error category."""
        category_map = {
            'missing_then': ErrorCategory.SYNTAX,
            'missing_end': ErrorCategory.SYNTAX,
            'missing_equals': ErrorCategory.SYNTAX,
            'undefined_variable': ErrorCategory.UNDEFINED_VARIABLE,
            'type_mismatch_add': ErrorCategory.TYPE_MISMATCH,
            'type_mismatch_math': ErrorCategory.TYPE_MISMATCH,
            'division_by_zero': ErrorCategory.DIVISION_ERROR,
            'invalid_syntax': ErrorCategory.SYNTAX,
            'missing_parenthesis': ErrorCategory.SYNTAX,
            'string_quotes': ErrorCategory.SYNTAX,
            'mixed_flavors': ErrorCategory.FLAVOR_ERROR,
        }
        return category_map.get(error_type, ErrorCategory.UNKNOWN)
    
    def _get_friendly_message(self, error_message: str) -> str:
        """Convert technical error message to friendly language."""
        # Common transformations
        friendly_transforms = [
            (r"Line (\d+), Column (\d+): ", r"Problem at line \1, column \2: "),
            (r"Expected.*got.*", "Something unexpected was found here."),
            (r"Undefined variable: (\w+)", r"The variable '\1' hasn't been defined yet."),
            (r"Division by zero", "You can't divide something by zero - it's like trying to share cookies with nobody!"),
            (r"unterminated string", "A text string wasn't finished - did you forget a closing quote?"),
            (r"unexpected token", "There's something here that doesn't belong."),
        ]
        
        friendly = error_message
        for pattern, replacement in friendly_transforms:
            friendly = re.sub(pattern, replacement, friendly, flags=re.IGNORECASE)
        
        return friendly
    
    def format_error_report(self, error_message: str, source_code: str = None, 
                           line_number: int = None) -> str:
        """
        Create a formatted, user-friendly error report.
        
        Args:
            error_message: The raw error message.
            source_code: Optional source code for context.
            line_number: Optional line number where error occurred.
        
        Returns:
            Formatted error report string.
        """
        analysis = self.analyze_error(error_message)
        
        report = []
        report.append("╔════════════════════════════════════════╗")
        report.append("║       SimPL Error Report              ║")
        report.append("╚════════════════════════════════════════╝")
        report.append("")
        
        # Category
        report.append(f"📁 Category: {analysis['category']}")
        report.append("")
        
        # Friendly message
        report.append(f"❗ {analysis['friendly_message']}")
        report.append("")
        
        # Show context if available
        if source_code and line_number:
            lines = source_code.split('\n')
            if 0 < line_number <= len(lines):
                report.append("📄 Context:")
                report.append(f"   Line {line_number}: {lines[line_number - 1]}")
                report.append("   " + " " * (len(str(line_number)) + 2) + "^")
                report.append("")
        
        # Tip if available
        if analysis['tip']:
            report.append(analysis['tip'])
            report.append("")
        
        # Original error (technical details)
        report.append("─────────────────────────────────────")
        report.append("Technical details (for debugging):")
        report.append(f"   {analysis['original_error']}")
        
        return '\n'.join(report)
    
    def check_common_mistakes(self, source_code: str) -> List[Dict[str, Any]]:
        """
        Proactively check source code for common mistakes before execution.
        
        Args:
            source_code: The SimPL source code to check.
        
        Returns:
            List of potential issues found.
        """
        issues = []
        lines = source_code.split('\n')
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Check for unclosed strings
            quote_count = stripped.count('"') - stripped.count('\\"')
            if quote_count % 2 != 0:
                issues.append({
                    'line': i,
                    'type': 'unclosed_string',
                    'message': "This line has an unclosed string (odd number of quotes).",
                    'tip': "Make sure every \" has a matching \"",
                })
            
            # Check for if without then (only if not using C/Python flavors)
            if stripped.startswith('if ') and ' then' not in stripped:
                if '{' not in stripped and ':' not in stripped:
                    issues.append({
                        'line': i,
                        'type': 'missing_then',
                        'message': "'if' statements need 'then' keyword.",
                        'tip': "Add 'then' after the condition: if x > 5 then",
                    })

            # Check for mixed flavors in the same block
            # (C-style open + Standard close or vice versa)
            if stripped.endswith('{') and 'end' in stripped:
                issues.append({
                    'line': i,
                    'type': 'mixed_flavors',
                    'message': "Mixed C-style '{' with Standard 'end' on same line.",
                    'tip': "Stick to one flavor: either { } or then/end",
                })
            
            # Check for let without =
            if stripped.startswith('let ') and '=' not in stripped:
                issues.append({
                    'line': i,
                    'type': 'missing_equals',
                    'message': "'let' statements need '=' to assign a value.",
                    'tip': "Use: let x = 10",
                })
            
            # Check for unbalanced parentheses
            if stripped.count('(') != stripped.count(')'):
                issues.append({
                    'line': i,
                    'type': 'unbalanced_parens',
                    'message': "Unbalanced parentheses on this line.",
                    'tip': "Count your ( and ) - they should match!",
                })
        
        return issues
    
    def get_quick_reference(self) -> str:
        """Return a quick reference guide for common errors."""
        reference = """
╔═══════════════════════════════════════════════════════════════╗
║          SimPL Quick Reference - Common Errors & Flavors      ║
╚═══════════════════════════════════════════════════════════════╝

📝 VARIABLE DECLARATION
   ✓ Correct: let x = 10
   ✗ Wrong: x = 10 (missing 'let')

📝 IF STATEMENTS (Standard)
   ✓ Correct: if x > 5 then print x end
   ✗ Wrong: if x > 5 print x (missing 'then' and 'end')

📝 IF STATEMENTS (C/JS Style)
   ✓ Correct: if (x > 5) { print x }
   ✗ Wrong: if (x > 5) { print x end  (mixed flavors!)

📝 IF STATEMENTS (Python Style)
   ✓ Correct: if x > 5:
               print x
   ✗ Wrong: if x > 5: print x }  (mixed flavors!)

📝 STRINGS
   ✓ Correct: print "Hello, World!"
   ✗ Wrong: print "Hello (missing closing quote)

📝 MATH OPERATIONS
   ✓ Correct: let sum = 5 + 3
   ✗ Wrong: let result = "5" + 3 (can't mix text and numbers)

📝 DIVISION
   ✓ Safe: if divisor != 0 then result = a / b end
   ✗ Dangerous: result = a / 0 (division by zero!)

📝 MIXED FLAVORS
   ✗ WRONG: if x > 5 { print x end
   💡 Stick to ONE flavor per block!
      Standard: if x > 5 then ... end
      C-style:  if (x > 5) { ... }
      Python:   if x > 5: (indent)

💡 Remember: When you see an error, read the friendly message
   first - it will tell you exactly what to fix!
"""
        return reference


# Global helper instance
_helper_instance: Optional[SmartHelper] = None


def get_helper() -> SmartHelper:
    """Get the global SmartHelper instance."""
    global _helper_instance
    if _helper_instance is None:
        _helper_instance = SmartHelper()
    return _helper_instance


def handle_error(error: Exception, source_code: str = None, 
                 line_number: int = None) -> str:
    """
    Handle an exception and return a friendly error report.
    
    Args:
        error: The exception that was raised.
        source_code: Optional source code for context.
        line_number: Optional line number where error occurred.
    
    Returns:
        Formatted friendly error report.
    """
    helper = get_helper()
    error_message = str(error)
    
    # Try to extract line number from exception if not provided
    if line_number is None and hasattr(error, 'line'):
        line_number = error.line
    
    return helper.format_error_report(error_message, source_code, line_number)


if __name__ == '__main__':
    # Demo the Smart Helper
    helper = SmartHelper()
    
    print("=== SimPL Smart Helper Demo ===\n")
    
    # Test various error messages
    test_errors = [
        "Line 3, Column 5: Expected THEN, got NUMBER",
        "Undefined variable: score",
        "Division by zero",
        "Unterminated string starting at line 2",
        "can only concatenate str (not \"int\") to str",
    ]
    
    for error_msg in test_errors:
        print(helper.format_error_report(error_msg))
        print("\n" + "="*50 + "\n")
    
    # Show quick reference
    print(helper.get_quick_reference())
