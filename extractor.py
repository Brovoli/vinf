"""
Extractor for the pages saved by the crawler (main.py).

Each saved page is matched to a layout by its URL and parsed with regexes:
  /<slug>                     game detail        -> extracted/games.tsv
  /boardgamedesigner/<slug>   designer listing   -> extracted/designers.tsv
  /boardgameartist/<slug>     artist listing     -> extracted/artists.tsv
  /boardgamepublisher/<slug>  publisher listing  -> extracted/publishers.tsv
  /category/<slug>            category listing   -> extracted/categories.tsv
  /mechanisms/<slug>          mechanism listing  -> extracted/mechanisms.tsv
  /subdomain/<slug>           type listing       -> extracted/types.tsv
  /ranking?page=N             ranking table      -> rank, rating, voters in games.tsv

Skipped: events, shops, users, search/popular lists and static pages.
Multiple values in one cell are separated by "|".
"""
import html
import os
import re


# =============================================================================
# Configuration
# =============================================================================

BASE_URL = "https://boardgamewikia.com"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVED_PAGES_DIR = os.path.join(BASE_DIR, "saved_pages")
CRAWLED_URLS_FILE = os.path.join(BASE_DIR, "links", "crawled_urls.tsv")
OUTPUT_DIR = os.path.join(BASE_DIR, "extracted")

LIST_SEPARATOR = "|"

# URL prefix -> output table and games.tsv column
ENTITY_TABLES = {
    "boardgamedesigner": "designers",
    "boardgameartist": "artists",
    "boardgamepublisher": "publishers",
    "category": "categories",
    "mechanisms": "mechanisms",
    "subdomain": "types",
}

EXPANSION_CATEGORY = "expansion-for-basegame"

GAME_COLUMNS = [
    "slug", "url", "name", "year", "summary",
    "min_players", "max_players", "min_playtime", "max_playtime", "min_age",
    "complexity", "rating", "num_voters", "rank", "bgg_id",
    "is_expansion", "base_game",
    "designers", "artists", "publishers", "categories", "mechanisms", "types",
    "related_games", "description", "how_to_play",
]
ENTITY_COLUMNS = ["slug", "url", "name", "num_games", "games"]


# =============================================================================
# Regexes (examples: matched text -> extracted groups, ".../" = BASE_URL)
# =============================================================================

ENTITY_KINDS = "|".join(ENTITY_TABLES)

# Page layout by URL

# .../ranking?page=2          -> match
# .../ranking?subdomain=1022  -> no match (per-type rankings are skipped)
RANKING_URL = re.compile(r"https://boardgamewikia\.com/ranking(?:\?page=\d+)?")

# .../boardgamedesigner/reiner-knizia?page=2  -> ("boardgamedesigner", "reiner-knizia")
# .../mechanisms/cooperative-game             -> ("mechanisms", "cooperative-game")
LISTING_URL = re.compile(
    rf"https://boardgamewikia\.com/({ENTITY_KINDS})/([^/?]+)(?:\?page=\d+)?")

# .../gloomhaven  -> "gloomhaven"
# .../about       -> "about" (rejected in extract_game, not a game page)
GAME_URL = re.compile(r"https://boardgamewikia\.com/([^/?]+)")

# Game page

# <div class="title_h1"> <div class="point"> ... View on BGG </a> ... <div class="title_right">
#   -> rating, <h1>, summary, info box, credits and BGG link
GAME_HEADER = re.compile(
    r'<div class="title_h1">(.*?)<div class="title_right">', re.S)

# <h1>Gloomhaven (2017)</h1>        -> "Gloomhaven (2017)"
# <h1>Designer: Reiner Knizia</h1>  -> "Designer: Reiner Knizia"
TITLE = re.compile(r"<h1>(.*?)</h1>", re.S)

# "Gloomhaven (2017)"   -> ("Gloomhaven", "2017")
# "Backgammon (-3000)"  -> ("Backgammon", "-3000")
NAME_YEAR = re.compile(r"(.*?)\s*\((-?\d+)\)")

# <div class="point"> <span>8.5</span>  -> "8.5"
# <div class="point"> <span>--</span>   -> no match
RATING = re.compile(r'<div class="point">\s*<span>([\d.]+)</span>')

# <p class="desc">Travel to dark corners of the world, ...</p>
#   -> "Travel to dark corners of the world, ..."
SUMMARY = re.compile(r'<p class="desc">(.*?)</p>', re.S)

# <div class="box_info"> <div class="item"> <span>Rank: 4</span> ... <div class="content_p_ab">
#   -> after clean(): "Rank: 4 1-4 Players 60-120 Min Age: 14+ Complexity: 3.92/5"
INFO_BOX = re.compile(r'<div class="box_info">(.*?)<div class="content_p_ab">', re.S)

