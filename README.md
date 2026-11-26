# Innerspeak

A single-page website for Innerspeak: one-to-one chakra cleansing, blockage
removal and energy alignment sessions.

Plain HTML, CSS and JavaScript. No build step and no dependencies. Fonts are
self-hosted in `fonts/`, so the page makes no third-party requests.

## Before launch

1. **WhatsApp number.** Every "Book a session" link uses the placeholder
   `0000000000000`. Replace it everywhere in `index.html` with the real number
   in international format, digits only (no `+`, no spaces).
2. **Client words.** The three quotes in the "Kind words" section are sample
   wording and are labelled as such on the page. Replace them with real client
   words and remove the `words__note` paragraph, or delete the whole section.
3. **Photos.** See `images/README.md`.
4. **Prices.** Set in the "Choose your session" section of `index.html`.

## Structure

- `index.html` holds all content, in clearly commented sections.
- `css/style.css` holds the design. Colours and fonts are variables at the top.
- `js/main.js` runs the chakra explorer, the scroll reveal and the mobile menu.
  The page still works with JavaScript turned off.

## Design

- Monochrome palette to match the black-and-white still-life photography. The only
  colour on the page is the seven chakras in the explorer.
- Bodoni Moda for headings, Hanken Grotesk for text (both SIL Open Font
  License).
- Sharp corners everywhere; only the chakra marks are round.
- Light theme only, by choice.

## Publishing with GitHub Pages

Repository Settings, then Pages, then "Deploy from a branch". Choose the
branch and `/ (root)` and save. The repository must be public on a free plan.
GitHub then rebuilds the site after every push to that branch.
