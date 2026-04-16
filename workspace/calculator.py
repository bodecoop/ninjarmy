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
            DivisionByZeroError: If attempting modulo by zero.
        """
        if b == 0:
            raise DivisionByZeroError("Cannot perform modulo by zero")
        return a % b

    def _tokenize(self, expression: str) -> list:
        """
        Tokenize the expression into numbers and operators.
        
        Args:
            expression: Mathematical expression string.
            
        Returns:
            List of tokens (numbers as floats, operators as strings).
            
        Raises:
            SyntaxError_: If the expression contains invalid characters.
        """
        expression = expression.strip().replace(" ", "")
        
        if not expression:
            raise SyntaxError_("Empty expression")
        
        # Pattern to match numbers (including decimals and negative) and operators
        pattern = r'(\d+\.?\d*|\.\d+|[+\-*/%()^])'
        tokens = re.findall(pattern, expression)
        
        # Validate that we matched the entire expression
        matched = "".join(tokens)
        if matched != expression:
            raise SyntaxError_(f"Invalid characters in expression: {expression}")
        
        return tokens

    def _parse_expression(self, tokens: list) -> Union[int, float]:
        """
        Parse and evaluate tokens using recursive descent parsing with proper precedence.
        
        Precedence (highest to lowest):
        1. Parentheses
        2. Exponentiation (**)
        3. Multiplication, Division, Modulo (*, /, %)
        4. Addition, Subtraction (+, -)
        """
        self.tokens = tokens
        self.pos = 0
        return self._parse_addition()

    def _current_token(self) -> str:
        """Get the current token without advancing."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def _advance(self) -> str:
        """Get current token and advance to next."""
        token = self._current_token()
        self.pos += 1
        return token

    def _parse_addition(self) -> Union[int, float]:
        """Parse addition and subtraction (lowest precedence)."""
        result = self._parse_multiplication()
        
        while self._current_token() in ['+', '-']:
            op = self._advance()
            right = self._parse_multiplication()
            if op == '+':
                result = self.add(result, right)
            else:
                result = self.subtract(result, right)
        
        return result

    def _parse_multiplication(self) -> Union[int, float]:
        """Parse multiplication, division, and modulo."""
        result = self._parse_exponentiation()
        
        while self._current_token() in ['*', '/', '%']:
            op = self._advance()
            right = self._parse_exponentiation()
            if op == '*':
                result = self.multiply(result, right)
            elif op == '/':
                result = self.divide(result, right)
            else:  # op == '%'
                result = self.modulo(result, right)
        
        return result

    def _parse_exponentiation(self) -> Union[int, float]:
        """Parse exponentiation (right associative)."""
        result = self._parse_unary()
        
        if self._current_token() == '^':
            self._advance()
            right = self._parse_exponentiation()  # Right associative
            result = self.power(result, right)
        
        return result

    def _parse_unary(self) -> Union[int, float]:
        """Parse unary minus and primary expressions."""
        token = self._current_token()
        
        if token == '-':
            self._advance()
            value = self._parse_unary()
            return -value
        elif token == '+':
            self._advance()
            return self._parse_unary()
        
        return self._parse_primary()

    def _parse_primary(self) -> Union[int, float]:
        """Parse primary expressions: numbers and parenthesized expressions."""
        token = self._current_token()
        
        if token is None:
            raise SyntaxError_("Unexpected end of expression")
        
        if token == '(':
            self._advance()  # consume '('
            result = self._parse_addition()
            if self._current_token() != ')':
                raise SyntaxError_("Missing closing parenthesis")
            self._advance()  # consume ')'
            return result
        
        if token == ')':
            raise SyntaxError_("Unexpected closing parenthesis")
        
        # Try to parse as number
        try:
            return float(token)
        except ValueError:
            raise SyntaxError_(f"Invalid token: {token}")

    def evaluate(self, expression: str) -> Union[int, float]:
        """
        Evaluate a mathematical expression.
        
        Args:
            expression: Mathematical expression as string.
            
        Returns:
            The result of the calculation.
            
        Raises:
            CalculatorError: For various calculation errors.
        """
        self.expression = expression
        tokens = self._tokenize(expression)
        result = self._parse_expression(tokens)
        
        # Check if we've consumed all tokens
        if self.pos < len(self.tokens):
            raise SyntaxError_("Unexpected token after expression")
        
        # Convert to int if it's a whole number
        if isinstance(result, float) and result.is_integer():
            return int(result)
        
        return result
