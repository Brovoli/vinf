====== Konzultácia 3 ======

Opis projektu a dvojice otázok a odpovedí sú v **Konzultácii 1**. Frameworky crawlera, diagram architektúry, metadáta crawlovania (''crawled_urls.tsv'') a zdôvodnenie hlavičiek, timeoutov a sleepov sú v **Konzultácii 2**. Tu je len to, čo pribudlo: dokončený crawl, extrakcia, indexer a TF-IDF.

Celý postup:

^ Krok ^ Skript ^ Vstup ^ Výstup ^ Čas ^
| 1. crawlovanie | ''main.py'' | boardgamewikia.com | ''saved_pages/'' (15 334 HTML), ''links/*.tsv'' | 12. – 20. 10. 2026 |
| 2. extrakcia | ''extractor.py'' | ''saved_pages/'' | ''extracted/*.tsv'' (7 tabuliek) | 12 s |
| 3. index | ''indexer.py build'' | ''extracted/games.tsv'' | ''index/documents.tsv'', ''index/terms.tsv'' | 1 s |
| 4. vyhľadávanie | ''indexer.py search'' | dopyt | zoradené hry | 65 ms |

===== Scrapovaná stránka a extrahované dáta =====

Zdroj: [[https://boardgamewikia.com|boardgamewikia.com]]. Extraktor určí typ stránky podľa URL a overí ho podľa obsahu. Každý typ stránky má vlastné regexy a vlastnú tabuľku:

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

===== Nové knižnice =====

Doplnenie ku Konzultácii 2. Stále len štandardná knižnica Pythonu, bez pandas, NLTK a SQL.

^ Modul ^ Kde ^ Prečo ^
| ''re'' | extraktor, indexer | celá extrakcia z HTML a tokenizácia |
| ''html'' | extraktor | dekódovanie entít (''&#039;'' → apostrof) |
| ''unicodedata'' | indexer | odstránenie diakritiky (''Jožin'' → ''jozin'') |
| ''math'', ''collections.Counter'' | indexer | log, odmocnina, počty termov |
| ''argparse'' | indexer | príkazový riadok (''build'', ''search'') |
| ''unittest'' | testy | testy regexov |

Index je **vlastný** (pravidlá to povoľujú). Plán z Konzultácie 2 s PyLucene sme zmenili, pretože potrebujeme dve vlastné schémy váženia TF-IDF.

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

Zaujímavosti pri extrakcii:

^ Problém ^ Riešenie ^
| Eventy a obchody sú na stránke hry | sú v samostatnej záložke ''play_now'', ktorú extraktor nečíta |
| „Suggested Games“ sú náhodné (prekryv mechaník 0,07, náhodné hry 0,06) | berieme len „Related Games“ (prekryv 0,27) |
| Rozšírenie neodkazuje na základnú hru | odhad podľa prefixu slugu/názvu, prednosť má spoločný autor: 464 zo 478 rozšírení |
| Typy (''/subdomain/'') majú v ''<h1>'' len slug (''party-games'') | názov sa berie z odkazov na stránkach hier (''Party Games'') |
| Poradie na stránkach hier je z rôznych dní crawlu | poradie, hodnotenie a hlasujúci sa berú z rebríčka (jeden snímok) |

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

^ term ^ df ^ idf ^
| game | 3 621 | 0,010 |
| dice | 881 | 1,424 |
| world | 680 | 1,683 |
| cooperative | 609 | 1,793 |
| i | 257 | 2,656 |
| war | 244 | 2,708 |
| horror | 205 | 2,882 |
| reiner | 71 | 3,942 |
| knizia | 63 | 4,062 |
| zombie | 45 | 4,398 |

===== Porovnanie metód na dopytoch =====

Obe metódy dostanú tú istú množinu hier (AND/OR filter), líšia sa len poradím.

==== 1. „world war I“ – 18 hier ====

^ # ^ klasické TF-IDF ^ skóre ^ double normalization ^ skóre ^
| 1 | Twilight Struggle | 0,205 | Risk | 0,145 |
| 2 | Star Wars: Rebellion | 0,174 | Aeon's End: War Eternal | 0,131 |
| 3 | Aeon's End: War Eternal | 0,173 | **The Grizzled** | 0,125 |
| 4 | War of the Ring: Second Edition | 0,170 | **History of the World** | 0,121 |
| 5 | Undaunted: Stalingrad | 0,154 | Sniper Elite: The Board Game | 0,119 |

Double normalization dostane obe hry z kategórie World War I do top 4. Klasické TF-IDF uprednostní dlhé popisy, kde sa často opakuje „war“.

==== 2. „Reiner Knizia“ – 63 hier ====

^ # ^ klasické TF-IDF ^ skóre ^ double normalization ^ skóre ^
| 1 | Medici | 0,331 | Ninja Master | 0,290 |
| 2 | MEOW | 0,319 | Piñatas | 0,273 |
| 3 | High Society | 0,317 | MEOW | 0,266 |
| 4 | Piñatas | 0,301 | The Quest for El Dorado: The Golden Temples | 0,238 |
| 5 | Rebirth | 0,285 | Medici | 0,230 |

Klasické TF-IDF dáva vyššie hry, ktoré meno Knizia spomínajú v popise viackrát. Double normalization dáva vyššie hry s krátkym popisom.

==== 3. „horror dice OR zombie“ – 113 hier ====

^ # ^ klasické TF-IDF ^ skóre ^ double normalization ^ skóre ^
| 1 | Tiny Epic Zombies | 0,670 | After the Virus | 0,257 |
| 2 | Last Night on Earth: The Zombie Game | 0,610 | Selfish: Zombie Edition | 0,255 |
| 3 | Zombicide | 0,597 | Zombicide | 0,251 |
| 4 | Zombie in My Pocket | 0,552 | Zombie Kittens | 0,238 |
| 5 | After the Virus | 0,525 | Flick 'em Up!: Dead of Winter | 0,223 |

Pri klasickom TF-IDF rozhoduje počet výskytov slova „zombie“ (skóre až 0,67). Pri double normalization sú skóre nižšie a bližšie pri sebe, takže vyššie sa dostanú aj kratšie popisy.

==== Zhrnutie ====

^ ^ klasické TF-IDF ^ double normalization ^
| čo odmeňuje | časté opakovanie termu | prítomnosť termu, krátke texty |
| rozsah skóre (top 5) | širší (0,15 – 0,67) | užší (0,12 – 0,29) |
| vhodné pre | fulltext („o čom hra je“) | metadáta (kategória, autor) |

===== Štatistika crawlu =====

Crawl je dokončený. Prešlo sa 15 939 URL: 15 334 × HTTP 200, 309 × 404, 296 × 302.

^ Typ stránky ^ Stránok ^ Veľkosť ^ Relevantné ^
| hry (''/<slug>'') | 3 673 | 998 MB | áno, 3 659 hier (14 sú statické stránky) |
| ilustrátori | 3 422 | 335 MB | áno |
| vydavatelia | 3 320 | 358 MB | áno |
| autori | 2 200 | 219 MB | áno |
| mechaniky | 831 | 120 MB | áno |
| kategórie | 470 | 70 MB | áno |
| typy (''/subdomain/'') | 123 | 19 MB | áno |
| rebríček (všetky hry) | 184 | 23 MB | áno |
| rebríček podľa typu | 358 | 45 MB | nie (duplikát) |
| vyhľadávanie, populárne, najlepšie… | 515 | 79 MB | nie (zoznamy hier bez nových údajov) |
| obchody | 166 | 62 MB | nie |
| eventy | 33 | 18 MB | nie |
| používatelia, ostatné | 39 | 7 MB | nie |
| **spolu** | **15 334** | **2,35 GB** | **14 209 (93 %)** |

^ Dáta ^ Veľkosť ^
| ''saved_pages/'' (surové HTML) | 2,35 GB |
| ''extracted/'' (7 TSV tabuliek) | 10,6 MB |
| ''index/'' | 3,1 MB |

==== BONUS: počet tokenov ====

^ Text ^ Tokenov ^ Rôznych termov ^
| celý ''games.tsv'' (všetky stĺpce) | 1 395 356 | – |
| indexované stĺpce (pred spracovaním) | 905 586 | 28 275 |
| po odstránení stopslov a stemmingu (index) | 544 759 | 24 508 |
| priemer na hru | 149 | – |

===== BONUS: unit testy regexov =====

[[https://github.com/Brovoli/vinf/blob/main/tests/test_regex.py|tests/test_regex.py]] obsahuje 23 testov. Testujú odkazy a robots.txt v crawleri, každý typ stránky v extraktore (na HTML úryvkoch z reálnych stránok) a tokenizér indexera.

<code>
$ python -m unittest discover tests
.......................
Ran 23 tests in 0.001s
OK
</code>

===== Kód =====

ZIP: ''cv3_kod.zip'' (''main.py'', ''extractor.py'', ''indexer.py'', ''tests/test_regex.py'', ''requirements.txt'').
