"""
Builds the online reader in /read from the manuscript in /content.

Usage:
    pip install markdown
    python build.py

Edit the book in content/*.md (files are read in name order), then run this
again and commit the updated /read folder. Each "## " heading starts a new
chapter page. "### " headings become sections listed in the chapter sidebar.
Formulas go in ```latex blocks and are drawn by KaTeX in the browser.
"""

import html
import re
from pathlib import Path

import markdown

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
OUT = ROOT / "read"

BOOK_TITLE = "Dalton Dean's Guide to Rebuilding Civilization"
KATEX = "https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9"

# One line per chapter for the contents page, keyed by slug.
SUMMARIES = {
    "introduction": "How the book is ordered, how to read it, and a word on safety.",
    "water": "Finding, filtering, boiling and storing water you can trust.",
    "fire": "Combustion, fire without matches, chimneys, rocket stoves and charcoal.",
    "shelter": "Heat loss, beams and triangles, frost, timber, earth and lime.",
    "food": "Nutrition, deadly lookalikes, nitrogen, rotation, seed saving and preserving.",
    "medicine": "Bleeding, wounds, burns, fractures, rehydration, blood types and childbirth.",
    "tools": "Stone, bronze, the bloomery, forging, heat treatment and sharpening.",
    "power": "Simple machines, water wheels, wind, animal power and flywheels.",
    "machines": "Gears, bearings, true flats, the lathe, steam and electricity.",
    "knowledge": "Paper, ink, printing, measurement, numbers and the scientific method.",
}


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def split_chapters(source):
    chapters = []
    for block in re.split(r"(?m)^## ", source):
        block = block.strip()
        if not block:
            continue
        heading, _, body = block.partition("\n")
        match = re.match(r"Chapter (\d+):\s*(.+)", heading.strip())
        if match:
            number, name = int(match.group(1)), match.group(2).strip()
        else:
            number, name = None, heading.strip()
        chapters.append({"number": number, "name": name, "slug": slugify(name), "body": body.strip()})
    return chapters


def render_body(body):
    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc"],
                           extension_configs={"toc": {"slugify": lambda v, s: slugify(v)}})
    out = md.convert(body)
    # Formulas: KaTeX renders these in the browser.
    out = re.sub(r'<pre><code class="language-latex">(.*?)</code></pre>',
                 lambda m: f'<div class="math" role="math">{m.group(1).strip()}</div>', out, flags=re.S)
    # Tables scroll sideways on small screens instead of squashing.
    out = out.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    # The chapter's opening paragraph is set as a lede.
    out = out.replace("<p>", '<p class="lede">', 1)
    sections = [(t["id"], t["name"]) for t in md.toc_tokens]
    words = len(re.sub(r"<[^>]+>", " ", out).split())
    return out, sections, max(1, round(words / 230))


def label(ch):
    return f"Chapter {ch['number']}" if ch["number"] else "Before you begin"


def head(title, description, extra=""):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ccircle cx='32' cy='32' r='30' fill='%232F5D52'/%3E%3Cpath d='M32 46V26M32 32c-8 0-12-6-12-12 8 0 12 5 12 12zm0-4c0-7 4-11 12-11 0 7-5 11-12 11z' fill='none' stroke='%23D6A64A' stroke-width='3' stroke-linecap='round'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IM+Fell+DW+Pica:ital@0;1&family=Literata:ital,opsz,wght@0,7..72,400;0,7..72,600;1,7..72,400&display=swap" rel="stylesheet">
{extra}<link rel="stylesheet" href="reader.css">
</head>
<body>
<a class="skip" href="#main">Skip to the text</a>
<header class="site-head">
  <div class="wrap">
    <a class="mark" href="../index.html">Dalton Dean</a>
    <nav aria-label="Main">
      <a href="index.html">Contents</a>
      <a class="nav-order" href="../index.html#order">Order the book</a>
    </nav>
  </div>
</header>
"""


FOOT = """<footer class="site-foot">
  <div class="wrap">
    <span>&copy; <span id="year">2026</span> Dalton Dean</span>
    <a href="../index.html">Back to the book's home page</a>
  </div>
</footer>
<script>
  document.getElementById('year').textContent = new Date().getFullYear();
  // Sidebar lists start open on wide screens and folded on phones.
  if (window.matchMedia('(min-width: 901px)').matches) {
    document.querySelectorAll('.side-box').forEach(function (d) { d.open = true; });
  }
