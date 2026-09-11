# Suggested Action Prioritization Matrix

## Methodology
Suggested actions are prioritized using a deterministic scoring formula based on:
1. **Impact Score (1 - 5)**: Severity of the defect (Critical = 5, High = 4, Medium = 2).
2. **Reach / Scope (1 - 3)**: Site-wide (3), Multiple core landing pages (2), Single isolated page (1).
3. **Implementation Effort (1 - 3)**: Low effort / config change (1), Moderate code template change (2), Architectural refactor (3).

$$\text{Priority Score} = \frac{\text{Impact} \times \text{Reach}}{\text{Effort}}$$

## Priority Bands
- **Critical (Score >= 6.0)**: Must be resolved immediately; blocks discoverability or causes total customer bounce.
- **High (Score 3.5 - 5.9)**: High-leverage fixes that dramatically improve AI extraction accuracy and visitor conversion.
- **Medium (Score 2.0 - 3.4)**: Hygiene, disambiguation, and orientation enhancements.
- **Low (Score < 2.0)**: Minor stylistic or cosmetic refinements.