# "Rank: 4"  -> "4"
RANK = re.compile(r"Rank: ([\d,]+)")

# "1-4 Players"  -> ("1", "4")
# "2 Players"    -> ("2", None)
PLAYERS = re.compile(r"(\d+)(?:-(\d+))? Players?")

# "60-120 Min"  -> ("60", "120")
# "30 Min"      -> ("30", None)
PLAYTIME = re.compile(r"(\d+)(?:-(\d+))? Min")

# "Age: 14+"  -> "14"
# "Age: --"   -> no match
AGE = re.compile(r"Age: (\d+)\+")

# "Complexity: 3.92/5"  -> "3.92"
COMPLEXITY = re.compile(r"Complexity: ([\d.]+)/5")

# <div class="content_p_ab"> <p class="designer-wrapper">Designer: ... <div class="func_box">
#   -> the Designer, Artist and Publisher paragraphs
CREDITS = re.compile(r'<div class="content_p_ab">(.*?)<div class="func_box">', re.S)

# href="https://boardgamegeek.com/boardgame/174430"  -> "174430"
BGG_ID = re.compile(r'href="https://boardgamegeek\.com/boardgame/(\d+)"')

# <h4>Classification</h4> ... <h5 class="tt_sub">Mechanism</h5> ... <h2>Related Games<
#   -> the Category, Mechanism and Type lists
CLASSIFICATION = re.compile(r"<h4>Classification</h4>(.*?)>Related Games<", re.S)

# href="https://boardgamewikia.com/boardgamedesigner/isaac-childres/">Isaac Childres</a>
#   -> ("boardgamedesigner", "isaac-childres", "Isaac Childres")
# href="https://boardgamewikia.com/mechanisms/action-queue/"><span>Action Queue</span></a>
#   -> ("mechanisms", "action-queue", "<span>Action Queue</span>")
ENTITY_LINK = re.compile(
    rf'href="https://boardgamewikia\.com/({ENTITY_KINDS})/([^/"?]+)/?"[^>]*>(.*?)</a>',
    re.S)

# "Suggested Games" after it are random picks, so they are not used
# >Related Games</h2> ... data-slug="gloomhaven-jaws-of-the-lion" ... <h2>Suggested Games<
#   -> the Related Games cards
RELATED_GAMES = re.compile(r">Related Games<(.*?)>Suggested Games<", re.S)

# panel-contnet="overview"> <div class="content_p"> <h2>About the game</h2> <p>Gloomhaven is ...
#   ... <div class="tab-content" panel-contnet="how_to_play"  -> the Overview tab HTML
OVERVIEW = re.compile(
    r'panel-contnet="overview">(.*?)<div class="tab-content" panel-contnet="how_to_play"',
    re.S)

# <div class="more_content" style="display: none;"><h2>How To Play Gloomhaven</h2>
#   -> split point between description and how_to_play
MORE_CONTENT = re.compile(r'<div class="more_content"[^>]*>')

# <p class="show_hide_howtoplay read_more" data-more="Read More" ...>Read More</p>  -> removed
READ_MORE = re.compile(r'<p class="show_hide_howtoplay.*?</p>', re.S)

# Listing page (designer, category, ...)

# class="wrapper_content_related_multi page " > <div class="child"> ... data-slug="ra" ... </main>
#   -> the grid of game cards
LISTING_GRID = re.compile(
    r'class="wrapper_content_related_multi page.*?</main>', re.S)

# "Designer: Reiner Knizia"  -> "Reiner Knizia"
# "Turn Order: Progressive"  -> unchanged (a mechanism name)
LISTING_PREFIX = re.compile(r"^(?:Designer|Artist|Publisher): ")

# data-slug="ra"                       -> "ra"
# data-slug="the-quest-for-el-dorado"  -> "the-quest-for-el-dorado"
CARD_SLUG = re.compile(r'data-slug="([^"]+)"')

# Ranking page: rank ("-" = unranked), game, rating, number of voters
# <span>21</span> ... .../great-western-trail/ ... <span>8.141</span> ... <span>44,222</span>
#   -> ("21", "great-western-trail", "8.141", "44,222")
# <span>-</span> ... .../1st-ceo/ ... <span>8.429</span> ... <span>17</span>
#   -> ("-", "1st-ceo", "8.429", "17")
RANKING_ROW = re.compile(
    r'<div class="item rank[^"]*">\s*<span>(.*?)</span>'
    r'.*?href="https://boardgamewikia\.com/([^/"]+)/?"'
    r'.*?<div class="item">\s*<span>(.*?)</span>\s*</div>'
    r'\s*<div class="item">\s*<span>(.*?)</span>',
    re.S)

# "Kemet: Blood and Sand – Onyx"  -> "Kemet" (first part of the split)
# "Five Tribes: Dhenim"           -> "Five Tribes"
NAME_PREFIX = re.compile(r":| – ")

