"""
Unit tests for the regex extractors (crawler, extractor, indexer tokenizer).
HTML snippets are copied from real saved pages.

  python -m unittest discover tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import extractor as ex  # noqa: E402
import indexer as ix  # noqa: E402
import main as crawler  # noqa: E402

B = "https://boardgamewikia.com/"

GAME_PAGE = """
<div class="container game-detail">
 <div class="title_h1">
  <div class="point"> <span>8.5</span> </div>
  <h1>Gloomhaven (2017)</h1>
 </div>
 <p class="desc">Travel to dark corners of the world.</p>
 <div class="box_info">
  <div class="item"><span>Rank: 4</span></div>
  <div class="item"><span>1-4 Players</span></div>
  <div class="item"><span>60-120 Min</span></div>
  <div class="item"><span>Age: 14+</span></div>
  <div class="item"><span>Complexity: 3.92/5</span></div>
 </div>
 <div class="content_p_ab">
  <p class="designer-wrapper">Designer:
   <a href="https://boardgamewikia.com/boardgamedesigner/isaac-childres/">Isaac Childres</a></p>
  <p class="artist-wrapper">Artist:
   <a href="https://boardgamewikia.com/boardgameartist/alexandr-elichev/">Alexandr Elichev</a>
   <span class="more-publishers" style="display: none;">,
   <a href="https://boardgamewikia.com/boardgameartist/alvaro-nebot/">Alvaro Nebot</a></span></p>
  <p class="publisher-wrapper">Publisher:
   <a href="https://boardgamewikia.com/boardgamepublisher/cephalofair-games">
    Cephalofair Games
   </a></p>
 </div>
 <div class="func_box">
  <a class="bgw-cab__btn bgw-bgg-link" href="https://boardgamegeek.com/boardgame/174430">View on BGG</a>
 </div>
</div>
<div class="title_right"></div>
<div class="tab-content" panel-contnet="overview">
 <div class="content_p">
  <h2>About the game</h2>
  <p><em><strong>Gloomhaven</strong></em> is a game of tactical combat.</p>
  <div class="more_content" style="display: none;"><h2>How To Play Gloomhaven</h2>
  <p>Choose two cards.</p></div>
  <p class="show_hide_howtoplay read_more" data-more="Read More" data-less="Show less">Read More</p>
 </div>
</div>
<div class="tab-content" panel-contnet="how_to_play"></div>
<div class="tab-content" panel-contnet="play_now"><h2>Events &amp; meetups for Gloomhaven</h2></div>
<div class="about_right_top">
 <h4>Classification</h4>
 <h5 class="tt_sub">Category</h5>
 <ul class="content"><li><a target="_blank"
  href="https://boardgamewikia.com/category/adventure/"><span>Adventure</span></a></li></ul>
 <h5 class="tt_sub">Mechanism</h5>
 <ul class="content"><li><a target="_blank"
  href="https://boardgamewikia.com/mechanisms/cooperative-game/"><span>Cooperative Game</span></a></li></ul>
 <h5 class="tt_sub">Type</h5>
 <ul class="content"><li><a target="_blank"
  href="https://boardgamewikia.com/subdomain/strategy-games/"><span>Strategy Games</span></a></li></ul>
</div>
<h2>Related Games</h2>
<a href="https://boardgamewikia.com/gloomhaven-jaws-of-the-lion/" class="game-hover-trigger"
   data-slug="gloomhaven-jaws-of-the-lion" data-id="1">
<h2>Suggested Games</h2>
<a href="https://boardgamewikia.com/harmonies/" class="game-hover-trigger" data-slug="harmonies">
"""

LISTING_PAGE = """
<div class="title_page title_browse_main"><h1>Designer: Reiner Knizia</h1></div>
<div style="overflow-x: auto;" class="wrapper_content_related_multi page " >
 <div class="child">
  <a href="https://boardgamewikia.com/ra/" title="Ra" class="game-hover-trigger" data-slug="ra">
  <a href="https://boardgamewikia.com/modern-art/" class="game-hover-trigger" data-slug="modern-art">
 </div>
</div>
</main>
"""

RANKING_PAGE = """
<div class="box_search">
 <div class="item rank  "><span>21</span></div>
 <div class="item box_title">
  <div class="ava"><a target="_blank" href="https://boardgamewikia.com/great-western-trail/"></a></div>
  <div class="title"><a href="https://boardgamewikia.com/great-western-trail/"><h2>Great Western Trail</h2></a>
  <p>Manage your herd.</p></div>
 </div>
 <div class="item"> <span>8.141</span> </div>
 <div class="item"> <span>44,222</span> </div>
