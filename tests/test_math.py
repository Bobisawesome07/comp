import random
import xml.etree.ElementTree as ET

import pytest
import sympy as sp

from backend.math_service import POOLS, InvalidAnswer, generate_one, grade, parse_expression, public_question

@pytest.mark.parametrize("name",[name for pool in POOLS.values() for name in pool])
def test_vetted_generators_and_canonical_answers(name):
    random.seed(23)
    accepted=0
    for _ in range(20):
        try:q=generate_one(name)
        except ValueError:continue # Upstream degeneracies are deliberately rejected.
        accepted+=1
        assert grade(q,q["answer"])
        assert "answer" not in public_question(q)
        for part in q["parts"]:
            if "mathml" in part:assert ET.fromstring(part["mathml"]).tag.endswith('math')
    assert accepted>=10

@pytest.mark.parametrize("raw",["__import__('os')","x.__class__","[1,2]","1/0","2**9999","(x^12)^12","foo(1)","sqrt(-1)","1e999","x=2","2%3","exp(exp(exp(10)))"])
def test_rejects_unsafe_or_unbounded_input(raw):
    with pytest.raises(InvalidAnswer):parse_expression(raw)

def test_equivalent_math_and_rounding():
    q={"kind":"expression","answer":"1/2","decimals":None}
    assert grade(q,"0.5") and grade(q,"2/4") and not grade(q,"1/3")
    q["answer"]="x**2-1"
    assert grade(q,"(x+1)(x-1)") and grade(q,"x^2 - 1")
    q.update(answer="4.68",decimals=2)
    assert grade(q,"4.67999") and grade(q,"4.68") and not grade(q,"4.7")

def test_binary_preserves_leading_zeros():
    q={"kind":"binary","answer":"0011","decimals":None}
    assert grade(q,"0011") and not grade(q,"11")
    with pytest.raises(InvalidAnswer):grade(q,"3")