# Inline tags are dropped, other tags become spaces
# <em><strong>Carcassonne</strong></em> is  -> "Carcassonne is"
INLINE_TAG = re.compile(r"</?(?:a|abbr|b|em|i|span|strong|sub|sup|u)\b[^>]*>", re.I)
# <div class="content_p">, <p>, </li>  -> " "
TAG = re.compile(r"<[^>]+>")
# "\n                    "  -> " "
WHITESPACE = re.compile(r"\s+")


# =============================================================================
# Helpers
# =============================================================================

def clean(fragment):
  """HTML fragment -> one line of plain text."""
  text = TAG.sub(" ", INLINE_TAG.sub("", fragment))
  return WHITESPACE.sub(" ", html.unescape(text)).strip()


def first(pattern, text):
  """First group of the first match, or ""."""
  match = pattern.search(text)
  return match.group(1) if match else ""


def min_max(pattern, text):
  """'1-4 Players' -> ('1', '4'), '2 Players' -> ('2', '2')."""
  match = pattern.search(text)
  if not match:
    return "", ""
  return match.group(1), match.group(2) or match.group(1)


def number(text):
  """'1,293' -> '1293', '-' -> ''."""
  text = text.replace(",", "").strip()
  return text if re.fullmatch(r"\d+(?:\.\d+)?", text) else ""


def unique(values):
  return list(dict.fromkeys(value for value in values if value))


# =============================================================================
# Page extractors
# =============================================================================

def extract_game(page, slug):
  """Game page -> (games.tsv row, entity links [(kind, slug, name)])."""
  header = first(GAME_HEADER, page)
  if 'class="container game-detail"' not in page or not header:
    return None

  title = clean(first(TITLE, header))
  name_year = NAME_YEAR.fullmatch(title)
  name, year = name_year.groups() if name_year else (title, "")

  info = clean(first(INFO_BOX, header))
  min_players, max_players = min_max(PLAYERS, info)
  min_playtime, max_playtime = min_max(PLAYTIME, info)

  # Credits are in the header, categories/mechanisms/types in the sidebar
  links = [
      (kind, entity_slug, clean(entity_name))
      for kind, entity_slug, entity_name in ENTITY_LINK.findall(
          first(CREDITS, header) + first(CLASSIFICATION, page))
  ]

  # Overview tab = description + hidden "How to play" article
  overview = READ_MORE.sub("", first(OVERVIEW, page))
  description, how_to_play = (MORE_CONTENT.split(overview, maxsplit=1) + [""])[:2]

  row = {
      "slug": slug,
      "url": f"{BASE_URL}/{slug}",
      "name": name,
      "year": year,
      "summary": clean(first(SUMMARY, header)),
      "min_players": min_players,
      "max_players": max_players,
      "min_playtime": min_playtime,
      "max_playtime": max_playtime,
      "min_age": first(AGE, info),
      "complexity": first(COMPLEXITY, info),
      "rating": first(RATING, header),
      "num_voters": "",
      "rank": number(first(RANK, info)),
      "bgg_id": first(BGG_ID, header),
      "is_expansion": int(any(kind == "category" and entity_slug == EXPANSION_CATEGORY
                              for kind, entity_slug, _ in links)),
      "base_game": "",
      "related_games": [s for s in unique(CARD_SLUG.findall(first(RELATED_GAMES, page)))
                        if s != slug],
      "description": clean(description),
      "how_to_play": clean(how_to_play),
  }
  for kind, column in ENTITY_TABLES.items():
    row[column] = unique(entity_name for k, _, entity_name in links if k == kind)
  return row, links


def extract_listing(page):
  """Listing page (designer, category, ...) -> (name, game slugs)."""
  grid = LISTING_GRID.search(page)
  if 'class="title_page title_browse_main"' not in page or not grid:
    return None
  name = LISTING_PREFIX.sub("", clean(first(TITLE, page)))
  return name, CARD_SLUG.findall(grid.group(0))


def extract_ranking(page):
  """Ranking page -> {slug: (rank, rating, num_voters)}."""
  return {
      slug: (number(rank), number(rating), number(voters))
      for rank, slug, rating, voters in RANKING_ROW.findall(page)
  }


# =============================================================================
# Combining pages
# =============================================================================

def add_ranking(games, ranking):
  """Rank, rating and voters from the ranking pages (one consistent snapshot)."""
  for slug, (rank, rating, voters) in ranking.items():
    game = games.get(slug)
    if game:
      game["rank"] = rank
      game["num_voters"] = voters
      game["rating"] = rating if voters not in ("", "0") else ""


