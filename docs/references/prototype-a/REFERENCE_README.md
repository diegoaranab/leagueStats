# Approved LeagueStats Prototype A

This directory contains the original offline visual-direction bundle from the November 22, 2026 evaluation. The archive name was `leagueStats-visual-direction-82775f.zip`. Its SHA-256 was verified as `9ef3db5d4bf889436e76bc8184b53fc64626cf623302abebc4dd47fdd9c55c81`. The files listed in `SHA256SUMS` were extracted byte for byte. Verify them with `sha256sum -c SHA256SUMS` from this directory.

The approved visual direction is **A · Ranked list**. The sole approved contribution from B is the named compact Flex / Clash Draft destination and its return to Picks. [Approval comment on #39](https://github.com/diegoaranab/leagueStats/issues/39#issuecomment-7093873994)

The evaluation started from `82775f672e6741b6488c70d820eaf304de5dd1d3`. The corrective implementation under #57 starts from `cbb32553dd6b3615bb3545271ae5d2e1c502f05c`. [Issue #57](https://github.com/diegoaranab/leagueStats/issues/57) · [Parent #34](https://github.com/diegoaranab/leagueStats/issues/34)

- [Original visual direction](VISUAL_DIRECTION.md) and [browser measurements](research/render-metrics.json)
- [Original HTML](prototype.html), [CSS](prototype.css) and [JavaScript](prototype.js)
- [Solo historical snapshot](assets/solo-source.json) and [Flex / Clash historical snapshot](assets/team-source.json) for NA, Diamond, Last 7 days, generated November 22, 2026 UTC
- Approved default captures use `images/a-{home,solo,team}-{1366x768,1920x1080,390x844,320x568}.png`. Also see `a-solo-bans-390x844.png`, `a-draft-*.png` and `a-lineup-*.png`. The original captures also include landscape, enlarged text, keyboard and native zoom.
- [B compact Draft capture](images/b-draft-390x844.png) shows the interaction referenced in the approval. The B visual specimens and alternate typography trials are historical research.

Open `prototype.html?direction=a&screen=home`, or set `screen=solo` or `screen=team`, to inspect the original locally. The original prototype only implements the historical snapshot. The Angular browser regression intercepts dataset and portrait requests with that snapshot for deterministic comparisons. The historical JSON and prototype remain outside the Pages build. Home includes an explicitly dated example derived from three rows in the Solo snapshot.

The Angular build uses the matching Space Grotesk file from the bundle. [Font license](../../../apps/web/public/fonts/space-grotesk-OFL.txt)
