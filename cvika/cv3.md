====== Odovzdanie 1 ======

Ako rámcovú tému som si vybral spoločenské hry. Používatel by mal mať možnosť vyhladať hry podla názvu, popisu, dizajnéra alebo vlastností hry (strategické, katrové, party etc.). Indexer by mal nájsť relevantné výsledky na základe vyhladávaných slov.

===== Scrapovaná stránka a extrahované dáta =====

Zdroj: [[https://boardgamewikia.com|boardgamewikia.com]]. Stránka je pôvodom z vietnamu takže je potrebné nastaviť utf-8 kódovanie pre niektoré stránky. V Extraktor určí typ stránky podľa URL a overí ho podľa obsahu. Každý typ stránky má vlastné regexy a vlastnú tabuľku:

^ Typ stránky ^ URL ^ Výstup ^ Riadkov ^
| hra | ''/<slug>'' | ''games.tsv'' | 3 659 |
| autor / ilustrátor / vydavateľ | ''/boardgamedesigner/…'', ''/boardgameartist/…'', ''/boardgamepublisher/…'' | ''designers.tsv'', ''artists.tsv'', ''publishers.tsv'' | 2 179 / 3 392 / 2 688 |
| kategória / mechanika / typ | ''/category/…'', ''/mechanisms/…'', ''/subdomain/…'' | ''categories.tsv'', ''mechanisms.tsv'', ''types.tsv'' | 79 / 191 / 9 |
| rebríček | ''/ranking?page=N'' | poradie, hodnotenie a počet hlasujúcich sa doplnia do ''games.tsv'' | – |
| eventy, obchody, používatelia, vyhľadávanie, statické stránky | – | nepoužívajú sa (pre projekt nie sú relevantné) | – |

==== 5 ukážok extrahovaných dát ====

Hry (''games.tsv'', vybrané stĺpce, v TSV sú viaceré hodnoty oddelené znakom %%|%%, tu čiarkou):

^ name ^ year ^ hráči ^ min ^ vek ^ complexity ^ rating ^ num_voters ^ designers ^ categories ^ is_expansion / base_game ^
| Gloomhaven | 2017 | 1–4 | 60–120 | 14 | 3.92 | 8.531 | 67 850 | Isaac Childres | Adventure, Exploration, Fantasy, Fighting, Miniatures | 0 |
| Wingspan | 2019 | 1–5 | 40–70 | 10 | 2.48 | 7.993 | 115 977 | Elizabeth Hargrave | Animals, Card Game, Educational, Environmental | 0 |
| The Grizzled | 2015 | 2–5 | 30 | 14 | 1.97 | 7.105 | 15 743 | Fabien Riffaud, Juan Rodriguez | Card Game, World War I | 0 |
| Arcs: The Blighted Reach Expansion | 2024 | 2–4 | – | – | 4.55 | 8.846 | 2 353 | Cole Wehrle | Expansion for Base-game, Negotiation, Science Fiction | 1 / ''arcs'' |

Entity (''designers.tsv'', ''mechanisms.tsv''):

^ súbor ^ slug ^ name ^ num_games ^ games ^
| designers.tsv | reiner-knizia | Reiner Knizia | 62 | ra, the-quest-for-el-dorado, tigris-euphrates, modern-art, … |
| mechanisms.tsv | cooperative-game | Cooperative Game | 568 | pandemic-legacy-season-1, gloomhaven, spirit-island, … |

Ďalšie stĺpce ''games.tsv'': ''summary'', ''rank'', ''bgg_id'', ''artists'', ''publishers'', ''mechanisms'', ''types'', ''related_games'', ''description'', ''how_to_play'' (spolu 26 stĺpcov).


^ Krok ^ Skript ^ Vstup ^ Výstup ^ Čas ^
| 1. crawlovanie | ''main.py'' | boardgamewikia.com | ''saved_pages/'' (15 334 HTML), ''links/*.tsv'' | 12. – 20. 10. 2026 |
| 2. extrakcia | ''extractor.py'' | ''saved_pages/'' | ''extracted/*.tsv'' (7 tabuliek) | 12 s |
| 3. index | ''indexer.py build'' | ''extracted/games.tsv'' | ''index/documents.tsv'', ''index/terms.tsv'' | 1 s |
| 4. vyhľadávanie | ''indexer.py search'' | dopyt | zoradené hry | 65 ms |

===== Queries a odpovede systému =====

  * Brass Birmingham spoločenskú hru -> systém vráti informácie o hre Brass birmingham
  * Aké expanzie na hru Wingspan existujú -> systém vráti IBA zoznam expanzii na hru Wingspan (Wingspan: European Expansion eg.)
  * Nájdi mi hry od dizajnéra Reiner Knizia -> Zoznam hier ktoré dizajnoval/spoludizajnoval Reiner Knizia (Ra)
  * Nájdi mi miniatúrové hry s horrorovou tematikou -> Zoznam horrorových kartových hier (Horrified)
  * Nájdi mi kartové hry hry s tematikou 2. svetovej vojny aleb hry z Warhammer 40k -> Spojený zoznam kartových hier z 2. sv a Warhammer (Undatunted & Warhammer 40k spacemarine)

===== Knižnice =====

^ Modul ^ Kde ^ Prečo ^
| ''requests'' | sťahovanie stránok (''requests.Session'') | jednoduché HTTP, jedno spojenie pre všetky požiadavky |
| ''re'' | extraktor, indexer | celá extrakcia z HTML a tokenizácia |
| ''html'' | extraktor | dekódovanie entít (''&#039;'' → apostrof) |
| ''unicodedata'' | indexer | odstránenie diakritiky (''Jožin'' → ''jozin'') |
| ''math'', ''collections.Counter'' | indexer | log, odmocnina, počty termov |
| ''argparse'' | indexer | príkazový riadok (''build'', ''search'') |
| ''unittest'' | testy | testy regexov |

===== 7. Hlavičky, timeouty, sleep =====

^ Nastavenie ^ Hodnota ^ Prečo ^
| ''User-Agent'' | ''VinfProjectBot/1.0 (Contact: xkemenya@stuba.sk)'' | bot sa identifikuje, správca vie, komu napísať |
| ''Accept-Encoding'' | ''gzip, deflate'' | menej prenesených dát (stránka má priemerne 150 KB) |
| ''Connection'' | ''keep-alive'' (''requests.Session'') | jedno TCP spojenie, menšia záťaž servera |
| timeout | 30 s | zaseknuté spojenie nezastaví crawler |
| sleep | 1 s po každej požiadavke | robots.txt nemá ''Crawl-delay'', 1 požiadavka za sekundu nezaťaží malú stránku |
| opakovanie | 3 pokusy, pauza 5 s a 10 s | len pri dočasných chybách (sieť, 429, 5xx) |
| robots.txt | dodržiava sa | zakázané sú napr. ''/login'', ''/api/'', ''/blog/'' |

===== Architektúra Crawleru =====

^ Krok ^ Skript ^ Vstup ^ Výstup ^ Čas ^
| 1. crawlovanie | ''main.py'' | boardgamewikia.com | ''saved_pages/'' (15 334 HTML), ''links/*.tsv'' | 12. – 20. 10. 2026 |
| 2. extrakcia | ''extractor.py'' | ''saved_pages/'' | ''extracted/*.tsv'' (7 tabuliek) | 12 s |
| 3. index | ''indexer.py build'' | ''extracted/games.tsv'' | ''index/documents.tsv'', ''index/terms.tsv'' | 1 s |
| 4. vyhľadávanie | ''indexer.py search'' | dopyt | zoradené hry | 65 ms |

{{:user:adam_kemeny:diagram.png?400|}}

===== Extrakcia URL z HTML =====

Odkazy berieme len z ''<a href>''. Najprv sa odstránia ''<script>'' a HTML komentáre, pretože obsahujú šablóny ako ''href="${linkHref}"''. Kód: [[https://github.com/Brovoli/vinf/blob/main/main.py#L267-L313|main.py, riadky 267–313]], normalizácia URL: [[https://github.com/Brovoli/vinf/blob/main/main.py#L84|main.py, riadok 84]].

<code python>
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


def extract_links(page_html, page_url):
  """Return the normalized URLs of all <a href> links on the page."""
  page_html = SCRIPT_OR_COMMENT_PATTERN.sub("", page_html)
  links = []
  for double_quoted, single_quoted in LINK_PATTERN.findall(page_html):
    url = normalize_url(double_quoted or single_quoted, page_url)
    if url:
      links.append(url)
  return links
</code>

^ Vstup ''href'' ^ Výsledok ^
| ''/ark-nova/'' | ''https://boardgamewikia.com/ark-nova'' |
| ''https://BoardGameWikia.com/root#top'' | ''https://boardgamewikia.com/root'' |
| ''mailto:a@b.c'', ''#top'', ''${linkHref}'' v ''<script>'' | ignorované |

===== Extrakcia entít z HTML =====

Kód: [[https://github.com/Brovoli/vinf/blob/main/extractor.py#L62-L198|regexy]] (pri každom je v komentári príklad), [[https://github.com/Brovoli/vinf/blob/main/extractor.py#L239-L290|extract_game]], [[https://github.com/Brovoli/vinf/blob/main/extractor.py#L293-L307|extract_listing, extract_ranking]].

Ukážka regexov ([[https://github.com/Brovoli/vinf/blob/main/extractor.py#L104-L141|extractor.py, riadky 104–141]]):

<code python>
# <div class="box_info"> <div class="item"> <span>Rank: 4</span> ... <div class="content_p_ab">
#   -> after clean(): "Rank: 4 1-4 Players 60-120 Min Age: 14+ Complexity: 3.92/5"
INFO_BOX = re.compile(r'<div class="box_info">(.*?)<div class="content_p_ab">', re.S)

# "1-4 Players"  -> ("1", "4")
# "2 Players"    -> ("2", None)
PLAYERS = re.compile(r"(\d+)(?:-(\d+))? Players?")

# href="https://boardgamewikia.com/boardgamedesigner/isaac-childres/">Isaac Childres</a>
#   -> ("boardgamedesigner", "isaac-childres", "Isaac Childres")
# href="https://boardgamewikia.com/mechanisms/action-queue/"><span>Action Queue</span></a>
#   -> ("mechanisms", "action-queue", "<span>Action Queue</span>")
ENTITY_LINK = re.compile(
    rf'href="https://boardgamewikia\.com/({ENTITY_KINDS})/([^/"?]+)/?"[^>]*>(.*?)</a>',
    re.S)
</code>

Použitie v ''extract_game'' (skrátené):

<code python>
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
  ...
</code>


===== Indexer a index =====

Kód: [[https://github.com/Brovoli/vinf/blob/main/indexer.py|indexer.py]]

<code>
python indexer.py build                          # vytvorí index/ z extracted/games.tsv
python indexer.py search cooperative dice        # hry so VŠETKÝMI termami (AND)
python indexer.py search horror dice OR zombie   # (horror AND dice) OR zombie
python indexer.py search world war I --scheme double --top 5
python indexer.py search                         # interaktívny režim
</code>

^ Vlastnosť ^ Hodnota ^
| dokument | 1 hra (3 659 dokumentov) |
| indexované stĺpce | name, summary, designers, categories, mechanisms, types, description, how_to_play (bez artists a publishers: hra má až 100+ vydavateľov, čo by prevážilo popis) |
| spracovanie textu | malé písmená, bez diakritiky, regex ''[^\W_]+'', anglické stopslová (bez ''i'' kvôli „World War I“), jednoduchý stemming množného čísla (''zombies'' → ''zombie'') |
| index | invertovaný index ''term → df, [(doc_id, tf)]'' v TSV |
| veľkosť | 24 508 termov, 363 140 postingov, 3,1 MB |
| vytváranie | **raz** po extrakcii (~1 s), znova len pri zmene dát. Pri vyhľadávaní sa iba načíta (postingy sa parsujú len pre termy z dopytu). |
| dopyt | termy sú spojené cez AND, ''OR'' oddeľuje alternatívy |

Formát indexu:

<code>
index/terms.tsv
term     df   postings (doc_id:tf)
zombie   45   90:6|176:1|274:1|397:3|...

index/documents.tsv
doc_id  slug        name        year  url                                   length  max_tf  norm_classic  norm_double
0       11-nimmt    11 nimmt!   2010  https://boardgamewikia.com/11-nimmt   131     19      50.335426     14.981085
</code>

''norm_*'' je dĺžka TF-IDF vektora hry pre každú schému. Počíta sa raz pri ''build'' a slúži ako menovateľ kosínusovej podobnosti.

===== Metódy výpočtu TF-IDF =====

Obe metódy používajú rovnaké **idf = ln(N / df)** (N = 3 659 hier, df = počet hier s termom). Líšia sa vo **váhe tf**. Hry sa zoraďujú podľa **kosínusovej podobnosti** vektora dopytu a vektora hry.

^ Metóda ^ Váha termu ^ Vlastnosť ^
| klasické TF-IDF | ''w = tf · idf'' | odmeňuje opakovanie termu v texte |
| double normalization (K = 0,5) | ''w = (0,5 + 0,5 · tf / max_tf) · idf'' | tf je v intervale <0,5; 1>, opakovanie pomáha málo, dlhé texty nemajú výhodu |

Kód ([[https://github.com/Brovoli/vinf/blob/main/indexer.py#L107-L116|indexer.py, riadky 107–116]]):

<code python>
def tf_weight(scheme, tf, max_tf):
  """classic: tf=3 -> 3;  double: tf=3, max_tf=6 -> 0.5 + 0.5 * 3/6 = 0.75"""
  if scheme == "classic":
    return tf
  return DOUBLE_NORMALIZATION_K + (1 - DOUBLE_NORMALIZATION_K) * tf / max_tf


def idf(df, num_documents):
  """df=10 of N=3659 games -> log(365.9) = 5.90; terms in no game -> 0"""
  return math.log(num_documents / df) if df else 0.0
</code>

idf termov z porovnávaných dopytov:

^ term ^ world ^ war ^ i ^ reiner ^ knizia ^ horror ^ dice ^ zombie ^
| df | 680 | 244 | 257 | 71 | 63 | 205 | 881 | 45 |
| idf | 1,68 | 2,71 | 2,66 | 3,94 | 4,06 | 2,88 | 1,42 | 4,40 |

===== Porovnanie metód na dopytoch =====

Obe metódy vrátia tie isté hry, líšia sa poradím.

==== „world war I“ (18 hier) ====

^ # ^ klasické TF-IDF ^ skóre ^ double normalization ^ skóre ^
| 1 | Twilight Struggle | 70,49 | Undaunted: Stalingrad | 5,21 |
| 2 | Star Wars: Rebellion | 63,81 | Undaunted: Normandy | 4,95 |
| 3 | War of the Ring: Second Edition | 42,20 | Undaunted: Battle of Britain | 4,74 |
| 4 | Churchill | 30,24 | Star Wars: Rebellion | 4,62 |
| 5 | Root | 25,69 | History of the World | 4,53 |

Klasické uprednostní dlhé texty s častým „war“ (Twilight Struggle 19×). Double uprednostní krátke popisy, a tak je History of the World (hra o 1. svetovej vojne) 5., pri klasickom až 10.

==== „Reiner Knizia“ (63 hier) ====

^ # ^ klasické TF-IDF ^ skóre ^ double normalization ^ skóre ^
| 1 | Botswana | 24,01 | High Society | 6,00 |
| 2 | Tigris & Euphrates | 24,01 | Pick-omino | 6,00 |
| 3 | Battle Line: Chiến Thần Vũ Trụ | 20,07 | The Quest for El Dorado | 6,00 |
| 4 | Lost Cities: The Board Game | 20,07 | Tigris & Euphrates | 6,00 |
| 5 | Rebirth | 20,07 | Rebirth | 5,67 |

Klasické uprednostní hry, kde je meno v popise 3×. Pri double majú 4 hry rovnaké skóre (oba termy majú tf / max_tf = 1/2), poradie medzi nimi určí abeceda.

==== „horror dice OR zombie“ (113 hier) ====

^ # ^ klasické TF-IDF ^ skóre ^ double normalization ^ skóre ^
| 1 | Tiny Epic Zombies | 123,06 | Mall of Horror | 7,18 |
| 2 | Zombie in My Pocket | 55,66 | Run Fight or Die: Reloaded | 7,06 |
| 3 | Last Night on Earth: The Zombie Game | 51,08 | Hit Z Road | 6,96 |
| 4 | Zombicide: Gear Up | 48,38 | Zombicide: 2nd Edition | 6,91 |
| 5 | Zombie Princess | 46,86 | Last Night on Earth: The Zombie Game | 6,91 |

Pri klasickom rozhoduje jedno opakované slovo (Tiny Epic Zombies: „zombie“ 27×). Pri double vyhrajú hry, ktoré obsahujú všetky tri slová.

==== Zhrnutie ====

^ ^ klasické TF-IDF ^ double normalization ^
| rozhoduje | počet výskytov termu | prítomnosť termu |
| dlhé texty | majú výhodu | nemajú výhodu |
| skóre v top 5 | 20 – 123 | 4,5 – 7,2 |

===== Štatistika crawlu =====

Spolu 15 939 URL: 15 334 × HTTP 200, 309 × 404, 296 × 302.

^ Typ stránky ^ Stránok ^ Na disku ^ Relevantné ^
| hry | 3 659 | 995 MB | áno |
| autori, ilustrátori, vydavatelia | 8 942 | 912 MB | áno |
| kategórie, mechaniky, typy | 1 424 | 208 MB | áno |
| rebríček | 184 | 23 MB | áno |
| ostatné (vyhľadávanie, rebríčky podľa typu, obchody, eventy, používatelia, statické stránky) | 1 125 | 213 MB | nie |
| **spolu** | **15 334** | **2,35 GB** | **14 209 (93 %)** |

^ Dáta ^ Veľkosť ^
| HTML (''saved_pages/'') | 2,35 GB |
| extrahované TSV (''extracted/'') | 10,6 MB |
| index (''index/'') | 3,0 MB |

==== BONUS: počet tokenov ====

^ Text ^ Tokenov ^ Rôznych termov ^
| celý ''games.tsv'' | 1 395 356 | – |
| indexované stĺpce pred spracovaním | 905 586 | 28 275 |
| v indexe (bez stopslov, po stemmingu) | 544 759 | 24 508 |
| priemer na hru v indexe | 149 | – |

===== ZIP s kódom =====

{{ :user:adam_kemeny:adam_kemeny_vinf1.zip |zip link}} (''main.py'', ''extractor.py'', ''indexer.py'', ''tests/test_regex.py'', ''requirements.txt'')

===== BONUS: unit testy regexov =====

[[https://github.com/Brovoli/vinf/blob/main/tests/test_regex.py|tests/test_regex.py]]: 23 testov na HTML úryvkoch z reálnych stránok.

^ Časť ^ Čo testy overujú ^
| crawler | odkazy z ''<a href>'', ignorovanie ''<script>'', robots.txt |
| extraktor | typ stránky podľa URL, hra, autor, rebríček, čistenie textu |
| indexer | tokenizácia, diakritika, množné číslo, AND/OR |

<code>
$ python -m unittest discover tests
.......................
Ran 23 tests in 0.001s
OK
</code>