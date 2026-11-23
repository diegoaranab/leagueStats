# LeagueStats Design System

## 1. Purpose and authority

This document is the current approved LeagueStats product-design contract. Future UI work should use it without needing prototype bundles, old chat history, or issue threads. GitHub issues retain decision rationale and historical evidence; this file records the current system.

The approved direction is **A · Ranked list**, with one targeted interaction adaptation from B: explicit compact/mobile Flex / Clash Draft discovery. A and B are not competing current options; B is historical evidence for that discovery improvement.

## 2. Decision states

- **LOCKED** — Approved and expected in future LeagueStats UI work until explicitly superseded. A future PR must not silently contradict it.
- **GUIDELINE** — Preferred design/system pattern. It may adapt when real product, responsive, or accessibility evidence justifies the change.
- **OPEN** — Intentionally unresolved. It is not an approved decision and must not be treated as one.
- **EVIDENCE** — Prototype/audit measurements that informed a decision. They help validate intent but are not necessarily literal production requirements.

## 3. Product design principles

- **LOCKED:** Results should help people identify a strong usable champion quickly and compare viable alternatives.
- **LOCKED:** Preserve existing ranking, ban, and lineup semantics and algorithms.
- **LOCKED:** Make the purpose of each mode, task, sort, and status understandable in context.
- **GUIDELINE:** Spend visual emphasis on ranking, portraits, evidence, selection, and meaningful state rather than ornamental chrome.

## 4. Identity and visual grammar

- **LOCKED:** LeagueStats' repeated visual grammar is **rank → portrait → difficulty/evidence**. Ranking sequence is the primary visual structure.
- **LOCKED:** The canonical recommendation is one highlighted row inside the same ranking, not a duplicated standalone full Spotlight card.
- **LOCKED:** Build identity from ranking, portraits, evidence, and decision hierarchy rather than generic fantasy UI, esports ornamentation, or gaming chrome. Do not imitate the Riot client or proprietary Riot/League visual language.
- **LOCKED:** Three descending horizontal bars may participate in wordmark/ranking geometry. The prototype used approximately 26px beside the mixed-case wordmark. Keep the motif contextual to wordmark, ranking, or canonical-row geometry.
- **OPEN:** Standalone three-bar app/icon treatment. In isolation, the bars can read as sort, filter, or menu/data controls; they are not an approved standalone app icon.

## 5. Color system

**LOCKED — semantic roles and approved palette:**

| Role | Color |
| --- | --- |
| Page / canvas | `#101820` |
| Primary surface | `#151F28` |
| Secondary / canonical surface | `#192733` |
| Primary text | `#F1F3EE` |
| Secondary text | `#A9BBC5` |
| Primary action | `#96DFC4` |
| On-action text | `#10241E` |
| Selected surface | `#203830` |
| Focus | `#ADD9FF` |
| Positive / healthy | `#B2D9CC` |
| Warning / uncertainty | `#FFC676` |
| Error | `#FFABA8` |
| Divider | `#344654` |
| Control border | `#687F8D` |

Semantic meaning and accessible contrast take precedence over mechanically reusing a literal token where a future component or state requires adaptation. This document specifies semantic roles; it does not establish production CSS variable names.

- **LOCKED:** Mint is constrained to meaningful action, selection, and active rules; do not use it as decoration throughout the interface.
- **LOCKED:** Amber means uncertainty, partial coverage, or attention requiring explanation, not generic accent decoration.
- **LOCKED:** Error and healthy states need readable status meaning and must not rely on color alone.
- **LOCKED:** Passive dividers and interactive control borders are separate roles.

## 6. Typography and numerical data

- **LOCKED:** Space Grotesk weights 400–700 is the approved primary family for wordmark, display, body, and data.
- **LOCKED:** Use tabular numerals for comparable numerical data where available.
- **LOCKED:** Cinzel is retired from primary product display language.
- **LOCKED:** Do not introduce Barlow Semi Condensed or Instrument Sans unless a later evidence-backed decision explicitly supersedes this system.
- **GUIDELINE:** Keep champion names and evidence labels easy to scan at the density needed for comparison.

## 7. Surfaces, borders, radius, spacing, and elevation

**GUIDELINE — preferred geometry, not universal pixel requirements:**

- Flat ranked rows: `0px` radius.
- Champion portraits: approximately `5px` radius.
- Controls and forms: approximately `8px` radius.
- Preferred spacing rhythm: `4 / 8px`.
- Item/row insets: approximately `8–12px`.
- Grouping: approximately `16–24px`.
- Ranked list to Draft rail: approximately `30px` where layout permits.
- Prefer flat rows, hairline separators, and minimal elevation for primary Results presentation. The prototype baseline uses zero elevation; reserve elevation primarily for genuine overlay or separation needs.
- Avoid nested rounded panels as the default structural grammar.

Adapt these values when text reflow, touch targets, or actual layout evidence requires it. Passive dividers are visually quieter than interactive control borders.

## 8. Results information hierarchy

- **LOCKED:** Repeated ranked entries expose recommendation rank, portrait, champion, difficulty, and relevant comparable evidence.
- **LOCKED:** The canonical #1 receives stronger emphasis but remains in the same sequence.
- **LOCKED:** Recommendation rank remains recommendation rank under alternate sorting. Show the metric driving the current sort. If sorting moves the canonical recommendation away from the top, provide a clear path back to it.
- **GUIDELINE:** Use progressive disclosure for secondary/source details instead of repeating dominant panels.

## 9. Solo Queue pattern