def add_base_games(games):
  """Expansions don't link their base game, so guess it from games whose slug
  prefixes the expansion slug or whose name starts like the expansion name
  ("Five Tribes: Dhenim" -> "Five Tribes: The Djinns of Naqala")."""
  base_games = [game for game in games.values() if not game["is_expansion"]]
  for expansion in games.values():
    if not expansion["is_expansion"]:
      continue
    prefix = NAME_PREFIX.split(expansion["name"])[0].strip()
    candidates = [
        game for game in base_games
        if expansion["slug"].startswith(game["slug"] + "-")
        or game["name"] == prefix or game["name"].startswith(prefix + ":")
    ]
    if candidates:
      best = max(candidates, key=lambda game: base_game_score(expansion, game))
      expansion["base_game"] = best["slug"]


def base_game_score(expansion, game):
  """Prefer a shared designer, then a longer slug match, then more voters."""
  shares_designer = bool(set(game["designers"]) & set(expansion["designers"]))
  slug_match = len(game["slug"]) if expansion["slug"].startswith(game["slug"] + "-") else 0
  return shares_designer, slug_match, int(game["num_voters"] or 0)


def entity_rows(kind, listings, entity_names):
  """Rows for one entity table; names from game pages, the h1 as fallback."""
  rows = []
  for (listing_kind, slug), (h1_name, game_slugs) in sorted(listings.items()):
    if listing_kind != kind or not game_slugs:
      continue
    rows.append({
        "slug": slug,
        "url": f"{BASE_URL}/{kind}/{slug}",
        "name": entity_names.get((kind, slug), h1_name),
        "num_games": len(game_slugs),
        "games": list(game_slugs),
    })
  return rows


# =============================================================================
# Input / output
# =============================================================================

def read_crawled_pages():
  """(url, file path) of every page saved with HTTP 200."""
  with open(CRAWLED_URLS_FILE, encoding="utf-8") as f:
    rows = [line.rstrip("\n").split("\t") for line in f][1:]
  return [
      (url, os.path.join(SAVED_PAGES_DIR, filename))
      for url, status, filename, _ in rows
      if status == "200" and filename
  ]


def write_tsv(name, columns, rows):
  path = os.path.join(OUTPUT_DIR, name)
  with open(path, "w", encoding="utf-8") as f:
    f.write("\t".join(columns) + "\n")
    for row in rows:
      cells = []
      for column in columns:
        value = row[column]
        if isinstance(value, list):
          value = LIST_SEPARATOR.join(value)
        # "line one\nline two" -> "line one line two" (a cell can't hold tabs/newlines)
        cells.append(re.sub(r"[\t\r\n]+", " ", str(value)))
      f.write("\t".join(cells) + "\n")
  print(f"  {path}: {len(rows)} rows")


# =============================================================================
# Main
# =============================================================================

def main():
  os.makedirs(OUTPUT_DIR, exist_ok=True)

  games = {}          # slug -> row
  listings = {}       # (kind, slug) -> (h1 name, {game slug: None})
  ranking = {}        # slug -> (rank, rating, voters)
  entity_names = {}   # (kind, slug) -> name used on game pages
  counts = {"game": 0, "listing": 0, "ranking": 0, "skipped": 0}

  pages = read_crawled_pages()
  for index, (url, path) in enumerate(pages, 1):
    if index % 1000 == 0:
      print(f"{index}/{len(pages)} pages")

    ranking_match = RANKING_URL.fullmatch(url)
    listing_match = LISTING_URL.fullmatch(url)
    game_match = GAME_URL.fullmatch(url)
    if not (ranking_match or listing_match or game_match):
      counts["skipped"] += 1
      continue

    with open(path, encoding="utf-8", errors="replace") as f:
      page = f.read()

    if ranking_match:
      ranking.update(extract_ranking(page))
      counts["ranking"] += 1

    elif listing_match:
      result = extract_listing(page)
      if result is None:
        counts["skipped"] += 1
        continue
      # One entity is spread over ?page=N pages - merge their games
      name, game_slugs = result
      _, entity_games = listings.setdefault(listing_match.groups(), (name, {}))
      entity_games.update(dict.fromkeys(game_slugs))
      counts["listing"] += 1

    else:
      result = extract_game(page, game_match.group(1))
      if result is None:  # /about, /events, /search, ...
        counts["skipped"] += 1
        continue
      row, links = result
      games[row["slug"]] = row
      for kind, slug, name in links:
        entity_names[kind, slug] = name
      counts["game"] += 1

  add_ranking(games, ranking)
  add_base_games(games)

  print(f"\nPages: {len(pages)} | " + " | ".join(f"{k} {v}" for k, v in counts.items()))
  write_tsv("games.tsv", GAME_COLUMNS, [games[slug] for slug in sorted(games)])
  for kind, table in ENTITY_TABLES.items():
    write_tsv(f"{table}.tsv", ENTITY_COLUMNS, entity_rows(kind, listings, entity_names))


if __name__ == "__main__":
  main()
