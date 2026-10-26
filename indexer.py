"""
TF-IDF index and command-line search over the extracted games (extracted/games.tsv).

  python indexer.py build                          build index/ from extracted/games.tsv
  python indexer.py search cooperative dice        games containing ALL the terms (AND)
  python indexer.py search horror dice OR zombie   (horror AND dice) OR zombie
  python indexer.py search                         interactive mode

Matching games are ranked by the sum of the query terms' TF-IDF weights in the game,
two tf variants:
  classic  w = tf * idf
  double   w = (K + (1 - K) * tf / max_tf) * idf    (double normalization, K = 0.5)
tf = count of the term in the game, max_tf = count of the game's most frequent term,
idf = log(N / df), N = number of games, df = number of games containing the term.
"""
import argparse
import math
import os
import re
import unicodedata
from collections import Counter, defaultdict


# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GAMES_FILE = os.path.join(BASE_DIR, "extracted", "games.tsv")
INDEX_DIR = os.path.join(BASE_DIR, "index")
DOCUMENTS_FILE = os.path.join(INDEX_DIR, "documents.tsv")
TERMS_FILE = os.path.join(INDEX_DIR, "terms.tsv")

# Searchable columns of games.tsv. Artists and publishers are left out
INDEXED_COLUMNS = [
    "name", "summary", "designers", "categories", "mechanisms", "types",
    "description", "how_to_play",
]

DOUBLE_NORMALIZATION_K = 0.5
SCHEMES = {
    "classic": "Classic TF-IDF",
    "double": f"Double normalization (K = {DOUBLE_NORMALIZATION_K})",
}
TOP_RESULTS = 10

DOCUMENT_COLUMNS = ["doc_id", "slug", "name", "year", "url", "length", "max_tf"]

# "i" is not a stopword: "World War I"
STOPWORDS = set("""
a about above after again against all also am an and any are as at be because
been before being below between both but by can could did do does doing down
during each few for from further had has have having he her here hers herself
him himself his how if in into is it its itself just me more most my myself
no nor not now of off on once only or other our ours ourselves out over own
same she should so some such than that the their theirs them themselves then
there these they this those through to too under until up very was we were
what when where which while who whom why will with would you your yours
yourself yourselves s t
""".split())


# =============================================================================
# Tokenizer (the same for games and queries)
# =============================================================================

# "Children's Game, 2-4" -> ["Children", "s", "Game", "2", "4"]
# "Gùgōng"              -> ["Gùgōng"]
TOKEN = re.compile(r"[^\W_]+")

# "horror dice OR zombie" -> ["horror dice", "zombie"]
OR_OPERATOR = re.compile(r"\s+OR\s+")


def fold(text):
  """'Jožin z Bažin' -> 'jozin z bazin' (lowercase, no diacritics)."""
  decomposed = unicodedata.normalize("NFKD", text.casefold())
  return "".join(char for char in decomposed if not unicodedata.combining(char))


def stem(token):
  """'zombies' -> 'zombie', 'cards' -> 'card'; 'chess', 'bonus', 'axis' stay."""
  if len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is")):
    return token[:-1]
  return token


def tokenize(text):
  """'The Zombies AND Dice' -> ['zombie', 'dice']"""
  return [stem(token) for token in TOKEN.findall(fold(text)) if token not in STOPWORDS]


def parse_query(query):
  """'horror dice OR zombie' -> [['horror', 'dice'], ['zombie']]
  Terms inside a group are joined with AND, the groups with OR."""
  groups = [tokenize(part) for part in OR_OPERATOR.split(query)]
  return [group for group in groups if group]


# =============================================================================
# TF-IDF
# =============================================================================

def tf_weight(scheme, tf, max_tf):
  """classic: tf=3 -> 3;  double: tf=3, max_tf=6 -> 0.5 + 0.5 * 3/6 = 0.75"""
  if scheme == "classic":
    return tf
  return DOUBLE_NORMALIZATION_K + (1 - DOUBLE_NORMALIZATION_K) * tf / max_tf


def idf(df, num_documents):
  """df=10 of N=3659 games -> log(365.9) = 5.90; terms in no game -> 0"""
  return math.log(num_documents / df) if df else 0.0


# =============================================================================
# Building the index
# =============================================================================

def build_index():
  games = read_tsv(GAMES_FILE)
  documents = []
  postings = defaultdict(list)  # term -> [(doc_id, tf)]

  for doc_id, game in enumerate(games):
    counts = Counter(tokenize(" ".join(game[column] for column in INDEXED_COLUMNS)))
    for term, tf in counts.items():
      postings[term].append((doc_id, tf))
    documents.append({
        "doc_id": doc_id,
        "slug": game["slug"],
        "name": game["name"],
        "year": game["year"],
        "url": game["url"],
        "length": sum(counts.values()),
        "max_tf": max(counts.values(), default=1),
    })

  # terms.tsv row: "zombie  45  90:6|176:1|..." (doc_id:tf pairs)
  terms = [
      {"term": term, "df": len(docs),
       "postings": "|".join(f"{doc_id}:{tf}" for doc_id, tf in docs)}
      for term, docs in sorted(postings.items())
  ]

  os.makedirs(INDEX_DIR, exist_ok=True)
  write_tsv(DOCUMENTS_FILE, DOCUMENT_COLUMNS, documents)
  write_tsv(TERMS_FILE, ["term", "df", "postings"], terms)

  num_postings = sum(len(docs) for docs in postings.values())
  num_tokens = sum(doc["length"] for doc in documents)
  print(f"Indexed {len(documents)} games: {len(terms)} terms, {num_postings} postings, "
        f"{num_tokens / len(documents):.0f} terms per game on average")
  print(f"  {DOCUMENTS_FILE}\n  {TERMS_FILE}")


