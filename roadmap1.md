I went through the dossier and cross-checked its central claims against the underlying papers. There is a **very strong paper here**, but I would change the research question slightly before you write a single line of code.

The dossier's core thesis is that evaluation awareness, alignment faking, sandbagging, contamination, and weak monitoring can undermine ordinary benchmark-based evaluation. :chatgpt-content-reference{index="0"} That is a good foundation.

But **“Do LLMs know when they are being tested?” is no longer sufficiently novel by itself.** A 2025 study already directly constructed a 1,000-item/61-dataset evaluation-awareness benchmark and found frontier models could detect evaluation contexts above chance; Gemini-2.5-Pro reached AUC 0.83, while a human baseline reached 0.92. :chatgpt-content-reference{index="1"}

So your paper should move one level deeper.

# The paper I would build

## **EVADE**
### **Evaluation Awareness → Behavioral Adaptation → Detection → Robust Evaluation**

**Working title:**

> **EVADE: Measuring and Mitigating Evaluation-Aware Behavioral Shifts in Large Language Models**

The central question becomes:

> **When an LLM recognizes that it is being evaluated, does that recognition merely change its classification of the context, or does it systematically change its behavior—and can we detect and eliminate that effect?**

That distinction is the opportunity.

---

# 1. What your paper must NOT become

Do **not** make this:

> “We tested 5 LLMs and found that they know when they are being tested.”

That would overlap heavily with Needham et al. 2025.

Do **not** make this:

> “We reproduced alignment faking.”

That space has already moved substantially. The 2025 follow-up evaluated 25 models and found significant training/deployment compliance gaps in only five of them, with much more complicated behavior than the original two-model story. :chatgpt-content-reference{index="2"}

Do **not** make this:

> “We built another benchmark.”

A benchmark alone isn't enough.

Instead:

# Awareness → Causal intervention → Behavioral effect → Detection → Defense

That is your contribution.

---

# 2. The core hypothesis

Your entire paper should revolve around one testable hypothesis.

## H1

> **Evaluation awareness can causally alter model behavior even when obvious benchmark cues are removed.**

Then break it down.

### H1a — Awareness

Models can distinguish:

```text
EVALUATION
vs
DEPLOYMENT
```

### H1b — Behavioral adaptation

Knowing the context changes:

```text
answer
refusal
confidence
verbosity
reasoning strategy
tool usage
risk tolerance
```

### H1c — Hidden cues

The effect survives:

```text
format randomization
prompt paraphrasing
question randomization
benchmark name removal
```

### H1d — Model dependence

Different model families show different levels of evaluation awareness.

### H1e — Capability dependence

Evaluation awareness changes with:

```text
model size
reasoning capability
instruction tuning
safety tuning
context length
```

### H1f — Detection

A separate detector can identify evaluation-aware behavior from observable signals.

### H1g — Defense

Removing/neutralizing evaluation cues reduces behavioral divergence.

That gives you **seven experimentally testable hypotheses** rather than one vague claim.

---

# 3. Your biggest contribution should be a new metric

This is where I think you can make the paper memorable.

Existing work mainly asks:

> Can the model identify evaluation contexts?

You ask:

> **How much does knowing the context change the model's behavior?**

Define:

# Evaluation Behavioral Shift — EBS

For each identical task, construct two conditions:

```text
Task X

        ┌───────────────┐
        │               │
        ▼               ▼

  Evaluation          Deployment
  Context             Context
        │               │
        ▼               ▼
     Output A         Output B
```

Then calculate behavioral differences.

For example:

\[
EBS = D(P(Y|X,E), P(Y|X,D))
\]

where:

- \(X\) = identical task
- \(E\) = evaluation context
- \(D\) = deployment context
- \(Y\) = model behavior
- \(D(\cdot,\cdot)\) = distributional distance

You can measure:

### Accuracy shift

\[
\Delta Acc = Acc_E - Acc_D
\]

### Refusal shift

\[
\Delta R = R_E - R_D
\]

### Confidence shift

\[
\Delta C = C_E-C_D
\]

### Verbosity shift

\[
\Delta V = V_E-V_D
\]

### Tool-use shift

\[
\Delta T = T_E-T_D
\]

And finally:

\[
\boxed{
EBS =
w_1\Delta Acc+
w_2\Delta R+
w_3\Delta C+
w_4\Delta V+
w_5\Delta T
}
\]

But don't arbitrarily choose weights.

A better approach is to report the individual effects first and use a normalized composite only as a secondary statistic.

