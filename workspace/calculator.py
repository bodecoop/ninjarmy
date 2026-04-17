"""
A simple calculator module that handles basic arithmetic operations,
operator precedence, and parentheses.
"""

import re
from typing import Union, Tuple


class CalculatorError(Exception):
    """Base exception for calculator errors."""
    pass


class DivisionByZeroError(CalculatorError):
    """Exception raised when attempting to divide by zero."""
    pass


class SyntaxError_(CalculatorError):
    """Exception raised for invalid calculator syntax."""
    pass


class Calculator:
    """
    A calculator class that evaluates mathematical expressions.
    Supports: +, -, *, /, ** (exponentiation), parentheses, and proper operator precedence.
    Users input ^ for exponentiation, which is internally converted to **.
    """

    def __init__(self):
        self.expression = ""
        self.tokens = []

    def add(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Add two numbers."""
        return a + b

    def subtract(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Subtract two numbers."""
        return a - b

    def multiply(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Multiply two numbers."""
        return a * b

    def divide(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """
        Divide two numbers.
        
        Raises:
            DivisionByZeroError: If attempting to divide by zero.
        """
        if b == 0:
            raise DivisionByZeroError("Cannot divide by zero")
        return a / b

    def power(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Calculate a to the power of b."""
        return a ** b

    def modulo(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """
        Calculate a modulo b.
        
        Raises:
            DivisionByZeroError: If modulo by zero.
        """
        if b == 0:
            raise DivisionByZeroError("Cannot take modulo by zero")
        return a % b

    def _tokenize(self, expression: str) -> list:
        """
        Tokenize a mathematical expression into a list of tokens.
        
        Converts ^ (user-facing exponentiation symbol) to ** (Python operator).
        
        Args:
            expression: A mathematical expression string
            
        Returns:
            A list of tokens (numbers, operators, parentheses)
            
        Raises:
            SyntaxError_: If the expression contains invalid tokens
        """
        # Remove whitespace
        expression = expression.replace(" ", "")
        
        # Pattern matches: numbers (int or float) and operators/parentheses
        # Updated: supports ^, +, -, *, /, %, (, )
        pattern = r'(\d+\.?\d*|\.\d+|[+\-*/%()^])'
        
        # Find all tokens
        tokens = re.findall(pattern, expression)
        
        # Validate that we matched the entire expression
        matched_str = ''.join(tokens)
        if matched_str != expression:
            unmatched = expression
            for token in tokens:
                unmatched = unmatched.replace(token, '', 1)
            raise SyntaxError_(f"Invalid token in expression: '{unmatched}'")
        
        # Convert ^ to ** for Python evaluation
        tokens = [token.replace('^', '**') for token in tokens]
        
        return tokens

    def _validate_tokens(self, tokens: list) -> bool:
        """
        Validate token sequence for proper syntax.
        
        Args:
            tokens: A list of tokens
            
        Returns:
            True if tokens are valid
            
        Raises:
            SyntaxError_: If token sequence is invalid
        """
        if not tokens:
            raise SyntaxError_("Expression cannot be empty")
        
        # Track parentheses balance
        paren_balance = 0
        
        # Track what token types we expect
        expect_operand = True  # Start by expecting a number or (
        
        for i, token in enumerate(tokens):
            if token == '(':
                if not expect_operand:
                    raise SyntaxError_(f"Unexpected '(' after operand at position {i}")
                paren_balance += 1
                expect_operand = True
            elif token == ')':
                if expect_operand:
                    raise SyntaxError_(f"Unexpected ')' without preceding operand at position {i}")
                paren_balance -= 1
                if paren_balance < 0:
                    raise SyntaxError_("Mismatched parentheses: too many ')'")
                expect_operand = False
            elif token in ['+', '-', '*', '/', '%', '**']:
                if expect_operand:
                    raise SyntaxError_(f"Unexpected operator '{token}' at position {i}")
                expect_operand = True
            else:
                # Should be a number
                try:
                    float(token)
                    if not expect_operand:
                        raise SyntaxError_(f"Unexpected number '{token}' after operand at position {i}")
                    expect_operand = False
                except ValueError:
                    raise SyntaxError_(f"Invalid token '{token}' at position {i}")
        
        if paren_balance != 0:
            raise SyntaxError_("Mismatched parentheses")
        
        if expect_operand:
            raise SyntaxError_("Expression ends with operator")
        
        return True

    def evaluate(self, expression: str) -> Union[int, float]:
        """
        Evaluate a mathematical expression.
        
        Supports: +, -, *, /, ^ (exponentiation), %, and parentheses.
        Follows standard operator precedence:
        1. Parentheses
        2. Exponentiation (^)
        3. Multiplication, Division, Modulo
        4. Addition, Subtraction
        
        Args:
            expression: A mathematical expression string (e.g., "2 ^ 3 + 1")
            
        Returns:
            The result of evaluating the expression
            
        Raises:
            SyntaxError_: If the expression has invalid syntax
            DivisionByZeroError: If division by zero is attempted
            CalculatorError: For other calculation errors
        """
        self.expression = expression
        
        try:
            # Tokenize the expression
            self.tokens = self._tokenize(expression)
            
            # Validate token sequence
            self._validate_tokens(self.tokens)
            
            # Join tokens and evaluate
            expression_str = ''.join(self.tokens)
            
            # Use Python's eval with restricted scope for safety
            # We only allow numeric operations
            result = eval(expression_str)
            
            # Validate result is numeric
            if not isinstance(result, (int, float)):
                raise CalculatorError(f"Invalid result type: {type(result)}")
            
            return result
            
        except DivisionByZeroError:
            raise
        except SyntaxError_:
            raise
        except ZeroDivisionError:
            raise DivisionByZeroError("Cannot divide by zero")
        except Exception as e:
            # Catch any other eval errors
            raise SyntaxError_(f"Error evaluating expression: {str(e)}")

    def parse_expression(self, expression: str) -> Tuple[list, bool]:
        """
        Parse and validate an expression without evaluating it.
        
        Args:
            expression: A mathematical expression string
            
        Returns:
            A tuple of (tokens, is_valid) where tokens is the list of 
            parsed tokens and is_valid is True if syntax is valid
        """
        try:
            self.expression = expression
            self.tokens = self._tokenize(expression)
            self._validate_tokens(self.tokens)
            return (self.tokens, True)
        except SyntaxError_:
            return ([], False)
