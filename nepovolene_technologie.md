SQL databázy sú nepovolené, ak potrebujete niečo uložiť, tak do csv súboru (resp. lepšie tsv - tab-separated values)
noSQL databázy sú na druhej strane povolené (ak by niekto potreboval niečo ukladať - poniektorí z vás majú nejaké veľké datasety, ktoré budú spracovávať, tak môžu) Cassandra, Hive, HBase, … (tieto 3 sú u nás aj nasadené, tak sa dajú použiť)
Python a Java sú vysoko odporúčané
Pri distribuovanom spracovaní je hlavným frameworkom Spark, ale ani klasický Hadoop, resp. Pig (dnes už ďalej nevyvíjaný a hlavne vhodný na spracovanie logov) nie sú na zahodenie
Na indexovanie použiť lucene (hlavne pre Java developerov), pre python je to trochu obtiažnejšie (existuje pylucene), je možné priamo použiť nejaký docker image s pylucene, alebo solrom, poprípade je dovolené budovať vlastný index (dosť roboty)
Vyhľadávanie je postačujúce robiť v command line
Evaluácia je vhodná, vždy nejakú vymyslíme, i keď niekedy bude dosť umelá, ak sa dá použiť nejaký zlatý štandard, ak nie skúšaním niekoľkých dopytov a porovnaním s tým čo mal systém vrátiť a čo vrátil
Pure Python: re, requests, playwright, selenium, NIE pandas, NIE NLTK (iba pre anglictinu, i to radsej nie)
