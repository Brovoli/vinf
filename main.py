"""
Crawler for boardgamewikia.com

How it works
------------
1. robots.txt is downloaded and every URL is checked against it.
2. The queue is seeded with START_URLS and all pages listed in the sitemap.
3. URLs are taken from the queue one by one:
     - the page is saved to saved_pages/
     - links are extracted from it and the ones not yet in all_urls are queued
4. Progress is kept in two TSV files in links/:
     - all_urls.tsv      every URL we know about (crawled + waiting)
     - crawled_urls.tsv  URLs that were already processed
   The queue is simply "all_urls minus crawled_urls", so when the crawler is
   interrupted (Ctrl+C, crash, ...) the next run continues where it stopped.

Only the standard library, requests and re are used - no HTML/XML parsing
libraries and no SQL database (see nepovolene_technologie.md).
"""
import hashlib
import html
import os
import re
import time
from collections import deque
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests


# =============================================================================
# Configuration
# =============================================================================

BASE_URL = "https://boardgamewikia.com"
ALLOWED_DOMAIN = "boardgamewikia.com"

START_URLS = [BASE_URL + "/"]
SITEMAP_URL = BASE_URL + "/sitemap/index.xml"  # None = don't use the sitemap
ROBOTS_URL = BASE_URL + "/robots.txt"

# bot identification
HEADERS = {
    "User-Agent": "VinfProjectBot/1.0 (Contact: xkemenya@stuba.sk)",
}

CRAWL_DELAY = 1  # Seconds to wait between requests
REQUEST_TIMEOUT = 30  # Seconds
MAX_RETRIES = 3  # Attempts per URL on network errors / temporary HTTP errors
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_PAGES_PER_RUN = None  # e.g. 20 for a quick test, None = no limit

# Links to files like these are never crawled
SKIPPED_EXTENSIONS = (
    ".css", ".js", ".json", ".xml", ".txt",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".avif",
    ".pdf", ".zip", ".mp3", ".mp4", ".webm",
    ".woff", ".woff2", ".ttf", ".eot",
)

# URL paths matching any of these regexes are not crawled
# (on top of what robots.txt disallows)
EXCLUDED_PATH_PATTERNS = [
    re.compile(r"^/vi(/|$)"),  # Vietnamese copy of the site (duplicate content)
]

# Output files (relative to this script, not to the current directory)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVED_PAGES_DIR = os.path.join(BASE_DIR, "saved_pages")
LINKS_DIR = os.path.join(BASE_DIR, "links")
ALL_URLS_FILE = os.path.join(LINKS_DIR, "all_urls.tsv")
CRAWLED_URLS_FILE = os.path.join(LINKS_DIR, "crawled_urls.tsv")

ALL_URLS_HEADER = ["url"]
CRAWLED_URLS_HEADER = ["url", "status", "file", "crawled_at"]

MAX_FILENAME_LENGTH = 200


# =============================================================================
# URL helpers
# =============================================================================

def normalize_url(href, base_url):
  """Turn an href into a canonical absolute URL.

  - resolves relative links against base_url
  - decodes HTML entities (&amp; -> &)
  - drops the #fragment
  - lowercases the domain
  - removes the trailing slash (/ark-nova/ and /ark-nova etc.)

  Returns None for links that are not web pages (mailto:, javascript:, #...).
  """
  href = html.unescape(href).strip()
  href = re.sub(r"[\t\r\n]", "", href).replace(" ", "%20")
  if not href or href.startswith("#"):
    return None

  parts = urlsplit(urljoin(base_url, href))
  if parts.scheme not in ("http", "https"):
    return None

  path = parts.path.rstrip("/") or "/"
  return urlunsplit((parts.scheme, parts.netloc.lower(), path, parts.query, ""))


def is_crawlable(url, robots):
  """Decide whether a normalized URL should be crawled."""
  parts = urlsplit(url)

  if parts.netloc != ALLOWED_DOMAIN:
    return False
  if parts.path.lower().endswith(SKIPPED_EXTENSIONS):
    return False
  if any(pattern.search(parts.path) for pattern in EXCLUDED_PATH_PATTERNS):
    return False

  # URLs are stored without the trailing slash, but robots.txt rules often
  # end with one ("Disallow: /blog/"), so both variants have to be allowed.
  with_slash = urlunsplit(parts._replace(path=parts.path.rstrip("/") + "/"))
  return robots.is_allowed(url) and robots.is_allowed(with_slash)


