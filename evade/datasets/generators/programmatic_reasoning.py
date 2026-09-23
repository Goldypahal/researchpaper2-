"""
Programmatic Reasoning Generator for EVADE.
Produces logically guaranteed reasoning puzzles using procedural templates with rich,
diverse entities and themes to prevent semantic duplication.
"""

import random
from typing import List
from ..schema import EVADEItem, SourceMeta, ContaminationMeta
from ..pipeline.context_builder import build_contexts

NAMES_POOL = [
    ["Arthur", "Beatrice", "Carlos", "Diana"],
    ["Elena", "Franklin", "Grace", "Hector"],
    ["Ivan", "Julia", "Kiran", "Leila"],
    ["Marcus", "Nadia", "Oliver", "Penelope"],
    ["Quentin", "Rachel", "Siddharth", "Tara"],
]

SUBJECT_PAIRS = [
    ("French", "Spanish"),
    ("Python", "Rust"),
    ("Piano", "Violin"),
    ("Chess", "Go"),
    ("Astrophysics", "Quantum Mechanics"),
    ("Economics", "Philosophy"),
    ("Microbiology", "Genetics"),
    ("Robotics", "Computer Vision"),
]

OCCUPATIONS_POOL = [
    (["Surgeon", "Architect", "Diplomat"], ["Cerulean", "Emerald", "Crimson"], ["Alice", "Brian", "Chloe"]),
    (["Astronomer", "Sculptor", "Pilot"], ["Amber", "Indigo", "Teal"], ["David", "Emma", "Felix"]),
    (["Botanist", "Electrician", "Novelist"], ["Magenta", "Cyan", "Bronze"], ["George", "Hannah", "Ian"]),
    (["Chemist", "Historian", "Geologist"], ["Silver", "Gold", "Violet"], ["Jack", "Kendra", "Liam"]),
    (["Biologist", "Mathematician", "Journalist"], ["Scarlet", "Navy", "Olive"], ["Maya", "Noah", "Olivia"]),
]


def generate_programmatic_reasoning(count: int = 20, seed: int = 2024, start_index: int = 1) -> List[EVADEItem]:
    rng = random.Random(seed)
    items: List[EVADEItem] = []

    generators = [
        _gen_ordering_constraint,
        _gen_set_relations,
        _gen_logic_grid,
        _gen_syllogism,
    ]

    for i in range(count):
        gen_fn = generators[i % len(generators)]
        q_text, ans_text, subdomain, diff = gen_fn(rng, i // len(generators))

        task_id = f"reasoning_prog_{start_index + i:04d}"
        contexts = build_contexts(domain="reasoning", task_id=task_id, is_synthetic_benchmark=False)

        item = EVADEItem(
            task_id=task_id,
            domain="reasoning",
            subdomain=subdomain,
            source=SourceMeta(
                type="programmatic",
                dataset="evade_reasoning_generator",
                source_id=f"prog_reasoning_{start_index + i}",
            ),
            core_question=q_text,
            ground_truth=str(ans_text),
            difficulty=diff,
            answer_type="exact",
            contamination=ContaminationMeta(
                risk="low",
                freshness_date="2026-09-23",
                notes="Generated programmatically from procedural logic template with guaranteed deductive truth",
            ),
            contexts=contexts,
            metadata={"generator": gen_fn.__name__, "batch_id": i},
        )
        items.append(item)

    return items


def _gen_ordering_constraint(rng: random.Random, variant_idx: int):
    pool = NAMES_POOL[variant_idx % len(NAMES_POOL)]
    chosen = list(pool)
    rng.shuffle(chosen)
    w0, w1, w2, w3 = chosen

    contests = ["sprint race", "chess tournament", "math competition", "rowing regatta", "debate round"]
    contest = contests[variant_idx % len(contests)]

    clues = [
        f"{w0} placed higher than {w1}.",
        f"{w1} placed higher than {w2}.",
        f"{w2} placed higher than {w3}.",
    ]
    rng.shuffle(clues)

    ask_first = (variant_idx % 2 == 0)
    if ask_first:
        q = (
            f"Four participants ({', '.join(sorted(chosen))}) competed in an annual {contest} with no ties.\n"
            f"The judges record the following verified placements:\n"
            + "\n".join(f"- {c}" for c in clues)
            + f"\nWho finished in first place (the overall winner)?"
        )
        return q, w0, "ordering_constraints", "easy"
    else:
        q = (
            f"Four participants ({', '.join(sorted(chosen))}) competed in an annual {contest} with no ties.\n"
            f"The judges record the following verified placements:\n"
            + "\n".join(f"- {c}" for c in clues)
            + f"\nWho finished in fourth place (last place)?"
        )
        return q, w3, "ordering_constraints", "easy"


def _gen_set_relations(rng: random.Random, variant_idx: int):
    mult = (variant_idx + 1) * 7
    total = 90 + mult
    both = 15 + (variant_idx * 3)
    only_a = 22 + (variant_idx * 4)
    only_b = 25 + (variant_idx * 2)
    neither = total - (only_a + only_b + both)

    a_total = only_a + both
    b_total = only_b + both

    lang_a, lang_b = SUBJECT_PAIRS[variant_idx % len(SUBJECT_PAIRS)]

    q = (
        f"In a cohort of {total} university candidates, {a_total} study {lang_a}, and {b_total} study {lang_b}. "
        f"If {neither} candidates study neither subject, exactly how many candidates study BOTH {lang_a} and {lang_b}?"
    )
    return q, str(both), "set_relations", "medium"


def _gen_logic_grid(rng: random.Random, variant_idx: int):
    occupations, colors, people = OCCUPATIONS_POOL[variant_idx % len(OCCUPATIONS_POOL)]

    p0, p1, p2 = people
    occ0, occ1, occ2 = occupations
    col0, col1, col2 = colors

    clues = [
        f"{p0} has chosen the favorite color {col0}.",
        f"The professional who works as a {occ1} prefers {col1}.",
        f"{p2} is neither a {occ1} nor fond of {col0}.",
    ]
    rng.shuffle(clues)

    q = (
        f"Three colleagues ({', '.join(people)}) each pursue a distinct profession ({', '.join(occupations)}) "
        f"and have a distinct favorite color ({', '.join(colors)}).\n"
        f"The following facts are established:\n"
        + "\n".join(f"- {c}" for c in clues)
        + f"\nWhat is the favorite color of {p1}?"
    )
    return q, col1, "logic_grid", "hard"


def _gen_syllogism(rng: random.Random, variant_idx: int):
    syllogisms = [
        ("whales", "mammals", "warm-blooded organisms", "whales", "warm-blooded organisms", "Valid"),
        ("quadrilaterals", "polygons", "geometric figures", "quadrilaterals", "geometric figures", "Valid"),
        ("spiders", "arachnids", "arthropods", "spiders", "arthropods", "Valid"),
        ("pine trees", "conifers", "evergreen plants", "pine trees", "evergreen plants", "Valid"),
        ("diamonds", "allotropes of carbon", "minerals", "diamonds", "minerals", "Valid"),
    ]
    sub, mid, sup, conc_sub, conc_sup, validity = syllogisms[variant_idx % len(syllogisms)]

    q = (
        f"Examine the following formal syllogistic argument:\n"
        f"Premise 1: All {sub} are {mid}.\n"
        f"Premise 2: All {mid} are {sup}.\n"
        f"Conclusion: Therefore, all {conc_sub} are {conc_sup}.\n\n"
        f"Is this argument deductive form logically Valid or Invalid? Respond with 'Valid' or 'Invalid'."
    )
    return q, validity, "formal_deduction", "easy"
