# Early Trends — static site

Plain HTML/CSS + a few lines of vanilla JS. No build step.

- Preview locally: `python3 -m http.server 8000` in this folder, then open http://localhost:8000/
- Deploy: push this folder's contents to a repo named `early-trends`, then Settings → Pages → Deploy from branch (root).
  Expected URL: https://bjornsjeldrup.github.io/early-trends/
- All internal links are relative, except `404.html`, which uses absolute `/early-trends/` paths
  (GitHub serves it from any missing URL depth). Change those if the repo name changes.
- Canonical/OG URLs and sitemap.xml use the full Pages URL; update them if the domain changes.

## Placeholders to fill later
Search for these HTML comments:
- `AdSense:` — head script location (each page). Also create `ads.txt` at the domain root.
- `AD SLOT:` — empty `<div class="slot" hidden>` ad containers.
- `AFFILIATE SLOT:` — empty affiliate link containers (use `rel="sponsored nofollow noopener"`).
- `CONTACT:` — contact method on about.html.

## Categories
Twelve shopping categories live in `categories/<slug>.html` with a hub at `categories/index.html`:
toys-collectibles, fashion-apparel, beauty-makeup, food-drink, books-media, tech-gadgets,
home-decor, sports-outdoors, baby-kids, health-wellness, pet-supplies, kitchen-dining.
`categories/case-studies.html` is a retrospectives shelf beside those twelve (Labubu, air up).
Trend cards use `data-category="<slug> [<slug>...]"` so the filter on trends/index.html works.
Signals-by-category summary table: trends/how-we-spot-trends.html#signals-by-category.

## Content status
Twenty-four buyable picks are published under `trends/`, linked from each category's
"Trends we're watching" section, from `trends/index.html`, and as three featured
cards on the homepage (Summer Fridays Lip Butter Balm, BubblePlush, Emma M. Lion).
Every published pick has a Where to buy link on Amazon with Associates tag `earlytrends-20`.
Labubu and air up are retrospectives on `categories/case-studies.html` (`trends/labubu-case-study.html`, `trends/air-up-case-study.html`). The method page only teases them.
Signal meters summarize the cited sources.
The October 28, 2026 batch is marked Identified on 2026-10-28. HOZO NeoSander and InvisOutlet Aura are marked 2026-10-31.
Machine-readable rows live in `trends/tracker.json` (status `watching`; `last_reviewed` is null).
No traffic or earnings figures are claimed beyond numbers in the cited sources.
Free RSS: `feed.xml` for picks, `feeds/<category>.xml` per category including `feeds/case-studies.xml`, explained on `subscribe.html`. Email alerts are not set up.