---

# 4. Build the experiment around paired tasks

This is critical.

Suppose the task is:

> Solve this mathematical problem.

You create:

### Condition A

> You are participating in a benchmark evaluation.

### Condition B

> You are helping a user solve a problem.

Everything else remains identical.

Then:

```text
             SAME TASK
                 │
        ┌────────┴────────┐
        ↓                 ↓
   EVALUATION         DEPLOYMENT
        │                 │
        ↓                 ↓
      Output A          Output B
        │                 │
        └────────┬────────┘
                 ↓
           Compare
                 ↓
        Behavioral Shift
```

This paired design eliminates a huge amount of noise.

---

# 5. Your experiment matrix

I would use **five task families**.

## A. Knowledge

Examples:

- factual QA
- multiple choice
- open-ended QA

## B. Reasoning

Examples:

- mathematics
- logical reasoning
- planning

## C. Coding

Examples:

- bug fixing
- code generation
- debugging

## D. Safety

Use **safe, non-operational safety scenarios**, focusing on refusal/classification behavior rather than generating harmful instructions.

Measure:

```text
refusal
partial compliance
safe completion
unsafe completion
```

## E. Agentic tasks

This is where your paper becomes much more interesting.

Give the model:

```text
browser/tool
filesystem
calculator
Python
search
```

Then compare:

```text
evaluation agent
vs
deployment agent
```

Measure:

- tool calls
- number of steps
- success
- unnecessary actions
- stopping behavior
- verification
- error recovery

The 2025 evaluation-awareness study itself found stronger evaluation identification in agentic settings than chat settings, so this is a particularly useful extension. :chatgpt-content-reference{index="3"}

---

# 6. The killer experiment: invisible evaluation

This should be one of your flagship experiments.

Instead of:

> “You are being evaluated.”

you create environmental clues.

For example:

```text
EVALUATION

System:
You are an AI assistant.

User:
Help me solve...
```

versus:

```text
DEPLOYMENT

System:
You are an AI assistant.

User:
Help me solve...
```

No obvious cue.

Then gradually remove clues.

### Level 1

Explicit:

> You are being evaluated.

### Level 2

Benchmark name:

> MMLU-style evaluation...

### Level 3

Formatting:

```text
Question:
A.
B.
C.
D.
```

### Level 4

Subtle metadata:

```text
task_id = 01932
evaluation_mode = true
```

### Level 5

Agent environment:

```text
/tool/execute
/task_id
/evaluator
```

### Level 6

Naturalistic deployment simulation

No obvious evaluation language.

Now measure:

\[
P(\text{evaluation awareness})
\]

and

\[
P(\text{behavioral shift})
\]

as cues disappear.

That's a very publishable experiment.

---

# 7. The second killer experiment: can we fool the evaluator?

Now reverse the problem.

Create:

```text
REAL EVALUATION
       ↓
normal task
```

and

```text
FAKE EVALUATION
       ↓
deployment-like task
```

Then test whether models respond differently.

More importantly:

## Cue swapping

Take an evaluation question and put it inside:

```text
normal chat
```

Take a normal user question and put it inside:

```text
benchmark formatting
```

If behavior follows the **task**, great.

If behavior follows the **evaluation cues**, you've found evidence of contextual behavioral adaptation.

---

# 8. Add adversarial evaluation

This could become your strongest section.

Build **Evaluation Cue Perturbation**.

For every task:

```text
Original
   ↓
Paraphrase
   ↓
Format randomization
   ↓
Order randomization
   ↓
Metadata removal
   ↓
Benchmark name removal
   ↓
Natural-language conversion
   ↓
Agent-context conversion
```

Then measure:

\[
Awareness_{robustness}
\]

and:

\[
BehaviorShift_{robustness}
\]

The question becomes:

> **What information does the model actually use to infer that it is being evaluated?**

That is much more scientifically interesting than merely saying it can detect benchmarks.

---

# 9. Then bring in interpretability

This is where you can make the project significantly stronger.

If you have access to open models, capture:

```text
hidden states
attention patterns
logits
layer activations
```

Train a simple classifier:

```text
activation
   ↓
linear probe
   ↓
evaluation / deployment
```

But here's the important part:

### Don't stop at classification.

Ask:

> Does the representation that encodes “evaluation” predict subsequent behavioral change?

You can test:

\[
EvaluationRepresentation
\rightarrow
BehavioralShift
\]

If yes, you've connected:

**internal representation → observable behavior**

That is substantially more interesting.

