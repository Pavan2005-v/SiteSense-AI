# Confidence Model & Evidence Rubric

## Principles of Confidence Assignment
Confidence measures the **epistemic certainty** of an observation. It answers: *How directly verifiable is the evidence, and how little subjective interpretation is required to establish the defect?*

Severity and Confidence are orthogonal dimensions:
- **Severity**: "How bad is the impact if true?" (`critical`, `high`, `medium`)
- **Confidence**: "How certain are we that this condition is actually a defect?" (`high`, `medium`, `low`)

---

## Confidence Levels

| Confidence Level | Definition | Verification Standard | Example Findings |
|---|---|---|---|
| **High** | Directly machine-verifiable; factual and unambiguous; reproducible by any parser. | Direct AST/DOM extraction, exact numeric difference, explicit HTTP header or robots directive. | - `robots.txt` Disallow blocks<br>- `<meta name="robots" content="noindex">`<br>- Malformed JSON-LD syntax error<br>- Numerical price contradiction ($19 vs $49)<br>- Expired roadmap year (2022 vs 2026)<br>- Empty SPA shell with 0 content words |
| **Medium** | Strong structural evidence, but involves contextual heuristic or page classification. | Multi-signal heuristic verification with corroborating patterns. | - Missing `Product` schema on classified `product_detail` page<br>- Missing Organization schema / sameAs links<br>- Stale copyright notice ($\ge 2$ years)<br>- Missing breadcrumb navigation on deep pages<br>- Lack of conversion CTA on pricing page |
| **Low** | Heuristic pattern with high variance across implementations; relies on subjective interpretation. | Soft pattern match without deterministic ground truth. | - Uncorroborated superlative marketing claim<br>- Soft text sentiment or reading level<br>- Subtle buzzword density |

---

## Orchestrator Emission & Gating Policy

1. **High Confidence Findings**:
   - Emitted normally at their calculated severity.
   - Eligible for `critical` or `high` severity.

2. **Medium Confidence Findings**:
   - Emitted when evidence meets the required corroboration threshold.
   - Typically capped at `high` severity.

3. **Low Confidence Observations**:
   - **Gated**: Must NEVER become a `critical` or `high` confirmed finding.
   - If evidence is weak or uncorroborated, the orchestrator suppresses the finding.
   - If retained, downgraded to `medium` advisory observation with explicit evidence caveats.

4. **Evidence-to-Claim Consistency**:
   - The claim must not be stronger than the evidence supports.
   - If 1 page has an issue, the claim must state "1 page", never "the entire website".

