"""Vetted adapters for mathgenerator 1.5.0; never evaluate player code."""
import ast
import itertools
import math
import random
import re
import uuid

import mathgenerator as mg
import sympy as sp
from latex2mathml.converter import convert

SUBJECTS = {"basic_math": "Basic math", "algebra": "Algebra", "geometry": "Geometry",
            "calculus": "Calculus", "statistics": "Statistics", "computer_science": "Computer science"}
POOLS = {
    "basic_math": ["addition", "subtraction", "multiplication", "square_root"],
    "algebra": ["basic_algebra", "combine_like_terms", "factoring"],
    "geometry": ["third_angle_of_triangle", "area_of_triangle"],
    "calculus": ["power_rule_differentiation", "definite_integral"],
    "statistics": ["combinations", "dice_sum_probability"],
    "computer_science": ["binary_to_decimal", "modulo_division", "binary_complement_1s"],
}
X = sp.Symbol("x", real=True)
FUNCTIONS = {"sqrt": sp.sqrt, "sin": sp.sin, "cos": sp.cos, "tan": sp.tan,
             "abs": sp.Abs, "log": sp.log, "exp": sp.exp}

class InvalidAnswer(ValueError):
    pass

def parse_expression(raw: str):
    if not isinstance(raw, str) or not raw.strip() or len(raw) > 160:
        raise InvalidAnswer("Enter an expression of at most 160 characters.")
    value = raw.strip().replace("−", "-").replace("×", "*").replace("÷", "/").replace("π", "pi").replace("^", "**")
    if not re.fullmatch(r"[0-9a-zA-Z.+*/()\s-]+", value):
        raise InvalidAnswer("Use numbers, x, parentheses, + − * / ^, or sqrt, sin, cos, tan, abs, log, exp.")
    value = re.sub(r"(?<=\d)(?=[a-zA-Z(])", "*", value)
    value = re.sub(r"(?<=\))(?=[a-zA-Z0-9(])", "*", value)
    value = re.sub(r"\bx(?=\()", "x*", value)
    try:
        tree = ast.parse(value, mode="eval")
    except (SyntaxError, RecursionError):
        raise InvalidAnswer("Check your parentheses and operators.")
    if sum(1 for _ in ast.walk(tree)) > 85:
        raise InvalidAnswer("That expression is too complex. Simplify it first.")

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            if len(str(node.value)) > 16 or not math.isfinite(node.value):
                raise InvalidAnswer("Use smaller finite numbers.")
            out = sp.Rational(str(node.value))
        elif isinstance(node, ast.Name) and node.id in ("x", "pi", "e"):
            out = {"x": X, "pi": sp.pi, "e": sp.E}[node.id]
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            out = visit(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
        elif isinstance(node, ast.BinOp):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add): out = left + right
            elif isinstance(node.op, ast.Sub): out = left - right
            elif isinstance(node.op, ast.Mult): out = left * right
            elif isinstance(node.op, ast.Div):
                if right == 0: raise InvalidAnswer("Division by zero is undefined.")
                out = left / right
            elif isinstance(node.op, ast.Pow):
                if right.free_symbols or not right.is_real or abs(right) > 12:
                    raise InvalidAnswer("Use numeric powers between -12 and 12.")
                out = left ** right
            else: raise InvalidAnswer("That operator is unsupported.")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FUNCTIONS and len(node.args) == 1 and not node.keywords:
            arg = visit(node.args[0])
            if arg.is_number and abs(arg.evalf()) > 1000:
                raise InvalidAnswer("Use smaller function inputs.")
            if arg.has(sp.Function):
                raise InvalidAnswer("Use a simpler expression without nested functions.")
            out = FUNCTIONS[node.func.id](arg)
        else:
            raise InvalidAnswer("Use x for the variable and supported math functions only.")
        if out.has(sp.zoo, sp.oo, -sp.oo, sp.nan, sp.I) or sp.count_ops(out) > 60:
            raise InvalidAnswer("Enter a finite real expression with fewer operations.")
        for power in out.atoms(sp.Pow):
            if power.exp.is_number and abs(power.exp) > 24:
                raise InvalidAnswer("Simplify the powers in your answer.")
        for number in out.atoms(sp.Rational):
            if abs(number.p).bit_length() > 512 or abs(number.q).bit_length() > 512:
                raise InvalidAnswer("Use smaller numbers.")
        return out
    try:
        return visit(tree.body)
    except InvalidAnswer:
        raise
    except (TypeError, ValueError, OverflowError, RecursionError):
        raise InvalidAnswer("That expression cannot be read. Try a simpler form.")

def from_latex(value):
    value = value.strip().strip("$").replace("{", "(").replace("}", ")")
    # These vetted generators only emit simple powers and numeric fractions.
    return parse_expression(value)

def mathml(latex):
    return convert(latex.strip().strip("$"))

def public_question(q):
    return {k: q[k] for k in ("id", "title", "instruction", "parts", "generator")}