def url_to_filename(url):
  """Convert a URL into a safe local file name, e.g.
  https://boardgamewikia.com/ark-nova -> boardgamewikia.com_ark-nova.html
  """
  name = re.sub(r"^https?://", "", url)
  name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
  if len(name) > MAX_FILENAME_LENGTH:
    # Very long URL: shorten it and add a hash so the name stays unique
    url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:10]
    name = name[:MAX_FILENAME_LENGTH] + "_" + url_hash
  return name + ".html"


# =============================================================================
# robots.txt
# =============================================================================

class RobotsRules:
  """Minimal robots.txt parser.

  Supports Allow/Disallow, the * and $ wildcards and the "longest matching
  rule wins" logic. Uses the group for our bot name if there is one,
  otherwise the "User-agent: *" group.
  """

  def __init__(self, robots_txt, user_agent):
    groups = self._parse_groups(robots_txt)
    bot_name = user_agent.split("/")[0].lower()  # "vinfprojectbot"
    rules = groups[bot_name] if bot_name in groups else groups.get("*", [])
    # (is_allow, pattern length, compiled pattern)
    self.rules = [
        (is_allow, len(pattern), self._pattern_to_regex(pattern))
        for is_allow, pattern in rules
    ]

  @staticmethod
  def _parse_groups(robots_txt):
    """Return {user_agent: [(is_allow, pattern), ...]}."""
    groups = {}
    current_agents = []
    previous_line_was_agent = False

    for line in robots_txt.splitlines():
      line = line.split("#", 1)[0].strip()
      if ":" not in line:
        continue
      key, value = (part.strip() for part in line.split(":", 1))
      key = key.lower()

      if key == "user-agent":
        if not previous_line_was_agent:
          current_agents = []  # A new group starts
        current_agents.append(value.lower())
        groups.setdefault(value.lower(), [])
        previous_line_was_agent = True
        continue

      previous_line_was_agent = False
      if key in ("allow", "disallow") and value:
        for agent in current_agents:
          groups[agent].append((key == "allow", value))

    return groups

  @staticmethod
  def _pattern_to_regex(pattern):
    """'/shops/*/follow-status' -> regex; a trailing '$' anchors the end."""
    anchored = pattern.endswith("$")
    if anchored:
      pattern = pattern[:-1]
    regex = re.escape(pattern).replace(r"\*", ".*")
    return re.compile(regex + ("$" if anchored else ""))

  def is_allowed(self, url):
    parts = urlsplit(url)
    path = parts.path or "/"
    if parts.query:
      path += "?" + parts.query

    allowed, longest_match = True, -1
    for is_allow, length, regex in self.rules:
      if not regex.match(path):
        continue
      if length > longest_match or (length == longest_match and is_allow):
        allowed, longest_match = is_allow, length
    return allowed


def load_robots(session):
  """Download robots.txt and return the rules that apply to our crawler."""
  response = fetch(session, ROBOTS_URL)
  time.sleep(CRAWL_DELAY)

  if response is not None and response.status_code == 200:
    return RobotsRules(response_text(response), HEADERS["User-Agent"])
  if response is not None and 400 <= response.status_code < 500:
    print("robots.txt does not exist - everything is allowed.")
    return RobotsRules("", HEADERS["User-Agent"])
  raise SystemExit("Could not download robots.txt - stopping to be safe.")


# =============================================================================
# HTTP
# =============================================================================

def fetch(session, url):
  """Download a URL, retrying on network errors and temporary HTTP errors.

  Returns the Response (any status code), or None if all attempts failed.
  """
  for attempt in range(1, MAX_RETRIES + 1):
    try:
      response = session.get(url, timeout=REQUEST_TIMEOUT)
      if response.status_code not in RETRY_STATUS_CODES:
        return response
      print(f"  -> HTTP {response.status_code} (attempt {attempt}/{MAX_RETRIES})")
    except requests.exceptions.RequestException as e:
      print(f"  -> Error: {e} (attempt {attempt}/{MAX_RETRIES})")

    if attempt < MAX_RETRIES:
      time.sleep(CRAWL_DELAY * 5 * attempt)
  return None