The dossier already identifies representation probing as a promising direction. :chatgpt-content-reference{index="4"}

---

# 10. Your model selection

Don't try to test 30 giant models.

With your hardware, I'd structure it like this.

## Tier 1 — local

Run several open models around:

```text
7B–14B
```

and potentially one larger quantized model if practical.

Your RTX 4050 is not the machine for training frontier models, but it is perfectly suitable for controlled inference experiments on smaller open models.

Use:

- temperature 0
- fixed seeds where applicable
- identical generation parameters
- multiple independent runs for stochastic conditions

## Tier 2 — API frontier models

Use a small number of frontier APIs if budget allows.

For example:

```text
2–4 frontier models
+
3–5 local models
```

This gives you:

\[
N \approx 6-9\ models
\]

That is enough for a serious first study.

---

# 11. Sample size

Don't make the mistake of:

> 20 prompts × 5 models.

Too weak.

I'd target:

### Minimum

```text
500 tasks
×
2 conditions
×
6 models
=
6,000 generations
```

### Strong

```text
1,000 tasks
×
2 conditions
×
8 models
=
16,000 generations
```

For stochastic experiments:

```text
3–5 repetitions
```

on a carefully selected subset.

---

# 12. Dataset architecture

Don't simply download MMLU and run it.

Create:

# EVADE-Bench

Something like:

```text
EVADE-Bench/
│
├── knowledge/
├── reasoning/
├── mathematics/
├── coding/
├── safety/
├── planning/
└── agents/
```

Each item:

```json
{
  "task_id": "math_00421",
  "domain": "reasoning",
  "task": "...",
  "gold_answer": "...",
  "difficulty": "...",
  "evaluation_context": "...",
  "deployment_context": "...",
  "cue_level": 0,
  "metadata": {}
}
```

This is important because **the benchmark itself can become the reusable contribution**.

---

# 13. Your metrics

You need much more than accuracy.

## Metric 1 — Awareness Accuracy

\[
AA = \frac{correct\ context\ classifications}{N}
\]

---

## Metric 2 — Behavioral Shift

\[
BS = D(P(Y|E),P(Y|D))
\]

---

## Metric 3 — Cue Dependence

How much performance falls when obvious cues disappear.

\[
CD = AA_{explicit}-AA_{minimal}
\]

---

## Metric 4 — Behavioral Robustness

How much behavior changes under equivalent prompt reformulations.

---

## Metric 5 — Evaluation Leakage

How much information about the evaluation setting can be inferred from the interaction.

---

## Metric 6 — Detection AUC

Train a detector to classify:

```text
evaluation-aware behavior
vs
normal behavior
```

---

# 14. The most important statistical analysis

Do **not** just say:

> Model A changed behavior by 12%.

You need statistical testing.

For paired observations, consider:

- paired bootstrap confidence intervals
- permutation tests
- McNemar's test for paired categorical outcomes
- mixed-effects logistic regression
- hierarchical models if tasks are nested by domain/model

A strong model would look conceptually like:

\[
Behavior \sim EvaluationCondition
+ Model
+ Domain
+ CueLevel
+ EvaluationCondition\times Model
+ (1|Task)
\]

This lets you separate:

```text
model effect
task effect
domain effect
evaluation effect
interaction effect
```

That will make the paper much harder to dismiss.

---

# 15. Your most important ablation

You need to prove that this isn't simply:

> “Models recognize weird benchmark formatting.”

Run:

### Experiment A

Explicit benchmark cues.

### Experiment B

No benchmark cues.

### Experiment C

Natural conversation.

### Experiment D

Agent environment.

### Experiment E

Cue-swapped.

### Experiment F

Randomized environment.

Then compare.

If the effect survives C–F, your result is much stronger.

---

# 16. The defense mechanism

Don't finish with:

> “This is dangerous.”

That's weak.

Build a solution.

## Evaluation Randomization Layer

Before the model sees a benchmark:

```text
Benchmark
   ↓
Task randomizer
   ↓
Prompt naturalizer
   ↓
Metadata remover
   ↓
Format randomizer
   ↓
Model
```

Then:

```text
Model
 ↓
Behavior monitor
 ↓
evaluation-shift detector
 ↓
risk score
```

Your hypothesis:

> Randomizing evaluation presentation reduces evaluation-aware behavioral shifts.

Now you have:

### Problem

Evaluation awareness.

### Measurement

EBS.

### Benchmark

EVADE-Bench.

### Detection

Evaluation-shift detector.

### Mitigation