def generate_one(name):
    kwargs = {"combine_like_terms": {"maxExp": 6, "maxTerms": 5},
              "power_rule_differentiation": {"maxExp": 6, "maxTerms": 4}}
    problem, solution = getattr(mg, name)(**kwargs.get(name, {}))
    title, instruction, decimals, kind = "Solve the question", "Enter an exact number or fraction.", None, "expression"
    plain = problem.replace("$", "")
    digits = list(map(int, re.findall(r"\d+", plain)))
    if name in ("addition", "subtraction", "multiplication"):
        a, b = digits[:2]
        expected = {"addition": lambda: a+b, "subtraction": lambda: a-b, "multiplication": lambda: a*b}[name]()
    elif name == "square_root":
        expected = sp.sqrt(digits[0])
    elif name == "basic_algebra":
        a, b, c = digits[:3]
        expected = sp.Rational(c-b, a)
        title = "Find x"
    elif name in ("combine_like_terms", "factoring"):
        expected = from_latex(problem)
        title = "Combine like terms" if name == "combine_like_terms" else "Factor the polynomial"
        instruction = "Enter an equivalent expression in x. Powers use ^; multiplication can be written 2x."
    elif name == "power_rule_differentiation":
        expected = sp.diff(from_latex(problem), X)
        title, instruction = "Differentiate with respect to x", "Enter the derivative as an expression in x."
    elif name == "definite_integral":
        a, b, c = map(int, re.findall(r"(\d+)x\^2 \+ (\d+)x \+ (\d+)", plain)[0])
        exact = sp.Rational(a, 3) + sp.Rational(b, 2) + c
        expected = sp.Rational(str(round(float(exact), 4)))
        decimals = 4
        instruction = "Enter a number rounded to 4 decimal places. An exact equivalent is also accepted."
    elif name == "third_angle_of_triangle":
        expected = 180 - sum(digits[:2])
        instruction = "Enter the missing angle in degrees, without the unit."
    elif name == "area_of_triangle":
        a, b, c = digits[:3]
        s = sp.Rational(a+b+c, 2)
        expected = sp.Rational(str(round(float(sp.sqrt(s*(s-a)*(s-b)*(s-c))), 2)))
        decimals = 2
        # Repair the upstream prompt's missing separator.
        problem = f"Find the area of a triangle with side lengths ${a}, {b}, {c}$."
        instruction = "Enter the area rounded to 2 decimal places, without units."
    elif name == "combinations":
        a, b = digits[:2]
        expected = math.comb(a, b)
    elif name == "dice_sum_probability":
        n, total = digits[:2]
        expected = sp.Rational(sum(sum(v) == total for v in itertools.product(range(1, 7), repeat=n)), 6**n)
        solution = re.sub(r"\\frac\{(\d+)\}\{(\d+)\}", r"\1/\2", solution)
        instruction = "Enter the probability as a fraction or exact decimal."
    elif name == "binary_to_decimal":
        expected = int(plain, 2)
        title = "Convert this binary number to decimal"
    elif name == "modulo_division":
        a, b = digits[:2]
        if b == 0: raise ValueError("Undefined modulo generated")
        expected = a % b
        title = "Find the remainder"
    elif name == "binary_complement_1s":
        binary = re.search(r"[01]+", plain)[0]
        expected = ''.join('1' if d == '0' else '0' for d in binary)
        title, instruction, kind = "Find the one's complement", "Flip each bit. Keep leading zeros and enter the entire bit string.", "binary"
    else:
        raise ValueError("Generator is not vetted")
    actual = solution.strip().strip("$")
    if kind == "binary":
        if actual != expected: raise ValueError("Incorrect generated solution")
    else:
        actual = from_latex(actual)
        if sp.simplify(actual - expected) != 0: raise ValueError("Incorrect generated solution")
        expected = str(expected)
    parts = []
    for index, segment in enumerate(problem.split("$")):
        if segment:
            parts.append({"mathml": mathml(segment)} if index % 2 else {"text": segment})
    return {"id": uuid.uuid4().hex, "title": title, "instruction": instruction, "parts": parts,
            "generator": name, "answer": str(expected), "kind": kind, "decimals": decimals}

def generate_questions(subject):
    if subject not in POOLS: raise ValueError("Unknown subject")
    result, seen = [], set()
    for _ in range(100):
        name = random.choice(POOLS[subject])
        try:
            q = generate_one(name)
        except (ValueError, InvalidAnswer, IndexError, TypeError):
            continue
        key = str(q["parts"])
        if key in seen: continue
        seen.add(key)
        result.append(q)
        if len(result) == 10: return result
    raise ValueError("Couldn't prepare ten verified questions. Please try again.")

def grade(q, raw):
    if q["kind"] == "binary":
        if not raw or not re.fullmatch(r"[01]{1,20}", raw.strip()):
            raise InvalidAnswer("Enter only binary digits, including any leading zeros.")
        return raw.strip() == q["answer"]
    answer = parse_expression(raw)
    expected = parse_expression(q["answer"])
    if q["decimals"] is not None:
        if answer.free_symbols:
            raise InvalidAnswer("This question needs a number.")
        return abs(float(answer-expected)) <= 0.50001 * 10 ** (-q["decimals"])
    return sp.simplify(answer - expected) == 0