# =============================================================================
# Searching
# =============================================================================

class Index:
  """The index from index/; postings are parsed only for the query terms."""

  def __init__(self):
    self.documents = read_tsv(DOCUMENTS_FILE)
    for doc in self.documents:
      doc["max_tf"] = int(doc["max_tf"])

    # term -> "df<TAB>postings", split later
    with open(TERMS_FILE, encoding="utf-8") as f:
      next(f)
      self.terms = dict(line.rstrip("\n").split("\t", 1) for line in f)

  def df(self, term):
    entry = self.terms.get(term)
    return int(entry.split("\t", 1)[0]) if entry else 0

  def idf(self, term):
    return idf(self.df(term), len(self.documents))

  def postings(self, term):
    """'90:6|176:1' -> {90: 6, 176: 1}"""
    entry = self.terms.get(term)
    if not entry:
      return {}
    pairs = entry.split("\t", 1)[1].split("|")
    return {int(doc_id): int(tf) for doc_id, tf in (pair.split(":") for pair in pairs)}


def search(index, groups, scheme):
  """Games with all terms of at least one group, highest score first.
  score = sum of tf_weight * idf of the query terms in the game.
  Returns [(score, document)]."""
  terms = set(term for group in groups for term in group)
  postings = {term: index.postings(term) for term in terms}

  matches = set()
  for group in groups:
    matches |= set.intersection(*(set(postings[term]) for term in group))  # AND

  results = []
  for doc_id in matches:
    doc = index.documents[doc_id]
    score = sum(
        tf_weight(scheme, postings[term][doc_id], doc["max_tf"]) * index.idf(term)
        for term in terms if doc_id in postings[term])
    results.append((score, doc))

  results.sort(key=lambda result: (-result[0], result[1]["name"]))
  return results


def describe_query(index, groups):
  """[['horror', 'dice'], ['zombie']] -> '(horror [205] AND dice [881]) OR zombie [45]'"""
  parts = [" AND ".join(f"{term} [{index.df(term)}]" for term in group) for group in groups]
  if len(parts) > 1:
    parts = [f"({part})" if " AND " in part else part for part in parts]
  return " OR ".join(parts)


def run_query(index, query, schemes, top):
  groups = parse_query(query)
  if not groups:
    print("No searchable terms in the query (only stopwords?).")
    return

  rankings = {scheme: search(index, groups, scheme) for scheme in schemes}
  num_matches = len(next(iter(rankings.values())))
  print(f"\n{describe_query(index, groups)}  ->  {num_matches} games"
        f"   ([n] = games containing the term)")
  if not num_matches:
    return

  for scheme, results in rankings.items():
    print(f"\n{SCHEMES[scheme]}")
    for rank, (score, doc) in enumerate(results[:top], 1):
      year = f" ({doc['year']})" if doc["year"] else ""
      print(f"{rank:4}. {score:.4f}  {doc['name']}{year}  {doc['url']}")


def interactive(index, schemes, top):
  print("Terms are joined with AND, use OR between alternatives. "
        "Empty line or Ctrl+D quits.")
  while True:
    try:
      query = input("\nquery> ").strip()
    except (EOFError, KeyboardInterrupt):
      print()
      return
    if not query:
      return
    run_query(index, query, schemes, top)


# =============================================================================
# TSV files
# =============================================================================

def read_tsv(path):
  with open(path, encoding="utf-8") as f:
    header, *rows = [line.rstrip("\n").split("\t") for line in f]
  return [dict(zip(header, row)) for row in rows]


def write_tsv(path, columns, rows):
  with open(path, "w", encoding="utf-8") as f:
    f.write("\t".join(columns) + "\n")
    for row in rows:
      f.write("\t".join(str(row[column]) for column in columns) + "\n")


# =============================================================================
# Command line
# =============================================================================

def main():
  parser = argparse.ArgumentParser(description="TF-IDF search over board games.")
  commands = parser.add_subparsers(dest="command", required=True)
  commands.add_parser("build", help="build index/ from extracted/games.tsv")
  search_command = commands.add_parser(
      "search", help="search the index (without a query: interactive mode)")
  search_command.add_argument(
      "query", nargs="*", help="terms are joined with AND, OR separates alternatives")
  search_command.add_argument(
      "--scheme", choices=[*SCHEMES, "both"], default="both",
      help="tf-idf variant used for ranking (default: both)")
  search_command.add_argument(
      "--top", type=int, default=TOP_RESULTS, help="number of results to show")
  args = parser.parse_args()

  if args.command == "build":
    build_index()
    return

  if not os.path.exists(TERMS_FILE):
    raise SystemExit("Index not found - run: python indexer.py build")
  index = Index()
  schemes = list(SCHEMES) if args.scheme == "both" else [args.scheme]
  if args.query:
    run_query(index, " ".join(args.query), schemes, args.top)
  else:
    interactive(index, schemes, args.top)


if __name__ == "__main__":
  main()