- **LOCKED:** Picks are primary. Recommended bans stay nearby, are scoped to the selected role, and remain subordinate to champion selection.
- **LOCKED:** Do not duplicate the canonical champion in a separate full Spotlight surface.
- **GUIDELINE:** Difficulty may refine eligible picks without changing the semantic meaning of recommendation rank.
- **LOCKED:** Preserve current ranking and ban algorithms.

## 10. Flex / Clash pattern

- **LOCKED:** Picks are the landing/default task. Treat **Picks**, **Draft / denial**, and **five-role lineup** as distinct user jobs.
- **GUIDELINE:** On wide layouts, the Draft rail may sit adjacent to Picks when content fits.
- **LOCKED:** On compact/mobile layouts, provide an explicit named Draft destination/jump and a predictable return to Picks.
- **GUIDELINE:** Group lane-scoped denial and the five-role lineup in Draft. Place coverage/uncertainty messaging near the evidence it qualifies.
- **LOCKED:** A champion may validly be both a recommended pick and a ban/denial candidate when underlying semantics support both. Wording and context must explain the distinction.
- **LOCKED:** Preserve existing ranking, ban, and lineup algorithms.

## 11. Home / setup pattern

- **LOCKED:** Home is setup, not a marketing landing page. Its key job is to configure recommendation context and enter Results quickly.
- **LOCKED:** Make both queue choices readily discoverable. Preserve editable Region, Rank, and Window controls and an explicit **View recommendations** action.
- **GUIDELINE:** Avoid large explanatory content that pushes the first user decision or action unnecessarily far down the page.
- **LOCKED:** Preserve the durable URL/context contract delivered by #40.

## 12. Angular Material and interaction behavior

- **LOCKED:** Preserve mature Angular Material behavior where it already provides accessible control semantics.
- **LOCKED:** Theme and style through application tokens, Material tokens, and custom ranked presentation. Do not discard accessible Material behavior to achieve a visual look, and do not leave controls looking generically default-Material.
- **LOCKED:** Do not reintroduce deprecated legacy Angular animation providers.
- **LOCKED:** Keep controls keyboard-operable with semantic labels and visible keyboard focus.
- **LOCKED:** Critical meaning must not depend on color alone, hover alone, or motion alone.
- **GUIDELINE:** Frequent touch actions should target approximately `44 CSS px` where practical, while preserving dense comparison layouts where evidence supports them.

## 13. Responsive behavior

- **LOCKED:** Use content-driven breakpoints as the design rule, rather than device-name breakpoints.
- **LOCKED:** Prefer wrapping, growth, and document flow over clipping, truncating important labels, or horizontal overflow.
- **LOCKED:** Mobile must preserve the same product meaning, not merely stack desktop cards.
- **GUIDELINE:** Validate long values such as “Latin America North” in their actual controls and layouts.

## 14. Accessibility

**LOCKED:** Preserve visible keyboard focus, semantic labels, keyboard operation, text reflow, readable status labels, and critical meaning that is not color-, hover-, or motion-only. Consider frequent touch target size around `44 CSS px` where practical. Validate the actual component and state contrast when implementing; palette evidence below does not replace that work.

## 15. Prototype verification evidence

These measurements verify the prototype direction. Future production components still require their own contrast validation.

**EVIDENCE — A contrast:**

| Pair | Measured contrast |
| --- | ---: |
| Primary text / page | 16.02:1 |
| Secondary text / secondary surface | 7.69:1 |
| Secondary text / selected surface | 6.35:1 |
| Button label / action | 10.55:1 |
| Control outline / page | 4.27:1 |
| Selection accent / selected surface | 8.17:1 |
| Focus / secondary surface | 10.26:1 |
| Positive / page | 11.67:1 |
| Warning / page | 11.58:1 |
| Error / secondary surface | 8.44:1 |

**EVIDENCE — responsive and interaction evaluation:** Prototype A was evaluated at `320×568`, `390×844`, `1366×768`, `1920×1080`, `844×390` landscape, `390×844` with 200% text-only enlargement, and `1366×768` with 200% browser zoom, plus reduced motion and keyboard focus probes.

Representative `390×844` measurements:

- Home action: approximately `475px`.
- Solo canonical: approximately `384px`; two complete alternatives visible.
- Flex / Clash canonical: approximately `428px`; two complete alternatives visible.

These are **design-density evidence**, not exact production pixel acceptance criteria.

## 16. Open design questions

- **OPEN:** Final standalone treatment of the three-bar mark/icon. Until resolved, keep it contextual to wordmark, ranking, or canonical-row geometry.

## 17. Maintenance and supersession

If a future PR intentionally changes a **LOCKED** rule, it must either:

1. Update `docs/DESIGN_SYSTEM.md` in that same atomic PR; or
2. Link an approved dedicated design-decision issue/PR that supersedes the existing rule first.

A future implementation PR must not silently diverge from this canonical document. Historical issues remain rationale and evidence; this Markdown file represents the current approved state.

## 18. UI PR preflight checklist

- [ ] Did this PR read `docs/DESIGN_SYSTEM.md`?
- [ ] Does it conflict with a **LOCKED** rule? If so, where is the approved superseding decision or same-PR document update?
- [ ] Where relevant, does hierarchy remain rank → portrait → evidence?
- [ ] Is the canonical recommendation duplicated outside the ranking?
- [ ] Is the active sort metric visible, with a clear path back to the canonical recommendation?
- [ ] Are focus, semantic labels, and keyboard behavior preserved?
- [ ] Does mobile preserve product meaning and provide compact Flex / Clash Draft discovery?
- [ ] Were long labels and 200% text/zoom behavior considered?
- [ ] Are warning, error, healthy, and other status meanings readable without color alone?
- [ ] Were existing ranking, ban, and lineup semantics preserved?