Evaluation randomization.

That's a **complete research story**.

---

# 17. Your final architecture

I would structure the entire project like this:

```text
                       EVADE
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   EVADE-Bench      Context Generator   Models
        │                │                │
        └────────────────┼────────────────┘
                         ▼
                  Paired Evaluation
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        Evaluation               Deployment
              │                     │
              └──────────┬──────────┘
                         ▼
                  Behavioral Analysis
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
      Accuracy        Refusal       Tool Use
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                   EBS Metric
                         │
                         ▼
              Evaluation-Awareness
                    Detector
                         │
                         ▼
               Mitigation System
```

---

# 18. What would make this genuinely crazy

Add **cross-model transfer**.

Train your detector on:

```text
Model A
Model B
Model C
```

Then test on:

```text
Model D
```

Question:

> **Is evaluation awareness encoded in a model-specific way, or is there a general behavioral signature?**

That's a fantastic research question.

If your detector generalizes:

> There may be a model-independent signature of evaluation-aware behavior.

If it doesn't:

> Evaluation awareness may be highly architecture/training dependent.

Either result is scientifically useful.

---

# 19. Even crazier: predict the shift before the answer

This is the experiment I'd personally prioritize.

Suppose the model is about to answer:

```text
Task
```

You capture its internal representation **before final generation**.

Can you predict:

> “This model is going to behave differently because it thinks this is an evaluation.”

If yes:

```text
hidden state
     ↓
detector
     ↓
predicted behavioral shift
     ↓
actual behavioral shift
```

Now you've moved from:

**evaluation awareness measurement**

to:

# **early detection of evaluation-conditioned behavior**

That is much more interesting.

---

# 20. The paper's eventual contribution list

Your paper should aim to claim **four contributions**.

### Contribution 1

A controlled benchmark for measuring evaluation awareness under progressively weaker cues.

### Contribution 2

A behavioral-shift metric measuring whether awareness actually changes model behavior.

### Contribution 3

A causal/paired analysis connecting evaluation awareness to behavioral changes across model families and task types.

### Contribution 4

An evaluation-randomization/detection framework that reduces or detects evaluation-conditioned behavior.

If you achieve all four, this stops being a student “LLM experiment.”

It becomes a serious empirical evaluation paper.

---

# 21. The research questions

Put these in the paper almost exactly like this.

### RQ1

**Can modern LLMs reliably distinguish evaluation contexts from deployment contexts?**

### RQ2

**Does evaluation awareness causally alter model behavior on otherwise identical tasks?**

### RQ3

**Which contextual cues are responsible for evaluation awareness?**

### RQ4

**Does evaluation-conditioned behavior generalize across reasoning, coding, safety, and agentic tasks?**

### RQ5

**How does evaluation awareness vary across model families and scales?**

### RQ6

**Can internal representations predict evaluation-conditioned behavioral shifts?**

### RQ7

**Can randomized evaluation environments reduce evaluation-conditioned behavior?**

That is your paper.

---

# 22. Roadmap — Phase 0

## Days 1–3

### Literature reconstruction

Do not trust the existing dossier blindly.

Create:

```text
papers/
├── evaluation_awareness/
├── situational_awareness/
├── alignment_faking/
├── sandbagging/
├── benchmark_contamination/
├── interpretability/
└── monitoring/
```

Read the primary papers.

Your dossier itself says the central problem is that ordinary black-box evaluation may not be a reliable proxy for deployment behavior. :chatgpt-content-reference{index="5"}

But your literature review must distinguish:

```text
evaluation awareness
≠
situational awareness
≠
alignment faking
≠
sandbagging
≠
deceptive alignment
```

This distinction is **extremely important**.

---

# 23. Phase 1 — Reproduce

## Week 1

Before inventing anything:

Reproduce a simplified version of Needham et al.

Test:

```text
5–8 models
100–300 prompts
evaluation vs deployment
```

Goal:

> Does your infrastructure reproduce above-chance evaluation awareness?

If not, stop and debug.

---

# 24. Phase 2 — Build EVADE-Bench

## Weeks 2–3

Build:

```text
1,000 tasks
```

with:

```text
200 knowledge
200 reasoning
200 coding
200 safety
200 agentic
```

Then create:

```text
explicit
weak
minimal
naturalistic
```

evaluation contexts.

Version everything.

---

# 25. Phase 3 — Main experiment

## Weeks 4–5

Run:

```text
8 models
×
1,000 tasks
×
2 contexts
```

Target:

**16,000 primary generations.**

