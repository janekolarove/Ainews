from datetime import datetime, timezone
import os, re, textwrap
import feedparser
from bs4 import BeautifulSoup
from slugify import slugify

# === RSS ZDROJE ===
FEEDS = {
    "cs": [
        "https://www.root.cz/rss/clanky/",                # tech/IT
        "https://www.denikn.cz/tema/umela-inteligence/feed/",  # AI téma (pokud dostupné)
        "https://www.lupa.cz/rss/clanky/"                 # CZ tech business
    ],
    "en": [
        "https://feeds.feedburner.com/Techcrunch/artificial-intelligence",
        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "https://www.technologyreview.com/feed/ai/",
    ]
}

POSTS_DIR = "_posts"
os.makedirs(POSTS_DIR, exist_ok=True)

def clean_html(html):
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    # Vyhoď skripty/style a odkazy na share
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ").strip()
    # zkraceni whitespace
    return re.sub(r"\s+", " ", text)

def summarize(text, max_chars=800):
    """Velmi jednoduché shrnutí: první odstavec + 3–5 klíčových vět."""
    if not text:
        return ""
    text = text.strip()
    first = text.split(". ")
    # vezmi prvních ~6 vět
    chosen = ". ".join(first[:6]).strip()
    if len(chosen) > max_chars:
        chosen = chosen[:max_chars].rsplit(" ", 1)[0] + "…"
    return chosen

def make_md(title, date_dt, lang, link, summary, tags):
    fm = [
        "---",
        'layout: post',
        f'title: "{title.replace(\'"\', "\'")}"',
        f"date: {date_dt.strftime('%Y-%m-%d')}",
        f"lang: {lang}",
        f"tags: [{', '.join(tags)}]",
        "---",
        ""
    ]
    body = textwrap.dedent(f"""
    > Zdroj: [{link}]({link})

    {summary}

    **Takeaways**
    - Klíčové: {tags[0] if tags else 'ai'}
    - Odkaz na zdroj je uveden výše.
    """).strip()
    return "\n".join(fm) + "\n\n" + body + "\n"

def already_exists(filename):
    return os.path.exists(os.path.join(POSTS_DIR, filename))

def to_filename(date_dt, title):
    slug = slugify(title)[:80]
    return f"{date_dt.strftime('%Y-%m-%d')}-{slug}.md"

def process_feed(url, lang):
    feed = feedparser.parse(url)
    created = 0
    for e in feed.entries[:5]:  # zkusme max 5 položek na feed/run
        title = e.get("title", "").strip() or "AI News"
        link = e.get("link", "")
        # datum – pokud není, použij dnešek
        if "published_parsed" in e and e.published_parsed:
            dt = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
        else:
            dt = datetime.now(timezone.utc)
        date_local = dt.astimezone().date()

        # summary/content
        raw = e.get("summary", "") or e.get("content", [{}])[0].get("value", "")
        text = clean_html(raw)
        short = summarize(text)

        # tags
        tags = []
        if "tags" in e and e.tags:
            tags = [slugify(t["term"]).replace("-", "") for t in e.tags[:3] if "term" in t]
        if not tags:
            tags = ["ai", "news"]

        fname = to_filename(date_local, title)
        if already_exists(fname):
            continue

        md = make_md(title, date_local, lang, link, short, tags)
        with open(os.path.join(POSTS_DIR, fname), "w", encoding="utf-8") as f:
            f.write(md)
        created += 1
    return created

def main():
    total = 0
    for lang, urls in FEEDS.items():
        for u in urls:
            try:
                total += process_feed(u, lang)
            except Exception as ex:
                print(f"[WARN] {u}: {ex}")
                continue
    print(f"Generated {total} posts")

if __name__ == "__main__":
    main()