def response_text(response):
  """Return the decoded response body.

  When the server sends no charset (robots.txt and sitemaps on this site),
  requests falls back to ISO-8859-1, which breaks UTF-8 text.
  """
  if "charset" not in response.headers.get("Content-Type", "").lower():
    response.encoding = "utf-8"
  return response.text


# =============================================================================
# Sitemap & link extraction
# =============================================================================

# <loc>https://...</loc> in sitemap XML
SITEMAP_LOC_PATTERN = re.compile(r"<loc>\s*(.*?)\s*</loc>", re.DOTALL)

# <a ... href="..."> or <a ... href='...'>
LINK_PATTERN = re.compile(
    r"""<a\b[^>]*?\shref\s*=\s*(?:"([^"]*)"|'([^']*)')""",
    re.IGNORECASE,
)

# <script>...</script> and <!-- ... --> may contain <a href> templates
# (e.g. href="${linkHref}") that are not real links
SCRIPT_OR_COMMENT_PATTERN = re.compile(
    r"<script\b.*?</script>|<!--.*?-->",
    re.IGNORECASE | re.DOTALL,
)


def get_sitemap_urls(session, sitemap_url):
  """Return all page URLs listed in a sitemap.

  A sitemap index (a list of other sitemaps) is followed recursively.
  """
  print(f"Reading sitemap: {sitemap_url}")
  response = fetch(session, sitemap_url)
  time.sleep(CRAWL_DELAY)
  if response is None or response.status_code != 200:
    print("  -> Could not download the sitemap, skipping it.")
    return []

  xml = response_text(response)
  locations = [html.unescape(loc) for loc in SITEMAP_LOC_PATTERN.findall(xml)]

  if "<sitemapindex" not in xml:
    return locations

  urls = []
  for child_sitemap_url in locations:
    urls.extend(get_sitemap_urls(session, child_sitemap_url))
  return urls


def extract_links(page_html, page_url):
  """Return the normalized URLs of all <a href> links on the page."""
  page_html = SCRIPT_OR_COMMENT_PATTERN.sub("", page_html)
  links = []
  for double_quoted, single_quoted in LINK_PATTERN.findall(page_html):
    url = normalize_url(double_quoted or single_quoted, page_url)
    if url:
      links.append(url)
  return links


# =============================================================================
# Storage (TSV files + saved pages)
# =============================================================================

def create_tsv_if_missing(path, header):
  if not os.path.exists(path):
    append_tsv_rows(path, [header])


def append_tsv_rows(path, rows):
  with open(path, "a", encoding="utf-8") as f:
    for row in rows:
      f.write("\t".join(str(value) for value in row) + "\n")


def read_tsv_first_column(path):
  """Return the first column of a TSV file (without the header row)."""
  with open(path, encoding="utf-8") as f:
    rows = f.read().splitlines()[1:]
  return [row.split("\t")[0] for row in rows if row.strip()]


class UrlStore:
  """Keeps track of known URLs, crawled URLs and the queue of URLs to crawl.

  Every change is written to the TSV files immediately, so nothing is lost
  when the crawler is interrupted.
  """

  def __init__(self, all_urls_file, crawled_urls_file):
    self.all_urls_file = all_urls_file
    self.crawled_urls_file = crawled_urls_file
    create_tsv_if_missing(all_urls_file, ALL_URLS_HEADER)
    create_tsv_if_missing(crawled_urls_file, CRAWLED_URLS_HEADER)

    known_urls = list(dict.fromkeys(read_tsv_first_column(all_urls_file)))
    self.known = set(known_urls)
    self.crawled = set(read_tsv_first_column(crawled_urls_file))
    # URLs waiting to be crawled, in the order they were discovered
    self.queue = deque(url for url in known_urls if url not in self.crawled)

  def add(self, urls):
    """Save URLs not seen before to all_urls and queue them.

    Returns how many of them were new.
    """
    new_urls = []
    for url in urls:
      if url not in self.known:
        self.known.add(url)
        new_urls.append(url)

    append_tsv_rows(self.all_urls_file, [[url] for url in new_urls])
    self.queue.extend(new_urls)
    return len(new_urls)

  def mark_crawled(self, url, status, filename=""):
    self.crawled.add(url)
    crawled_at = time.strftime("%Y-%m-%d %H:%M:%S")
    append_tsv_rows(self.crawled_urls_file, [[url, status, filename, crawled_at]])

  def next_url(self):
    """Return the next URL to crawl, or None when the queue is empty."""
    while self.queue:
      url = self.queue.popleft()
      if url not in self.crawled:
        return url
    return None