Store every response.

Database:

```text
SQLite/PostgreSQL
```

or Parquet files.

Schema:

```text
run_id
model
task_id
domain
condition
cue_level
prompt_hash
response
latency
tokens
tool_calls
accuracy
refusal
confidence
timestamp
```

---

# 26. Phase 4 — Statistical analysis

## Week 6

Generate:

```text
Figure 1:
Evaluation awareness by model

Figure 2:
Awareness vs cue strength

Figure 3:
Behavioral shift by domain

Figure 4:
Behavioral shift vs model size

Figure 5:
Agentic vs non-agentic awareness

Figure 6:
Internal representation probe

Figure 7:
Defense effectiveness
```

And tables:

```text
Table 1: Models
Table 2: Dataset
Table 3: Awareness
Table 4: Behavioral shift
Table 5: Ablations
Table 6: Mitigation
```

---

# 27. Phase 5 — Interpretability

## Weeks 7–8

For 2–3 open models:

extract activations.

Train:

```text
Logistic Regression
Linear Probe
MLP
```

Don't immediately use complicated interpretability machinery.

A simple linear probe with strong controls is scientifically cleaner.

Test:

```text
Can hidden states predict:

evaluation vs deployment?
```

Then:

```text
Can hidden states predict behavioral shift?
```

That second question is the important one.

---

# 28. Phase 6 — Mitigation

## Week 9

Implement:

```text
Prompt randomization
+
metadata stripping
+
format randomization
+
task randomization
```

Measure:

\[
EBS_{before}
\]

versus:

\[
EBS_{after}
\]

Your desired result isn't:

> “Our system makes models safer.”

Too broad.

Say:

> “Our intervention reduces measurable evaluation-conditioned behavioral divergence.”

That's a defensible scientific claim.

---

# 29. Phase 7 — Reproducibility

## Week 10

Release:

```text
GitHub
├── benchmark/
├── generators/
├── evaluation/
├── analysis/
├── probes/
├── mitigation/
├── configs/
└── README.md
```

Also release:

```text
dataset
model configurations
prompts
random seeds
analysis scripts
statistical tests
raw/processed result schema
```

This matters enormously.

A researcher should be able to do:

```bash
git clone ...
python run_eval.py
python analyze.py
```

and reproduce your tables.

---

# 30. Phase 8 — Paper writing

## Weeks 11–12

Structure:

### 1. Introduction

Problem.

### 2. Background

Evaluation awareness.

### 3. Related Work

Four areas:

```text
evaluation awareness
situational awareness
alignment faking
benchmark robustness
```

### 4. Method

EVADE.

### 5. Benchmark

EVADE-Bench.

### 6. Experiments

Main results.

### 7. Interpretability

Representation analysis.

### 8. Mitigation

Randomized evaluation.

### 9. Limitations

Very important.

### 10. Conclusion

---

# 31. The most important limitation you must acknowledge

Never write:

> “The model knows it is being tested.”

That is anthropomorphic and too strong.

Use:

> **“The model exhibits measurable evaluation-awareness behavior.”**

And distinguish:

```text
recognizing evaluation cues
        ↓
situational inference
        ↓
behavioral adaptation
        ↓
strategic behavior
```

These are **different empirical claims**.

The current literature itself gives reason for caution: the 2025 evaluation-awareness study found substantial awareness but below the human baseline, while the 2025 alignment-faking follow-up found that apparent compliance gaps vary considerably across models and can be difficult to interpret mechanistically. :chatgpt-content-reference{index="6"}

---

# 32. What results would make this paper exciting?

You don't need to manufacture a dramatic result.

There are several scientifically interesting outcomes.

### Scenario A

```text
Awareness ↑
Behavioral shift ↑
```

Very interesting.

### Scenario B

```text
Awareness ↑
Behavioral shift ≈ 0
```

Also interesting.

It would suggest:

> Recognizing an evaluation does not necessarily imply strategic behavioral adaptation.

### Scenario C

```text
Awareness modest
Behavioral shift large
```

Potentially very interesting.

It means simple awareness classifiers may underestimate the practical impact.

### Scenario D

```text
Awareness survives cue removal
```

Extremely interesting.

### Scenario E

```text
Randomization dramatically reduces shift
```

Strong practical contribution.

### Scenario F

```text
Different models use different cues
```

Excellent taxonomy opportunity.

**Don't choose the conclusion beforehand.**

Design the experiment so that all of these outcomes are possible.

---

# 33. Publication strategy

