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
Twelve categories live in `categories/<slug>.html` with a hub at `categories/index.html`:
toys-collectibles, fashion-apparel, beauty-makeup, food-drink, books-media, tech-gadgets,
home-decor, sports-outdoors, baby-kids, health-wellness, pet-supplies, kitchen-dining.
Trend cards use `data-category="<slug> [<slug>...]"` so the filter on trends/index.html works.
Signals-by-category summary table: trends/how-we-spot-trends.html#signals-by-category.

## Content status
Trend cards are a Labubu historical case study plus clearly labelled fictional examples
(one or two per category). Replace them with real posts; see the `HOW TO ADD A REAL TREND`
comment in trends/index.html. No traffic or earnings figures are claimed anywhere.