def save_page(url, content):
  """Save the raw page bytes to saved_pages/ and return the file name."""
  filename = url_to_filename(url)
  with open(os.path.join(SAVED_PAGES_DIR, filename), "wb") as f:
    f.write(content)
  return filename


# =============================================================================
# Crawler
# =============================================================================

def crawl_page(session, store, robots, url):
  """Download one page, save it and queue the new links found on it."""
  response = fetch(session, url)
  if response is None:
    print("  -> Failed, it stays in the queue for the next run.")
    return

  # Redirected: the page really lives at final_url
  if response.history:
    final_url = normalize_url(response.url, url)
    if final_url != url:
      print(f"  -> Redirected to {final_url}")
      store.mark_crawled(url, response.history[0].status_code)
      if final_url in store.crawled or not is_crawlable(final_url, robots):
        return
      store.add([final_url])
      url = final_url

  if response.status_code != 200:
    print(f"  -> HTTP {response.status_code} {response.reason}")
    store.mark_crawled(url, response.status_code)
    return

  content_type = response.headers.get("Content-Type", "")
  if "text/html" not in content_type:
    print(f"  -> Not an HTML page ({content_type}), skipped.")
    store.mark_crawled(url, response.status_code)
    return

  filename = save_page(url, response.content)
  links = extract_links(response_text(response), url)
  new_count = store.add(link for link in links if is_crawlable(link, robots))
  store.mark_crawled(url, response.status_code, filename)
  print(f"  -> Saved {filename} ({len(links)} links, {new_count} new)")


def seed_queue(session, store, robots):
  """Add START_URLS and all sitemap URLs to the queue (known ones are skipped)."""
  seed_urls = list(START_URLS)
  if SITEMAP_URL:
    seed_urls += get_sitemap_urls(session, SITEMAP_URL)

  normalized = (normalize_url(url, BASE_URL) for url in seed_urls)
  new_count = store.add(
      url for url in normalized if url and is_crawlable(url, robots)
  )
  print(f"Found {len(seed_urls)} start/sitemap URLs, {new_count} of them new.\n")


def crawl():
  os.makedirs(SAVED_PAGES_DIR, exist_ok=True)
  os.makedirs(LINKS_DIR, exist_ok=True)

  session = requests.Session()
  session.headers.update(HEADERS)

  store = UrlStore(ALL_URLS_FILE, CRAWLED_URLS_FILE)
  print(
      f"Loaded progress: {len(store.known)} known URLs, "
      f"{len(store.crawled)} crawled, {len(store.queue)} waiting."
  )
  print(f"Delay between requests: {CRAWL_DELAY} seconds.\n")

  pages_this_run = 0
  try:
    robots = load_robots(session)
    seed_queue(session, store, robots)

    while MAX_PAGES_PER_RUN is None or pages_this_run < MAX_PAGES_PER_RUN:
      url = store.next_url()
      if url is None:
        break
      if not is_crawlable(url, robots):
        print(f"Skipping (excluded by config or robots.txt): {url}")
        continue

      print(f"[{len(store.crawled)} crawled | {len(store.queue)} waiting] {url}")
      crawl_page(session, store, robots, url)
      pages_this_run += 1
      time.sleep(CRAWL_DELAY)

  except KeyboardInterrupt:
    print("\nInterrupted. Progress is saved - run the script again to continue.")
    return

  print(
      f"\nDone for this run: {pages_this_run} pages processed, "
      f"{len(store.crawled)} crawled in total, {len(store.queue)} still waiting."
  )


if __name__ == "__main__":
  crawl()
