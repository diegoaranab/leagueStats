# LeagueStats visual direction

**Issue #39 · Design exploration**  
**Baseline** `82775f672e6741b6488c70d820eaf304de5dd1d3`

## Decision

**Choose A, Ranked list.** LeagueStats should be recognizable by the way it presents a decision. A player's eyes move from rank to portrait to difficulty and the evidence that matters for the queue. The top recommendation occupies one highlighted row in the same sequence as its alternatives. A separate draft rail keeps denial and lineup tools within reach while the player compares picks.

B, Pick brief, answers “Who should I pick?” faster in the initial layout and gives a captain a cleaner dedicated Draft view. It takes an additional interaction to see the full evidence for each alternate champion. A makes that evidence available immediately, which better serves the main job when the top pick is unavailable or hard to play. The largest tradeoff is the mobile Draft jump. It saves a persistent second navigation tier and keeps the ranking in one document, while B gives Draft a more visible destination and a clearer starting position after entry.

[Compare screenshots side by side](compare.html) · [Try A](prototype.html?direction=a&screen=home) · [Try B](prototype.html?direction=b&screen=home)

## Research basis

- **frontend-design** produced the competing layout plans, typography specimens and marks. The first visual move was to place the real ranked sequence on A's Home and keep queue setup dominant. The critique kept imagery to champion portraits and used rules to group the comparison. [Design plan](research/design-plan.md)
- **ui-ux-pro-max** supplied density, text reflow, touch and focus guidance and the Angular Material token model. Its gaming query suggested a showcase with 3D effects and repeated calls to action. Its shortlist query suggested minimalism with a marketing sequence. The exploration used the density and contrast ideas, then organized the screens around lane decisions and draft work. [Ranked-list search](research/ranked-design-system.md) · [Shortlist search](research/shortlist-design-system.md) · [Text reflow](research/reflow.md) · [Angular theming](research/angular.md)
- The reference flow is NA / Diamond / last 7 days / Top. Both directions use the same November 22, 2026 LeagueStats data, the same difficulty tags, and the same portrait URLs the product uses. Solo has 24 picks and recommends Darius at 52.8% win rate and 6.7% pick rate. Flex / Clash has 9 picks and recommends Camille at draft score 45, with 52 pro picks and 51 pro bans. Camille also leads draft denial. The Easy lineup is Dr. Mundo, Jarvan IV, LeBlanc, Tristana and Leona across the five roles. [Completed #34 audit](/tmp/leagueStats-ui-audit-82775f/UI_UX_AUDIT.md) · [Audit captures and measurements](/tmp/leagueStats-ui-audit-82775f/layout-metrics.json) · [Solo snapshot](assets/solo-source.json) · [Flex / Clash snapshot](assets/team-source.json)

The offline prototypes use one production context for comparison. Region, rank and window can be changed in setup. Other combinations show an explicit snapshot availability state. All five roles, sort, difficulty, evidence disclosures and the lineup run on the cached data. The comparison is an expert walkthrough supported by browser captures and measurements.

## A · Ranked list

**Home.** A direct title and one-sentence promise lead into equally visible queue choices, Region, Rank and Window. On wide screens the sample ranking shows three recognizable champions and their ladder evidence beside the form. On mobile the form comes first after the introduction, and the example follows the action.

**Solo Results.** The canonical pick appears as the highlighted ranked row, with a written recommendation label, difficulty and a reason grounded in the actual dataset. Aligned win rate, pick rate and best win estimate stay visible for every alternative. Sort and difficulty are always visible. Under a custom sort, the rank still means recommendation rank, and a compact link points to the canonical row if it moved down. Difficulty changes recompute the canonical pick among eligible champions. Bans stay scoped to the role and appear alongside the ranking on desktop or through a named jump on mobile.

**Flex / Clash Results.** Retain the same pick composition and replace the default evidence with draft score, pro picks and pro bans. A custom ladder sort puts the selected metric directly in the rows. The draft rail groups “Bans to consider” and “Five-role lineup” with a compact build disclosure. “Deny these Top picks if your team can’t secure them” explains why Camille can appear in both contexts. The role selection scopes bans. The roster spans all five roles and uses the Easy pool. Mobile offers a Draft jump and a return link to Picks. The amber coverage disclosure sits beside the evidence it affects.

**Surfaces.** One outlined Home setup surface. Results uses a page-level ranking, one tinted canonical row and an unboxed side rail. Hairlines separate entries. The functional border belongs to controls. Use 0px on flat rows, 5px portraits and 8px controls/form. Space on a 4/8px rhythm with 8–12px item insets, 16–24px grouping and about 30px between the list and rail. Inline evidence and lineup disclosures expand in document flow. Elevation is reserved for future overlay separation. The prototype uses zero elevation.

**Mark and wordmark.** Three left-aligned horizontal bars shorten as the sequence descends. The small rank glyph and the canonical row's mint edge share that geometry. Use the 26px mark next to the mixed-case Space Grotesk wordmark. The bars can read as a sorting glyph in isolation, so keep the mark paired with the wordmark in the primary lockup and repeat the geometry through the ranking itself.

## B · Pick brief

**Home.** A narrower, centered setup surface focuses attention on queue selection. The vertical rule ties the title to the short explanation before the form. Both queue options explain what changes when the player selects them. The form and CTA follow directly.

**Solo Results.** A single evidence brief leads with the champion name and portrait, the reason to pick, and three large metrics. Alternatives show a portrait, difficulty and one metric. Selecting an alternative replaces the brief and reveals a named return action to the canonical pick. The shortlist keeps its position below the brief, and the canonical champion has one dedicated presentation. Bans sit beside the shortlist on desktop and have a jump on mobile.

**Flex / Clash Results.** Picks and Draft are distinct destinations with the same context and role controls. Picks opens the Camille brief. Draft presents a lane-specific denial list and a separate all-role lineup module side by side on desktop and stacked on mobile. This is the clearest captain-focused view of the two, and a captain can return to Picks through the same navigation. The selected evidence brief depends on a tap or click to change. The draft destinations are links with current-page semantics.

**Surfaces.** One white setup surface on Home. Solo Results has three surfaces at desktop width: one lilac brief, one white shortlist and one white bans module. Team Picks uses the brief and shortlist. Team Draft uses two peer white surfaces. Use 12px panels, 8px role controls, 5–9px portraits, pill-shaped destination links and 8/16/24px grouping. Borders define modules and divide shortlist entries. The brief expands downward in place. The five-role lineup expands within Draft. The prototype uses zero elevation.

**Mark and wordmark.** Two data points share an open comparison bracket. At wordmark size it connects to inspecting two possible decisions against a shared context. At small scale the bracket can look like a plotting or messaging icon on its own. Barlow Semi Condensed gives the mixed-case name a clear narrow silhouette.

## Palette

| Role | A · Ranked list | B · Pick brief | Application |
|---|---|---|---|
| Page background | `#101820` | `#F4F5F9` | Canvas through Home and Results |
| Primary surface | `#151F28` | `#FFFFFF` | Setup and functional panels |
| Secondary surface | `#192733` | `#EFEDF9` | Canonical row or evidence brief |
| Primary text | `#F1F3EE` | `#21213B` | Names, headings, data |
| Secondary text | `#A9BBC5` | `#50536C` | Labels, context and supporting copy |
| Primary action | `#96DFC4` | `#5142AC` | Submit, meaningful links and active rules |
| On action | `#10241E` | `#FFFFFF` | Text on filled buttons |
| Selected surface | `#203830` | `#E5E0FA` | Queue or selected list option, paired with radio/indicator |
| Focus | `#ADD9FF` | `#3C37A4` | Dedicated 3px keyboard outline |
| Positive / healthy | `#B2D9CC` | `#27604C` | Freshness with written label and check |
| Warning / uncertainty | `#FFC676` | `#78510E` | Partial coverage with warning icon and copy |
| Error | `#FFABA8` | `#982B4C` | Proposed error text and icon, to pair with recovery in product |
| Divider | `#344654` | `#D8D9E5` | Passive row separation |
| Control border | `#687F8D` | `#7B7C97` | Visible interactive outlines |

| Representative pairing | A | B |
|---|---:|---:|
| Primary text on page | 16.02:1 | 14.33:1 |
| Secondary text on secondary surface | 7.69:1 | 6.49:1 |
| Secondary text on selected surface | 6.35:1 | 5.86:1 |
| Button label on action | 10.55:1 | 7.71:1 |
| Control outline on page | 4.27:1 | 3.73:1 |
| Selection accent on selected surface | 8.17:1 | 6.01:1 |
| Focus on secondary surface | 10.26:1 | 7.98:1 |
| Positive on page | 11.67:1 | 6.73:1 |
| Warning on page | 11.58:1 | 6.46:1 |
| Error on secondary surface | 8.44:1 | 6.52:1 |

The audit's cool dark, mint and amber combination works when mint has one clear action/selection role and the selected surface has its own outline and indicator. A adds a slightly darker primary surface for the setup form and separates decorative dividers from control borders. B shows that the same content can work on light paper. Its iris accent gives excellent contrast, and the pale brief pulls attention to one decision point. The color strategy supports each composition. Text labels and checkmarks identify recommendation, coverage and difficulty. [Contrast calculation](research/contrast.py)

## Typography

| Role | A · Ranked list | B · Pick brief |
|---|---|---|
| Wordmark / Home display | Space Grotesk 700. Wordmark 20–23px, Home 34–84px | Barlow Semi Condensed 700. Wordmark 24–27px, Home 34–72px |
| Page/section headings | Space Grotesk 700. Page 34–60px, section 18–22px, champion 19px | Barlow Semi Condensed 700. Page 34–60px, brief name 32–48px, section 22px |
| Body and controls | Space Grotesk 400 for prose, 500–600 for controls and 700 for the primary action. 16px body and 14–16px labels | Instrument Sans with the same weights and body/control range |
| Numeric evidence | Space Grotesk 700 with tabular figures. 15px rank, 17px values, 13px captions | Instrument Sans 700 with tabular figures. 16px shortlist values, 18–28px brief values, 13px captions |
| Line height and case | Sentence case. Headings 1.10, short Home display 0.98, prose about 1.35–1.50, data 1.15–1.20. Growth follows content | Sentence case. Headings 1.10, brief name 1.00, prose about 1.35–1.50, data 1.15–1.20. Growth follows content |

**Same-layout type trial for A.** Cinzel adds a ceremonious, small-cap display rhythm and the strongest tie to the current identity. In the phone Home specimen it adds another title line and pushes the action 34px farther down than Space Grotesk. Barlow Semi Condensed makes headings narrower, and Instrument Sans has a quieter, more neutral voice. The pair makes B's brief hierarchy crisp. In A it adds a second typographic tone to the rank-to-evidence reading path and uses narrower champion name shapes. The desktop rows have enough room for Space Grotesk, and both sans configurations reach the mobile Home action at the same y-position. **Keep Space Grotesk 400–700 across A and retire Cinzel from the product display and primary mark.** The gain is continuity with the current readable controls and one coherent everyday voice. The loss is Cinzel's familiar visual signature and some of Barlow's compact display texture.

| Specimen | Home desktop | Home mobile | Solo desktop | Solo mobile |
|---|---|---|---|---|
| A with Space Grotesk | [1366](images/a-home-1366x768.png) | [390](images/a-home-390x844.png) | [1366](images/a-solo-1366x768.png) | [390](images/a-solo-390x844.png) |
| A with Barlow Semi Condensed + Instrument Sans | [1366](images/a-type-paired-home-1366x768.png) | [390](images/a-type-paired-home-390x844.png) | [1366](images/a-type-paired-solo-1366x768.png) | [390](images/a-type-paired-solo-390x844.png) |
| A with current Cinzel + Space Grotesk | [1366](images/a-type-current-home-1366x768.png) | [390](images/a-type-current-home-390x844.png) | [1366](images/a-type-current-solo-1366x768.png) | [390](images/a-type-current-solo-390x844.png) |

## Screenshot index

### Required views

| Screen | A · 1366×768 | B · 1366×768 | A · 390×844 | B · 390×844 |
|---|---|---|---|---|
| Home / setup | [Desktop](images/a-home-1366x768.png) | [Desktop](images/b-home-1366x768.png) | [Mobile](images/a-home-390x844.png) | [Mobile](images/b-home-390x844.png) |
| Solo Results | [Desktop](images/a-solo-1366x768.png) | [Desktop](images/b-solo-1366x768.png) | [Mobile](images/a-solo-390x844.png) | [Mobile](images/b-solo-390x844.png) |
| Flex / Clash Picks | [Desktop](images/a-team-1366x768.png) | [Desktop](images/b-team-1366x768.png) | [Mobile](images/a-team-390x844.png) | [Mobile](images/b-team-390x844.png) |
| Flex / Clash Draft | [Adjacent rail](images/a-draft-1366x768.png) | [Draft view](images/b-draft-1366x768.png) | [After Draft jump](images/a-draft-390x844.png) | [Draft view](images/b-draft-390x844.png) |
| Flex / Clash expanded lineup | [Five roles](images/a-lineup-1366x768.png) | [Five roles](images/b-lineup-1366x768.png) | [Five roles](images/a-lineup-390x844.png) | [Five roles](images/b-lineup-390x844.png) |

Mobile details include [A Solo bans](images/a-solo-bans-390x844.png), [B Solo bans](images/b-solo-bans-390x844.png), [A sorted by ladder pick rate](images/a-pick-rate-team-390x844.png) and [B inspecting Akali](images/b-inspect-solo-390x844.png).

### Viewport extremes

| Screen | A · 320×568 | B · 320×568 | A · 1920×1080 | B · 1920×1080 |
|---|---|---|---|---|
| Home | [Small phone](images/a-home-320x568.png) | [Small phone](images/b-home-320x568.png) | [Wide desktop](images/a-home-1920x1080.png) | [Wide desktop](images/b-home-1920x1080.png) |
| Solo Results | [Small phone](images/a-solo-320x568.png) | [Small phone](images/b-solo-320x568.png) | [Wide desktop](images/a-solo-1920x1080.png) | [Wide desktop](images/b-solo-1920x1080.png) |
| Flex / Clash Picks | [Small phone](images/a-team-320x568.png) | [Small phone](images/b-team-320x568.png) | [Wide desktop](images/a-team-1920x1080.png) | [Wide desktop](images/b-team-1920x1080.png) |

### Enlargement and keyboard evidence for A

| Probe | Home | Solo | Flex / Clash |
|---|---|---|---|
| 200% text-only at 390×844 | [Start](images/a-text-200-home-390x844.png) · [Setup scrolled](images/a-text-200-home-detail-390x844.png) | [Start](images/a-text-200-solo-390x844.png) · [Rows scrolled](images/a-text-200-solo-detail-390x844.png) | [Start](images/a-text-200-team-390x844.png) · [Rows scrolled](images/a-text-200-team-detail-390x844.png) |
| Chromium page zoom 200% at 1366×768 | [Home](images/a-native-zoom-200-home-1366x768.png) | [Solo](images/a-native-zoom-200-solo-1366x768.png) | [Flex / Clash](images/a-native-zoom-200-team-1366x768.png) |
| 844×390 landscape with reduced motion | [Home](images/a-landscape-home-844x390.png) | [Solo](images/a-landscape-solo-844x390.png) | [Flex / Clash](images/a-landscape-team-844x390.png) |

[Visible keyboard focus on the Home action](images/a-keyboard-home-390x844.png) · [Measured layout and font evidence](research/render-metrics.json)

## Responsive and accessibility observations

- At 320×568, both directions show the queue choices and the full Home action. At 390×844, A makes the canonical pick and two full alternatives' core metrics available on the first screen in each queue. B reveals the lead recommendation higher and allows the viewer to scan several names and a single number per alternative. At 320px the alternatives in both directions start below the fold. At 1920px the maximum content widths preserve eye travel and metric alignment.
- Representative prototype controls use 44px or larger targets, with the whole queue choice as the radio's label. Native selects and evidence disclosures respond to keyboard and touch. Status uses text and an icon, and active role styling includes an underline. List rows and disclosures grow with text. Keyboard execution covered the skip link, Flex / Clash setup submission, a role change and opening a champion's evidence with Enter. Structured headings and names were checked in Chromium.
- Chromium page zoom at 200% produces a 683px CSS viewport without horizontal overflow. The separate text-only test doubled rendered text sizes at 390px and used the longer Latin America North value. Labels, ranks and values wrap or remain visible without measured clipping. The complete 200% setup and recommendation require ordinary vertical scrolling. Keep the full names and let the form and rows grow. The checks used emulated touch and desktop Chromium. Production Angular Material behavior, actual devices and assistive technology require implementation-stage verification.

### First-screen measurements

Positions use CSS pixels from the top of the page. Alternative counts include complete entries visible before scrolling. Each A alternative shows three values and each B alternative shows one.

| Measure | A at 390×844 | B at 390×844 | A at 1366×768 | B at 1366×768 |
|---|---:|---:|---:|---:|
| Home action starts | 475 | 471 | 472 | 503 |
| Solo recommendation starts | 384 | 250 | 361 | 273 |
| Solo alternatives fully visible | 2 | 4 | 4 | 6 |
| Flex / Clash recommendation starts | 428 | 267 | 405 | 273 |
| Flex / Clash alternatives fully visible | 2 | 2 | 3 | 2 |

For comparison, in the #34 audit the Home action started at 910px on 390×844 and 590px on 1366×768. The production comparison grid began at 1046px and 789px for Solo, and 1424px and 976px for Flex / Clash. The production grid repeated its canonical champion at the first position. [Audit measurements](/tmp/leagueStats-ui-audit-82775f/UI_UX_AUDIT.md) · [Prototype measurements](research/render-metrics.json)

## Decision matrix

| Criterion | A · Ranked list | B · Pick brief |
|---|---|---|
| LeagueStats distinctiveness | Rank, portrait and evidence repeat a recognizable grammar across tasks. The mark borrows that geometry. | The active brief gives the portrait a stronger focal role. The bracket is less specific at icon size. |
| Fast comprehension | Recommendation label and aligned metrics make the pick and the comparison visible together. | The champion name and brief appear higher, giving the fastest first answer. |
| Scanability | Rank and evidence run in consistent columns. Portrait recognition carries across positions. | Names are easy to scan. Full evidence swaps in on selection, and dual columns add a reading-direction choice. |
| Comparison density | Three evidence values per alternative remain visible in both queues. | One value per alternative fits more names in some views. Full comparisons require a click or tap per alternate. |
| Mobile usability | Setup submits above the fold at 320px. At 390px there are two full alternate rows with core evidence in each queue. | Setup also fits. The primary answer is prominent and draft entry stays close. The brief and list use more distinct blocks. |
| Flex / Clash clarity | Draft purpose is visible alongside Picks on desktop. Mobile reaches it via a named jump and return link. | Best dedicated draft workspace. The explicit Draft destination puts denial and lineup into one focused view. |
| Accessibility risk | Inline expansion and stable document order simplify focus, with more text and numbers per row at 200%. | Larger reading sizes for the brief. Replacing the inspected champion requires focus and selected-state management. |
| Material integration | Native prototype shapes map to existing Angular Material fields and controls, with custom ranked presentation. | Controls and panel shapes also map to Material. Destination state and inspector focus need integration. |
| Implementation complexity | Medium. One ranked renderer, adaptive draft rail and anchored canonical row. | Medium-high. Adds view and inspector state, return behavior and responsive two-column ordering. |
| Long-term extensibility | Predictable role evidence schema. Additional metrics can enter row disclosure when needed. | Easy to enrich the focused brief or draft workspace. Expanding the number of inline metrics erodes the shortlist’s simplicity. |
| Visual longevity | A typographic sequence, portrait rhythm and semantic color carry the identity with few dependencies. | A calm light palette and condensed hierarchy age well. The brief relies more on portrait crop and card treatment. |

## Implementation implications

1. Apply A's color and type tokens through the existing Angular Material theme and app typography. Use the quiet outline for dividers, the stronger one for controls, and the focus token for keyboard navigation. Use a person-readable status label beside warning and error.
2. Keep the typed setup form and return context. Put both queue choices and editable context before the submit. At compact widths place any reference ranking after the form.
3. Build one ranked surface with mode-specific evidence definitions. Use recommendation rank as the row identifier even when another metric sorts the list. Keep the canonical reason and details on the same row, with a named jump when sorting moves it down. Difficulty refines Picks while role context scopes bans. Preserve the current ranking, ban and lineup logic.
4. Keep Picks primary and put the team draft rail beside it wherever the content fits. At compact widths expose the named Draft jump beside the role controls, group denial and five-role lineup, and return the user to Picks predictably. Present the coverage note close to the affected evidence.
5. Carry the audit's route restoration and overlay focus work into the relevant implementation slices. Exercise long context labels, custom sorts, sparse/empty results, lineup-unavailable state, 200% text and actual Material focus behavior before calling the product update complete.

All prototypes and rendered evidence are under `/tmp/leagueStats-visual-direction-82775f/`. Product implementation has not started.