</script>
"""

MATH_SCRIPT = f"""<script defer src="{KATEX}/katex.min.js"></script>
<script>
  window.addEventListener('DOMContentLoaded', function () {{
    var draw = function () {{
      document.querySelectorAll('.math').forEach(function (el) {{
        katex.render(el.textContent, el, {{ displayMode: true, throwOnError: false }});
      }});
    }};
    if (window.katex) draw(); else document.querySelector('script[src*="katex"]').addEventListener('load', draw);
  }});
</script>
"""


def chapter_page(ch, chapters, i):
    body, sections, minutes = ch["html"], ch["sections"], ch["minutes"]
    prev_ch = chapters[i - 1] if i > 0 else None
    next_ch = chapters[i + 1] if i < len(chapters) - 1 else None

    current = ' aria-current="page"'
    book_nav = "\n".join(
        f'<li><a href="{c["slug"]}.html"{current if c is ch else ""}>'
        f'<span class="n">{c["number"] or ""}</span>{html.escape(c["name"])}</a></li>'
        for c in chapters)
    section_nav = "\n".join(f'<li><a href="#{sid}">{html.escape(name)}</a></li>' for sid, name in sections)

    pager = '<nav class="pager" aria-label="Chapters">'
    if prev_ch:
        pager += f'<a class="prev" href="{prev_ch["slug"]}.html"><span>Previous</span>{html.escape(prev_ch["name"])}</a>'
    else:
        pager += "<span></span>"
    if next_ch:
        pager += f'<a class="next" href="{next_ch["slug"]}.html"><span>Next, {label(next_ch).lower()}</span>{html.escape(next_ch["name"])}</a>'
    else:
        pager += '<a class="next" href="../index.html#order"><span>You have reached the end</span>Order the book</a>'
    pager += "</nav>"

    has_math = 'class="math"' in body
    extra = f'<link rel="stylesheet" href="{KATEX}/katex.min.css">\n' if has_math else ""
    title = f"{ch['name']} | {BOOK_TITLE}"

    return head(title, SUMMARIES.get(ch["slug"], ""), extra) + f"""
<main id="main">
  <div class="chapter-head">
    <div class="wrap">
      <p class="byline">{label(ch)}</p>
      <h1>{html.escape(ch["name"])}</h1>
      <p class="meta">About {minutes} minutes to read</p>
    </div>
  </div>

  <div class="wrap layout">
    <aside class="side" aria-label="Book contents">
      <details class="side-box">
        <summary>Chapters</summary>
        <ol class="book-nav">{book_nav}</ol>
      </details>
      {f'<details class="side-box sections"><summary>In this chapter</summary><ul>{section_nav}</ul></details>' if sections else ''}
    </aside>

    <article class="chapter">
{body}
      {pager}
    </article>
  </div>
</main>
""" + FOOT + (MATH_SCRIPT if has_math else "") + "</body>\n</html>\n"


def contents_page(chapters):
    total = sum(c["minutes"] for c in chapters)
    items = "\n".join(f"""      <li>
        <span class="n">{c["number"] or ""}</span>
        <div>
          <h2><a href="{c["slug"]}.html">{html.escape(c["name"])}</a></h2>
          <p>{html.escape(SUMMARIES.get(c["slug"], ""))}</p>
        </div>
        <span class="mins">{c["minutes"]} min</span>
      </li>""" for c in chapters)
    return head(f"Read the book | {BOOK_TITLE}",
                "Read Dalton Dean's Guide to Rebuilding Civilization online, chapter by chapter.") + f"""
<main id="main">
  <div class="chapter-head">
    <div class="wrap">
      <p class="byline">Dalton Dean's Guide to Rebuilding Civilization</p>
      <h1>Read the book</h1>
      <p class="meta">Nine chapters and an introduction, about {total} minutes of reading in all</p>
    </div>
  </div>
  <div class="wrap">
    <ol class="contents">
{items}
    </ol>
  </div>
</main>
""" + FOOT + "</body>\n</html>\n"


def main():
    source = "\n\n".join(p.read_text(encoding="utf-8") for p in sorted(CONTENT.glob("*.md")))
    chapters = split_chapters(source)
    for ch in chapters:
        ch["html"], ch["sections"], ch["minutes"] = render_body(ch["body"])
    OUT.mkdir(exist_ok=True)
    for i, ch in enumerate(chapters):
        (OUT / f"{ch['slug']}.html").write_text(chapter_page(ch, chapters, i), encoding="utf-8")
    (OUT / "index.html").write_text(contents_page(chapters), encoding="utf-8")
    print(f"Built {len(chapters)} chapter pages into {OUT}")
    for ch in chapters:
        print(f"  {ch['slug']}.html  {ch['minutes']} min  {len(ch['sections'])} sections")


if __name__ == "__main__":
    main()
