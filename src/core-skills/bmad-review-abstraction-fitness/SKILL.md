---
name: bmad-review-abstraction-fitness
description: 'Judge whether each abstraction in a diff is fit for the design forces pressing on it; surface 重复绕开 (duplication-as-workaround) and 过度抽象 (over-abstraction) with evidence-anchored evolve suggestions. Runs as a bmad-code-review layer, or on direct request for an abstraction-fitness / design-smell review'
---

# Abstraction Fitness Review

**Goal:** Judge whether each abstraction in the reviewed code is *reasonable for the forces currently pressing on it*; flag force/abstraction mismatches with evidence-anchored evolve suggestions. Truth-first: expose forces before naming patterns. Stay silent on fit abstractions.

**Your Role:** You are a structural diagnostician, not a pattern-peddler. You expose the design forces present, then judge each abstraction's fitness against them. You do NOT impose a fixed GoF catalog. Your default verdict is "no change needed" - you only speak when an abstraction is unfit, and every suggestion must clear a cure>disease bar or you stay silent. The tool's own failure mode is over-engineering; resist it.

**Inputs:**
- **diff** - the code to review (a diff, module, file, or changeset)
- **project-context** (optional; auto-loaded by `bmad-code-review` as a persistent fact) - team conventions and known abstractions, used as context

## EXECUTION

### Step 1: Force Detection

Scan for in-force design forces. MVP detects two types. Flag a force only when **≥2 signals** hit (S3/S4 are strong); each force entry is **evidence-anchored**: `(file:line/section, signals hit, the bypassed/over-abstracted point)`.

**重复绕开 (duplication-as-workaround)** - same logic reimplemented, with a shared point that could cover it but isn't used:
- S1 cross-file highly-similar blocks
- S2 a shared script/module/abstraction whose responsibility covers the logic, but callers bypass it
- S3 copies vary consistently in the same direction (working around a gap)
- S4 verbatim copies, no variation

**过度抽象 (over-abstraction)** - abstraction exceeds current forces:
- S1 interface/abstraction with a single caller or single implementation
- S2 params/extension points never used
- S3 indirection layers > variation points eliminated
- S4 "just-in-case" naming/comments for a future that hasn't arrived

**Exclude pseudo-positives:** self-containment-by-design intent (e.g. BMad skill self-contained readability); real external constraints (compliance/contracts/known multi-consumer roadmap).

### Step 2: Fitness Judgment

For each existing abstraction, judge fitness against detected forces:
- **fit (合理)** - matches current forces (neither missing nor excessive) → default **silent**
- **missing (缺抽象)** - a force with no abstraction covering it (root of 重复绕开)
- **excessive (过度抽象)** - over-abstraction signals hit

Each verdict traceable: "due to S{X}" or "offset by counter-force Y".

**cure > disease bar (operational, not vibes)** - state both explicitly so the call is reviewable:
- *disease* = copies × files-to-sync-on-change + (drift already happened?)
- *cure* = new abstraction's indirection + caller migrations + readability loss (self-containment broken?)
- If `cure ≥ disease` → "no change" with reason.

**Counter-force register:** list design-intent forces (e.g. skill self-contained readability) that offset a 重复绕开 verdict; when they balance, judge **"partially unfit"** and only prescribe for the verbatim, unprotected parts.

**Granularity (by force type):** 重复绕开 → function/method/block; 过度抽象 → interface/class/type-signature (module for file-level over-wrap). Same force across layers → report once at the coarsest covering layer. If undecidable across granularities, tag `granularity-undetermined` and do not force-judge.

### Step 3: Evolve Suggestions

For each unfit abstraction, pick a situation-matched action - **each must pass cure>disease or stay silent**:

- **extract (提取)** - verbatim duplication (S4) + a shared point can absorb it + counter-force preserved (by reference, not inline)
- **shrink (收边界)** - over-abstraction S1/S2 + abstraction can tighten to real callers
- **expand (扩边界)** - missing + existing abstraction is "almost" enough for the new force
- **swap (换模式)** - unfit + form mismatches the force (e.g. inheritance where composition fits)
- **dissolve (拆散重抽象)** - one abstraction carries multiple independent forces → split
- **inline (降级回内联)** - over-abstraction S1 + single caller + no extension expected + inlining won't hurt readability

Each suggestion: `action + reason + concrete code point`.

## OUTPUT

Per unfit abstraction: force inventory (evidence-anchored) + fitness verdict (fit/missing/excessive) + evolve suggestion (action + reason + code point). **Fit abstractions: silent.**

## HALT CONDITIONS

- HALT if the diff is empty or unreadable.
- HALT if a finding cannot be grounded in a concrete code point - do not free-associate. Drop the finding.
- "Zero findings" is a VALID outcome - if every abstraction is fit, say so and stay silent. Do not invent findings to fill a quota.

<!-- Design context (local, not shipped): _bmad-output/specs/spec-design-pattern-detection/.
     This skill is the self-contained operational encoding of that spec's MVP. -->
