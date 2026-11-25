# Prototype A implementation comparison

The Angular Pages build was compared with the original Prototype A PNGs for NA, Diamond, Last 7 days, Top, using the historical Solo and Teamplay fixtures. The fixture contains 24 eligible Solo picks and nine Teamplay picks. The test loads the same Space Grotesk binary and historical portraits, waits for visible images and fonts to settle, and captures the viewport at device scale factor 1. Default captures use the same scroll position. Draft, lineup and Solo bans include reference-position captures plus separate keyboard-destination captures where focus is part of the interaction.

[Download the comparison archive](prototype-a-comparison.zip). Extract it and open `index.html` for side-by-side views, links to full viewport PNGs, measurements and validation logs.

| Screen | Area | Classification | Finding |
| --- | --- | --- | --- |
| Home | Composition, typography and width | MATCH | The approved headline and promise lead the editorial column above the three historical ranking rows. The outlined setup panel is vertically centered beside that column on desktop. |
| Home | Header, surface, controls and spacing | MATCH | The wordmark and toolbar align with content. The matte setup surface, mint top rule, two choices, three external labels and 48px action follow A. |
| Home | Ranking and provenance | JUSTIFIED_ADAPTATION | The same Darius, Akali and Irelia rows include the snapshot date to identify the example as historical. |
| Home | Compact order and behavior | MATCH | The introduction, form and example follow that order. The region gets its own line above Rank and Window. Keyboard selection, explicit submission and returning context passed. |
| Home | Accessible controls | JUSTIFIED_ADAPTATION | Pressed-state queue buttons and Material select menus retain the application's keyboard and focus behavior. The select menu itself is a Material overlay. |
| Solo | Composition, width and surfaces | MATCH | The open title, compact context, queue navigation, underlined roles, 30px gap and unboxed bans rail follow A. |
| Solo | Ranking density and information | MATCH | The first viewport has four full alternatives at 1366×768 and two at 390×844. Flat rows, portraits, three evidence values and the canonical explanation match the approved hierarchy. |
| Solo | Bans availability | MATCH | The three bans are beside the first rows on desktop and a named action sits immediately below roles on compact layouts. Bans use the full lane across difficulties. |
| Solo | Focus and evidence | JUSTIFIED_ADAPTATION | The compact rail has a Return to Picks action. The ranked row chevron keeps its champion-specific accessible name and focus. The freshness disclosure exposes dataset provenance. |
| Flex / Clash | Composition, controls and ranking | MATCH | The ranking uses A's title, type scale, controls and row geometry with draft score, pro picks and pro bans. The first viewport has three full alternatives at 1366×768 and two at 390×844. |
| Flex / Clash | Draft rail | MATCH | Draft groups Bans to consider and the five-role lineup alongside Picks, with a single compact lineup disclosure. The same champion can appear as a pick and a denial candidate. |
| Flex / Clash | Mobile interaction and details | JUSTIFIED_ADAPTATION | The named Draft jump and Return to Picks move keyboard focus to their destination headings. The lineup method disclosure explains how five unique Easy champions are chosen and the role of ranking. |
| Flex / Clash | Coverage | JUSTIFIED_ADAPTATION | The visible amber summary uses the production coverage diagnosis and expands to source dates and warnings. This preserves the 44px disclosure and the affected comparison remains directly below it. |
| Both Results modes | Functional and accessibility requirements | JUSTIFIED_ADAPTATION | A compact Filters action opens the existing focus-managed drawer at all widths. Sort and Difficulty appear in the ranking header with immediate updates. Route-entry focus appears in direct-entry captures. Recommendation rank stays canonical under alternate sorts and displaced evidence remains in the details panel. |
| All | Responsive and accessibility checks | MATCH | Four required viewports, 844×390 landscape, Chromium native page zoom at 200%, keyboard focus and reduced motion passed. The regression separately tests the reference's text-only enlargement and 200% root font size. |
| Both Results modes | 200% text-only reflow | JUSTIFIED_ADAPTATION | Filters moves below the main title when enlarged text fills the line. The expanded coverage summary wraps where needed. This moves the first ranked rows down 37px in Solo and 49px in Flex / Clash while retaining their reference heights and keeping controls and evidence readable. |
| All | External validation | NOT_VERIFIED | The comparisons use historical fixtures. Independent screen reader and physical-device sessions, deployed production validation and human visual acceptance are pending. |

**Unresolved visual differences** None identified in the matched browser evidence. Small subpixel and line-height differences are visible in individual rows. The captures support a human fidelity review without assuming pixel equality.

## First-viewport geometry

The y positions are CSS pixels from the top and agree with the captured reference at each required viewport. See the archive for x positions, widths, row heights and interaction states.

| Viewport | Home action y | Solo canonical y | Flex / Clash canonical y | Fully visible alternatives (Solo / Flex) |
| --- | ---: | ---: | ---: | ---: |
| 1366×768 | 472 | 361 | 405 | 4 / 3 |
| 1920×1080 | 504 | 361 | 405 | 9 / 8 |
| 390×844 | 475 | 384 | 428 | 2 / 2 |
| 320×568 | 512 | 445 | 489 | 0 / 0 |

The desktop Solo bans section starts at y=280 at both desktop widths. The first ban row is fully visible with 10, 20, 30 and 38 picks. The desktop Draft rail starts at y=280 with the bans at y=310 and the lineup at y=544.

## Review files

- Original source, captures, fixture data and approval provenance are indexed in [REFERENCE_README.md](REFERENCE_README.md).
- The ZIP includes raw screenshots, reference and candidate positions, viewport dimensions, font and clipping checks, plus validation logs.
- The regression is in `apps/web/tests/prototype_a_fidelity_browser.py`. Build Pages, generate the static route entries, then run the script with `--evidence <directory> --native-zoom`. For an explicit external artifact use `PROTOTYPE_A_TEST_URL`.
