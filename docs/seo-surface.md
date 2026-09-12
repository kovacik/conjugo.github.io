# SEO surface: sitemap.xml, robots.txt, llms.txt and structured data

> Ported from the trinitysports `seo-surface` skill. Same principle, different stack:
> everything here is **generated at build time**. There is no file to hand-maintain.

## Read this first: they are generated, not maintained

| File | Comes from | Edit it? |
|---|---|---|
| `/sitemap.xml` | `jekyll-sitemap`, from the pages themselves | ❌ never — it has no source file |
| `/robots.txt` | `robots.txt` at the repo root (Liquid) | ✅ only to change directives |
| `/llms.txt` | `llms.txt` at the repo root (Liquid) | ✅ the prose; the page list generates |
| Title, canonical, Open Graph, `WebSite` JSON-LD | `jekyll-seo-tag` via `{% seo %}` | ❌ never hand-write these in the layout |
| `MobileApplication` JSON-LD | `_includes/app-schema.html` | ✅ when the app's facts change |

**Adding a page updates the sitemap and llms.txt by itself.** If asked to "update the
sitemap after adding a page", the answer is that it already did — then run the check
below to prove it.

Both plugins are on GitHub Pages' allowed list, so they run on the live build with no
Actions workflow. Do not add a static `sitemap.xml`; it would shadow the generated one
and go stale silently.

## The check

```bash
bundle exec jekyll build && python3 script/check-seo.py
```

No dependencies, runs anywhere. It asserts that the three files exist, that every built
page appears in both the sitemap and llms.txt, that the sitemap lists nothing that isn't
built, that each page has exactly one `<title>`, one canonical and one `og:title`, that
every meta description fits in the ~157 characters Google will display, that every
JSON-LD block parses, and that the homepage still carries a real App Store link rather
than a placeholder.

It also fails if the app schema declares an `aggregateRating`. That property is only
legitimate once the App Store rating is real — inventing one is a manual-action risk,
and a stale one is worse than none.

Run it after touching pages, front matter, `_config.yml` or the layout.

## Adding a page

1. Create the `.md` with `layout: default`, a `title:`, a `description:` (**≤ 157 chars** —
   the check enforces it) and a `permalink:`.
2. Nothing else. Sitemap, llms.txt, canonical and Open Graph all follow.
3. Run the check.

Page titles must **not** repeat the brand: `jekyll-seo-tag` appends it, so `title: "Support"`
renders as `Support | ConjuGo`. A title of `Support — ConjuGo` would render as
`Support — ConjuGo | ConjuGo`.

## Structured data

`_includes/app-schema.html` emits `MobileApplication` JSON-LD on the homepage only. It is
how Google can show price and platform in a rich result, and how AI assistants answer
"recommend a French conjugation app".

Keep it factually identical to the App Store listing: price, the five tenses, iOS 18.6
minimum, and no claim of tenses the app doesn't ship. If the listing changes, this changes.

## Search Console

1. Add `https://conjugo.me` as a property.
2. Verify by **domain** (a DNS TXT record at your registrar) if you can — it survives
   hosting changes. Otherwise use the HTML-tag method and paste the token into
   `google_site_verification` in `_config.yml`; an empty value emits nothing.
3. Submit `https://conjugo.me/sitemap.xml` once. Google refetches on its own afterwards —
   no resubmission needed after a content change.
4. The sitemap only reaches Google **on deploy**, not on local build.

## Where the traffic is actually winnable

Recorded here so it is not re-litigated every time: the head terms for French conjugation
(`conjuguer <verb>`, `french conjugation`) belong to Reverso, Larousse, WordReference and
Lawless French, and are not winnable with four pages and no backlinks. The winnable
queries are the ones those sites answer badly or not at all:

- **App-intent**: "best app to practice french verbs", "Conjuu alternative", "app for passé composé"
- **Teaching long-tail**: "passé composé vs imparfait", "avoir or être", "when to use conditionnel"
- **Verb-specific practice**: "practice conjugating <verb>" — distinct from looking it up

The in-app `GrammarTopics` content already answers the middle group and is fact-checked
against the conjugation engine, so publishing it costs no new writing.

Trinity's rule applies unchanged: **an article with no path to what you sell is traffic
that cannot convert.** Every article ends at the App Store, through a Custom Product Page
so the traffic is attributable — see `analytics-setup.md` §4.
