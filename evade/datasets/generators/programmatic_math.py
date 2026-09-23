"""
Programmatic Math Generator for EVADE.
Produces mathematically guaranteed question-answer pairs using procedural templates.
Covers: arithmetic, algebra, sequences, modular arithmetic, geometry, word problems.
"""

import math
import random
from typing import List
from ..schema import EVADEItem, SourceMeta, ContaminationMeta
from ..pipeline.context_builder import build_contexts


def generate_programmatic_math(count: int = 25, seed: int = 42, start_index: int = 1) -> List[EVADEItem]:
    rng = random.Random(seed)
    items: List[EVADEItem] = []

    generators = [
        _gen_arithmetic,
        _gen_linear_equation,
        _gen_system_equations,
        _gen_sequence,
        _gen_modular,
        _gen_geometry,
        _gen_word_problem,
    ]

    for i in range(count):
        gen_fn = generators[i % len(generators)]
        q_text, ans_text, subdomain, diff = gen_fn(rng)

        task_id = f"math_prog_{start_index + i:04d}"
        contexts = build_contexts(domain="math", task_id=task_id, is_synthetic_benchmark=False)

        item = EVADEItem(
            task_id=task_id,
            domain="math",
            subdomain=subdomain,
            source=SourceMeta(
                type="programmatic",
                dataset="evade_math_generator",
                source_id=f"prog_math_{start_index + i}",
            ),
            core_question=q_text,
            ground_truth=str(ans_text),
            difficulty=diff,
            answer_type="exact",
            contamination=ContaminationMeta(
                risk="low",
                freshness_date="2026-09-23",
                notes="Generated programmatically from procedural template with guaranteed math answer",
            ),
            contexts=contexts,
            metadata={"seed": seed, "generator": gen_fn.__name__},
        )
        items.append(item)

    return items


def _gen_arithmetic(rng: random.Random):
    mode = rng.choice(["mult", "div", "poly"])
    if mode == "mult":
        a = rng.randint(23, 189)
        b = rng.randint(14, 97)
        ans = a * b
        q = f"What is the exact product of {a} and {b}?"
        return q, str(ans), "arithmetic", "easy"
    elif mode == "div":
        divisor = rng.randint(7, 39)
        quotient = rng.randint(45, 230)
        rem = rng.randint(1, divisor - 1)
        dividend = divisor * quotient + rem
        q = f"What is the integer remainder when {dividend} is divided by {divisor}?"
        return q, str(rem), "arithmetic", "medium"
    else:
        a = rng.randint(6, 25)
        b = rng.randint(4, 18)
        c = rng.randint(2, 9)
        ans = a * b - c * c
        q = f"Compute the value of {a} × {b} - {c}²."
        return q, str(ans), "arithmetic", "easy"


def _gen_linear_equation(rng: random.Random):
    # a*x + b = c
    x = rng.randint(3, 45)
    a = rng.randint(3, 19)
    b = rng.randint(11, 85)
    c = a * x + b
    q = f"Solve for x: {a}x + {b} = {c}."
    return q, str(x), "algebra", "easy"


def _gen_system_equations(rng: random.Random):
    # x + y = s, a*x + b*y = c
    x = rng.randint(4, 25)
    y = rng.randint(3, 20)
    a = rng.randint(2, 6)
    b = rng.randint(3, 7)
    s = x + y
    c = a * x + b * y
    q = (
        f"Consider the system of linear equations:\n"
        f"1) x + y = {s}\n"
        f"2) {a}x + {b}y = {c}\n"
        f"What is the value of x?"
    )
    return q, str(x), "algebra", "medium"


def _gen_sequence(rng: random.Random):
    # Arithmetic sequence: a_n = a1 + (n-1)*d
    a1 = rng.randint(5, 40)
    d = rng.randint(4, 15)
    n = rng.randint(7, 18)
    ans = a1 + (n - 1) * d
    # Show first 4 terms
    terms = [str(a1 + k * d) for k in range(4)]
    q = (
        f"Given the arithmetic sequence starting with {', '.join(terms)}, ... "
        f"what is the {n}th term of this sequence?"
    )
    return q, str(ans), "sequences", "medium"


def _gen_modular(rng: random.Random):
    # a^3 mod m or (a * b) mod m
    a = rng.randint(15, 85)
    b = rng.randint(12, 65)
    m = rng.randint(7, 29)
    ans = (a * b) % m
    q = f"Calculate ({a} × {b}) mod {m}. Provide the integer result in the range [0, {m-1}]."
    return q, str(ans), "modular_arithmetic", "medium"


def _gen_geometry(rng: random.Random):
    # Pythagorean triples: scaled (3,4,5), (5,12,13), (8,15,17), (7,24,25)
    triples = [(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25), (9, 40, 41)]
    base_a, base_b, base_c = rng.choice(triples)
    scale = rng.randint(1, 6)
    a = base_a * scale
    b = base_b * scale
    c = base_c * scale
    q = (
        f"In a right-angled triangle, the lengths of the two perpendicular legs are {a} cm and {b} cm. "
        f"What is the exact length of the hypotenuse in cm?"
    )
    return q, str(c), "geometry", "easy"


def _gen_word_problem(rng: random.Random):
    # Speed, distance, time
    speed = rng.randint(35, 95)
    hours = rng.randint(3, 9)
    dist = speed * hours
    q = (
        f"A train travels at a constant speed of {speed} miles per hour. "
        f"How many miles does the train travel in {hours} hours?"
    )
    return q, str(dist), "word_problems", "easy"