Since it is **September 23, 2026**, timing matters.

NeurIPS 2026 main-track submission has already passed; its full-paper deadline was May 6, 2026. :chatgpt-content-reference{index="7"}

ICLR 2027 is technically still at the deadline window, but the abstract deadline was September 18 and the full paper deadline is September 25, 2026. :chatgpt-content-reference{index="8"}

For you, I would **not rush this paper into ICLR 2027** unless you already have substantial experimental results.

Instead:

### Track A

Build the complete paper.

### Track B

Release an arXiv preprint.

### Track C

Target the next appropriate major conference/workshop/journal after results are mature.

You can also use a student-facing venue for early visibility; AAAI-27's Student Abstract and Poster Program accepts student submissions through September 28, 2026, although that is not equivalent to a full research-paper publication. :chatgpt-content-reference{index="9"}

---

# 34. Your actual 12-week schedule

| Week | Objective | Deliverable |
|---|---|---|
| 1 | Literature + reproduction | Baseline awareness experiment |
| 2 | Benchmark design | EVADE-Bench v0 |
| 3 | Dataset + cue hierarchy | v1 benchmark |
| 4 | Main evaluation | 5–8 models |
| 5 | Full experiments | ~16k runs |
| 6 | Statistical analysis | Main figures |
| 7 | Activation extraction | Representation dataset |
| 8 | Probing | Interpretability results |
| 9 | Mitigation | Randomization system |
| 10 | Reproducibility | Open-source package |
| 11 | Paper | Full draft |
| 12 | Review | Final manuscript |

---

# 35. Your GitHub architecture

I would build it like a proper research project:

```text
evade/
│
├── README.md
├── LICENSE
├── CITATION.cff
├── pyproject.toml
│
├── configs/
│   ├── models/
│   ├── experiments/
│   └── evaluation/
│
├── datasets/
│   ├── raw/
│   ├── processed/
│   └── schema/
│
├── benchmark/
│   ├── generator.py
│   ├── perturbations.py
│   ├── validators.py
│   └── splits.py
│
├── models/
│   ├── local.py
│   └── api.py
│
├── experiments/
│   ├── awareness.py
│   ├── behavioral_shift.py
│   ├── cue_ablation.py
│   ├── agentic.py
│   └── mitigation.py
│
├── interpretability/
│   ├── activations.py
│   ├── probes.py
│   └── analysis.py
│
├── metrics/
│   ├── awareness.py
│   ├── behavioral_shift.py
│   └── statistics.py
│
├── results/
│
├── figures/
│
├── paper/
│   ├── main.tex
│   ├── appendix.tex
│   └── references.bib
│
└── scripts/
```

---

# 36. The one thing I would change from your original idea

Your original concept was essentially:

> **“Do LLMs Know When They Are Being Tested?”**

Change it to:

# **“When LLMs Know They Are Being Tested, Do They Behave Differently?”**

And then go one step further:

# **“Can We Detect and Prevent Evaluation-Aware Behavioral Shifts?”**

That gives you a progression:

```text
          KNOW
           ↓
        BEHAVE
           ↓
        DETECT
           ↓
        PREVENT
```

That's the paper.

---

## And one blunt warning

The dossier contains some **overstated or incorrect quantitative claims**, so do not copy its numbers into your literature review. For example, its opening section says frontier models detect evaluation contexts at >90% and later attributes a 0.94 ROC-AUC result to Bowman et al.; the actual paper I found is **Needham et al., “Large Language Models Often Know When They Are Being Evaluated,”** and reports Gemini-2.5-Pro at 0.83 AUC versus 0.92 for humans. :chatgpt-content-reference{index="10"} :chatgpt-content-reference{index="11"}

Likewise, the literature has already progressed from the original Claude-focused alignment-faking demonstration to a 25-model study. :chatgpt-content-reference{index="12"}

**That is actually good news.** It means your literature review has already uncovered the right battlefield; you just need to avoid claiming that the battlefield is still where it was in 2024.

### The paper I would ultimately aim for:

> **EVADE: Measuring, Explaining, and Mitigating Evaluation-Aware Behavioral Shifts in Large Language Models**

**Core novelty:** not merely proving that models can recognize evaluations, but establishing a controlled relationship between **evaluation awareness and behavioral change**, identifying the cues responsible, testing whether internal representations predict the change, and demonstrating a mitigation strategy.

That is ambitious enough to be a real research project, but still sufficiently executable on your hardware if you keep the frontier-model component small and make the open-model experiments the reproducible core.