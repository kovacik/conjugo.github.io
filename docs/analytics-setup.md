# Website analytics: what's in the code, what's left to do in the browser

> Companion to the app-side spec at `conjugo/design/docs/2026-07-25-analytics-spec.md`.
> That document owns the App. This one owns conjugo.me and the seam between them.

## 1. TL;DR — the code is done, the tag is off

Everything needed to measure this site is committed. Nothing is being collected yet,
because `ga4_measurement_id` in `_config.yml` is empty.

| Piece | Where | State |
|---|---|---|
| GA4 tag + Consent Mode v2 | `_includes/analytics.html` | ✅ committed, dormant |
| Consent banner | `_includes/consent-banner.html` | ✅ committed, dormant |
| Banner styling | `assets/css/styles.css` (end of file) | ✅ |
| `app_store_click` event | `_includes/analytics.html` | ✅ |
| CTA labelling | `data-cta` on both store links in `index.md` | ✅ |
| Privacy disclosure | `privacy.md` §1.4, §3, §4 | ✅ |
| Measurement ID | `_config.yml` | ⬜ **you, in the browser** |

**An empty ID emits nothing at all** — no script, no banner, no cookies. That is deliberate:
the site is legal to serve today, and measurement switches on in one commit when you're ready.

## 2. Put the web stream in the *same* property as the app

This is the decision that matters, and it is easy to get wrong by clicking "Create property".

Firebase Analytics **is** GA4. Your app already reports into a GA4 property (the one holding
the 31 events in the app spec). Add the website as a **second data stream inside that same
property** — do not create a new one.

- Same property → one funnel from "read a grammar article" to "purchased", and the audiences
  you build there are usable by Firebase Remote Config A/B testing.
- New property → two dashboards that can never be joined, and you will end up quoting whichever
  number is more flattering.

**Analytics → Admin → Data streams → Add stream → Web.** URL `https://conjugo.me`, name
`conjugo.me`. Copy the `G-XXXXXXXXXX` it gives you into `_config.yml`, commit, push.

Leave **Enhanced measurement ON** — it gives scroll depth, outbound clicks and site search for
free. It does *not* cover the App Store links (see §4), which is why those are tracked manually.

## 3. Console tasks, once

### A. Mark `app_store_click` as a key event
**Admin → Events → Key events → Mark as key event.** The event name only appears after it has
fired once, so click your own Download button after deploying, then come back.

Without this it is just another row in a table. With it, GA4 reports conversion rate per page,
per referrer and per country — which is the whole point of measuring this site.

### B. Hygiene (5 minutes, do once)
- **Data retention → 14 months.** Default is 2 months, which silently destroys year-over-year
  comparison. This is the single most regretted default in GA4.
- **Google signals → OFF.** It enables cross-device advertising features you do not use, and it
  is the part of GA4 that draws EU regulatory attention. Your tag already denies the ad_* signals;
  turning this off makes the property agree with the tag.
- **Internal traffic filter** → add your own IP, so your editing sessions don't look like demand.
- **Unwanted referrals** → add `apps.apple.com`, so a bounce back from the store doesn't start a
  fake new session.

### C. Verify (do this, don't assume)
1. Open conjugo.me in a private window → the banner appears.
2. **Realtime** in GA4 shows one user. Cookies: none yet (check DevTools → Application).
3. Click **Accept** → `_ga` cookies appear.
4. Click **Download on the App Store** → `app_store_click` shows in Realtime within ~30s,
   with `link_location = hero` or `footer_badge`.
5. In another private window, click **Decline** → no `_ga` cookie is ever written, and Realtime
   still counts the visit. That cookieless count is Consent Mode working, not a bug.

## 4. The seam: web → install is not directly measurable

Be honest about this boundary, because every "attribution" tool that claims otherwise is guessing.

When someone leaves conjugo.me for the App Store, **GA4 loses them**. Apple does not tell your
website what happened next. So the join has to happen on Apple's side:

1. Build a **Custom Product Page** in App Store Connect per web surface (one for the homepage,
   one per article once articles exist). Free, up to 35.
2. Link to the CPP URL instead of the bare listing, and add campaign parameters:
   `…/app/id6757608840?pt=<providerToken>&ct=homepage&mt=8`
3. **App Store Connect → App Analytics → Sources** then reports impressions, downloads and
   *conversion rate* per `ct` value.

So the chain reads: GA4 tells you how many people clicked (`app_store_click` by page), ASC tells
you how many of those installed (by campaign token). Neither tool sees both halves. Keep the `ct`
value identical to the `data-cta` value and the two reports line up by hand in seconds.

## 5. The weekly readout — six numbers, one direction each

Pulling numbers is not measurement; deciding something is. Once a week:

| Number | Where | What it decides |
|---|---|---|
| Product page conversion rate | ASC | Whether the preview video and screenshots are working |
| `app_store_click` per page | GA4 | Which page or article deserves more of the same |
| Installs per `ct` | ASC → Sources | Whether the website is worth writing for at all |
| Onboarding abandon by step | GA4 (app stream) | The one onboarding step to fix next |
| `paywall_view` → `trial_start` | GA4 (app stream) | Paywall placement and timing |
| `trial_start` → `purchase` | GA4, revenue truth in ASC | Whether 7 days is long enough to build the habit |

Rule from the app spec worth repeating here: **GA4 for conversion rates and cohorts, App Store
Connect for money.** GA4 `purchase` values are gross and pre-commission, so they will never
reconcile with ASC. Don't let the two argue.

## 6. Reading the data from the command line

For pulling GA4 numbers into a terminal (or handing them to Claude) rather than clicking through
reports, the pattern is a service account with Viewer access on the property plus the GA4 Data
API — the trinitysports repo already documents this end to end in `docs/analytics-reporting.md`,
and the same steps apply to this property. Worth doing once the weekly readout above stops being
a novelty and starts being a chore.

## 7. Turning it off

Set `ga4_measurement_id: ""` and push. The tag, the banner and the cookies all disappear on the
next build. No other file needs touching — which is the reason the ID lives in config rather than
pasted into the layout.