</div>
<div class="box_search">
 <div class="item rank  "><span>-</span></div>
 <div class="item box_title">
  <div class="ava"><a target="_blank" href="https://boardgamewikia.com/1st-ceo/"></a></div>
 </div>
 <div class="item"> <span>8.429</span> </div>
 <div class="item"> <span>17</span> </div>
</div>
"""


class CrawlerLinkTests(unittest.TestCase):

  def test_extracts_absolute_and_relative_links(self):
    html = '<a href="/ark-nova/">x</a> <a class="c" href=\'https://BoardGameWikia.com/root#top\'>y</a>'
    self.assertEqual(crawler.extract_links(html, B + "gloomhaven"),
                     [B + "ark-nova", B + "root"])

  def test_ignores_script_templates_and_comments(self):
    html = '<script>x = `<a href="${linkHref}">`</script><!-- <a href="/old"> --><a href="/ra">'
    self.assertEqual(crawler.extract_links(html, B), [B + "ra"])

  def test_ignores_data_href_and_non_page_links(self):
    html = '<a data-href="/x">a</a><a href="mailto:a@b.c">b</a><a href="#top">c</a>'
    self.assertEqual(crawler.extract_links(html, B), [])

  def test_normalize_url_decodes_entities(self):
    self.assertEqual(crawler.normalize_url("/search?page=2&amp;sort=1", B),
                     B + "search?page=2&sort=1")

  def test_robots_wildcards(self):
    rules = crawler.RobotsRules("User-agent: *\nDisallow: /shops/*/follow-status\nDisallow: /login",
                                "VinfProjectBot/1.0")
    self.assertFalse(rules.is_allowed(B + "shops/abc/follow-status"))
    self.assertFalse(rules.is_allowed(B + "login?redirect=%2Fra"))
    self.assertTrue(rules.is_allowed(B + "shops/abc"))


class UrlLayoutTests(unittest.TestCase):

  def test_ranking_url(self):
    self.assertTrue(ex.RANKING_URL.fullmatch(B + "ranking?page=2"))
    self.assertIsNone(ex.RANKING_URL.fullmatch(B + "ranking?subdomain=1022"))

  def test_listing_url(self):
    self.assertEqual(ex.LISTING_URL.fullmatch(B + "boardgamedesigner/reiner-knizia?page=2").groups(),
                     ("boardgamedesigner", "reiner-knizia"))
    self.assertEqual(ex.LISTING_URL.fullmatch(B + "mechanisms/cooperative-game").groups(),
                     ("mechanisms", "cooperative-game"))

  def test_game_url(self):
    self.assertEqual(ex.GAME_URL.fullmatch(B + "gloomhaven").group(1), "gloomhaven")
    self.assertIsNone(ex.GAME_URL.fullmatch(B + "events?event=KJMJ40"))


class GamePageRegexTests(unittest.TestCase):

  def test_name_and_year(self):
    self.assertEqual(ex.NAME_YEAR.fullmatch("Gloomhaven (2017)").groups(), ("Gloomhaven", "2017"))
    self.assertEqual(ex.NAME_YEAR.fullmatch("Backgammon (-3000)").groups(), ("Backgammon", "-3000"))
    self.assertEqual(ex.NAME_YEAR.fullmatch(
        "Descent: Journeys in the Dark (Second Edition) (2012)").groups(),
        ("Descent: Journeys in the Dark (Second Edition)", "2012"))
    self.assertIsNone(ex.NAME_YEAR.fullmatch("Ô Ăn Quan"))

  def test_rating(self):
    self.assertEqual(ex.first(ex.RATING, '<div class="point"> <span>8.5</span>'), "8.5")
    self.assertEqual(ex.first(ex.RATING, '<div class="point"> <span>--</span>'), "")

  def test_info_box_values(self):
    self.assertEqual(ex.min_max(ex.PLAYERS, "1-4 Players"), ("1", "4"))
    self.assertEqual(ex.min_max(ex.PLAYERS, "1 Player"), ("1", "1"))
    self.assertEqual(ex.min_max(ex.PLAYTIME, "30 Min"), ("30", "30"))
    self.assertEqual(ex.min_max(ex.PLAYTIME, "-- Min"), ("", ""))
    self.assertEqual(ex.first(ex.AGE, "Age: 14+"), "14")
    self.assertEqual(ex.first(ex.AGE, "Age: --"), "")
    self.assertEqual(ex.first(ex.COMPLEXITY, "Complexity: 3.92/5"), "3.92")
    self.assertEqual(ex.first(ex.RANK, "Rank: 4"), "4")

  def test_entity_link(self):
    self.assertEqual(ex.ENTITY_LINK.search(
        'href="https://boardgamewikia.com/mechanisms/action-queue/"><span>Action Queue</span></a>'
    ).groups(), ("mechanisms", "action-queue", "<span>Action Queue</span>"))

  def test_whole_game_page(self):
    row, _ = ex.extract_game(GAME_PAGE, "gloomhaven")
    expected = {
        "name": "Gloomhaven", "year": "2017", "summary": "Travel to dark corners of the world.",
        "min_players": "1", "max_players": "4", "min_playtime": "60", "max_playtime": "120",
        "min_age": "14", "complexity": "3.92", "rating": "8.5", "rank": "4", "bgg_id": "174430",
        "designers": ["Isaac Childres"], "artists": ["Alexandr Elichev", "Alvaro Nebot"],
        "publishers": ["Cephalofair Games"], "categories": ["Adventure"],
        "mechanisms": ["Cooperative Game"], "types": ["Strategy Games"],
        "related_games": ["gloomhaven-jaws-of-the-lion"], "is_expansion": 0,
        "description": "About the game Gloomhaven is a game of tactical combat.",
        "how_to_play": "How To Play Gloomhaven Choose two cards.",
    }
    for column, value in expected.items():
      self.assertEqual(row[column], value, column)

  def test_events_and_suggested_games_are_not_extracted(self):
    row, _ = ex.extract_game(GAME_PAGE, "gloomhaven")
    self.assertNotIn("meetups", row["description"] + row["how_to_play"])
    self.assertNotIn("harmonies", row["related_games"])

  def test_non_game_page(self):
    self.assertIsNone(ex.extract_game("<h1>About Us</h1>", "about"))


class ListingAndRankingTests(unittest.TestCase):

  def test_listing_page(self):
    self.assertEqual(ex.extract_listing(LISTING_PAGE), ("Reiner Knizia", ["ra", "modern-art"]))

  def test_listing_prefix_only_for_people(self):
    self.assertEqual(ex.LISTING_PREFIX.sub("", "Turn Order: Progressive"), "Turn Order: Progressive")

  def test_ranking_rows(self):
    self.assertEqual(ex.extract_ranking(RANKING_PAGE), {
        "great-western-trail": ("21", "8.141", "44222"),
        "1st-ceo": ("", "8.429", "17"),
    })


class TextCleanupTests(unittest.TestCase):

  def test_clean(self):
    self.assertEqual(ex.clean("<p><em><strong>Carcassonne</strong></em> is\n  a <b>tile</b>-game</p>"),
                     "Carcassonne is a tile-game")
    self.assertEqual(ex.clean("You Laugh You&#039;re Out"), "You Laugh You're Out")

  def test_name_prefix(self):
    self.assertEqual(ex.NAME_PREFIX.split("Kemet: Blood and Sand – Onyx")[0], "Kemet")


class TokenizerTests(unittest.TestCase):

  def test_tokenize(self):
    self.assertEqual(ix.tokenize("The Zombies AND Dice"), ["zombie", "dice"])
    self.assertEqual(ix.tokenize("Jožin z Bažin"), ["jozin", "z", "bazin"])
    self.assertEqual(ix.tokenize("Children's Game"), ["children", "game"])
    self.assertEqual(ix.tokenize("World War I"), ["world", "war", "i"])

  def test_stem(self):
    self.assertEqual([ix.stem(w) for w in ["zombies", "cards", "chess", "bonus", "axis"]],
                     ["zombie", "card", "chess", "bonus", "axis"])

  def test_parse_query(self):
    self.assertEqual(ix.parse_query("horror dice OR zombie"), [["horror", "dice"], ["zombie"]])
    self.assertEqual(ix.parse_query("horror AND dice"), [["horror", "dice"]])
    self.assertEqual(ix.parse_query("the and of"), [])


if __name__ == "__main__":
  unittest.main()
