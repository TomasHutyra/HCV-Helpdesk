# HCV Helpdesk

Společnost HCV potřebuje evidovat požadavky uživatelů z firem, kterým
spravuje IT infrastrukturu a informační systém Helios. Pro evidenci,
zpracování a správu požadavků bude sloužit helpdesk.

Helpdesk slouží k

- Evidenci požadavků uživatelů

- Komentování požadavků uživateli

- Uzavírání požadavků

- Odesílání notifikací při vytvoření nového požadavku, přidání nového
  komentáře, změny stavu požadavku

- Vyhodnocování požadavků, přes firmy, oblasti (IT, Helios) a agenty za
  období (měsíc).

Práce bude standartně probíhat tak, že žadatel vytvoří požadavek.
Správce projde požadavek, upraví jej a přiřadí řešiteli nebo
obchodníkovi. Obchodník vykomunikuje nabídku a schválení. Správce
přiřadí požadavek řešiteli. Řešitel vyřeší požadavek, zapíše způsob
řešení, počet strávených hodin a uzavře požadavek. Správce může kdykoliv
požadavek zamítnout. Na konci měsíce správce vyhodnotí statistiky
jednotlivých řešitelů a firem. Správce se může vracet k minulým měsícům.

## Uživatelé

Každý uživatel má zadán kontaktní e-mail.

Uživatelé mohou mít následující role (jeden uživatel může mít více rolí)

- Žadatel

  - Zástupce spravované firmy

  - Může založit požadavek

  - Rozsah viditelnosti tiketů se nastavuje per-uživatel (administrátorem):
    - **Pouze vlastní tikety** (výchozí) — vidí jen tikety, které sám založil
    - **Všechny tikety firmy** — vidí všechny tikety své firmy
    - **Tikety firmy v konkrétních oblastech** — vidí tikety firmy v zadaných
      oblastech; vlastní tikety jsou vždy viditelné bez ohledu na oblast

  - Může komentovat pouze tikety, které sám založil (bez ohledu na rozsah viditelnosti)

  - Má přiřazenu společnost, ke které patří

  - Nevidí čas řešení požadavku

- Řešitel

  - Řešitel požadavku

  - Může mít nastaven seznam oblastí, kterým se věnuje.
    Pokud nemá nastaveno nic, vidí všechny nové tikety.
    Pokud má nastaveny oblasti, vidí nové tikety pouze z těchto oblastí
    a tikety s neznámou oblastí nebo bez oblasti.
    Přiřazené tikety vidí vždy bez ohledu na oblast.

  - Vidí přiřazené požadavky a navíc nové požadavky v rámci svých oblastí

  - Může komentovat přiřazené požadavky (požadavky ve stavu „Nový",
    které mu dosud nebyly přiřazeny, komentovat nemůže)

  - Může převzít požadavek ve stavu „Nový" nebo „Řeší se" — přiřadí se
    sám sobě; při převzetí z „Nový" přejde požadavek do stavu „Řeší se",
    při převzetí z „Řeší se" se stav nemění; převzít lze pouze tiket
    z oblasti, kterou řešitel spravuje (nebo neznámé oblasti)

  - Může změnit typ požadavku, prioritu, oblast a stav požadavku

  - Může průběžně zapisovat čas řešení

  - Může vyřešit požadavek -- při vyřešení požadavku musí zapsat způsob
    vyřešení a čas strávený řešením požadavku

  - Vidí své statistiky za období (měsíc) - kolik vyřešil požadavků,
    kolik jich má přiřazeno, jak dlouho trvá jeden požadavek, kolik času
    celkem strávil řešením požadavků, kolik má požadavků v jednotlivých
    stavech, průměrné hodnocení spokojenosti žadatelů za měsíc

- Obchodník

  - Má stejné možnosti jako Řešitel, ale může být přiřazen jen
    k požadavku typu „Požadavek na vývoj".

- Správce

  - Rozděluje a vyhodnocuje práci

  - Může mít nastaven seznam oblastí a/nebo seznam firem.
    Pokud nemá nastaveno nic, vidí a spravuje všechny požadavky.
    Pokud má nastaveny oblasti, vidí pouze požadavky těchto oblastí.
    Pokud má nastaveny firmy, vidí pouze požadavky daných firem.
    Pokud má nastaveno obojí, vidí požadavky splňující zároveň jednu
    z oblastí i jednu z firem.
    Oblast označená jako „neznámá" se jako omezení nepočítá —
    přiřazení takové oblasti správci nemá vliv na viditelnost tiketů.

  - Požadavky s oblastí označenou jako „neznámá" nebo bez oblasti
    projdou oblast-filtrem u všech správců (rozhoduje pouze omezení firem).

  - Může přiřadit řešitele a obchodníka požadavku

  - Může vyřešit a zamítnout -- při vyřešení požadavku musí zapsat
    způsob vyřešení a čas strávený řešením, při zamítnutí požadavku musí
    zapsat důvod zamítnutí.

  - Hodiny zadané správcem při vyřešení požadavku se připíší přiřazenému
    řešiteli. Pokud řešitel není přiřazen, připíší se správci.

  - Pokud je správce zároveň přiřazen jako řešitel nebo obchodník, může
    průběžně zapisovat čas stejně jako řešitel.

  - Může změnit typ požadavku, prioritu, oblast a stav požadavku

  - Vidí veškeré statistiky za období (měsíc) -- statistiky uživatelů
    (včetně průměrného hodnocení spokojenosti každého řešitele),
    přehledy pro jednotlivé firmy (počet požadavků, počet otevřených
    požadavků, čas strávený na požadavcích) v rámci svého omezení

- Administrátor

  - Zakládá nové uživatele

  - Přiřazuje role uživatelům

  - Zakládá firmy

  - Přiřazuje žadatele k firmám

  - Zakládá a spravuje oblasti (název, příznak „neznámá"); v přehledu
    oblastí vidí, které kategorie práce jsou k dané oblasti přiřazeny;
    při editaci oblasti může přímo přiřadit existující kategorie nebo
    vytvořit novou

  - Zakládá a spravuje kategorie práce (název, seznam oblastí) přes
    webové rozhraní (stránka „Kategorie práce" v menu)

  - Nastavuje omezení správcům — seznam oblastí a/nebo firem přímo
    na stránce „Upravit uživatele" (pole se zobrazí pouze pokud má
    uživatel přiřazenu roli Správce)

  - Nastavuje oblasti řešitelům přímo na stránce „Upravit uživatele"
    (pole se zobrazí pouze pokud má uživatel přiřazenu roli Řešitel)

  - Nastavuje rozsah viditelnosti tiketů žadatelům přímo na stránce
    „Upravit uživatele" (pole se zobrazí pouze pokud má uživatel
    přiřazenu roli Žadatel): výchozí hodnota je „Pouze vlastní tikety"

### Tabulka práv

| Funkce | Žadatel | Řešitel | Obchodník | Správce | Administrátor |
|--------|:-------:|:-------:|:---------:|:-------:|:-------------:|
| **Tikety — čtení** | | | | | |
| Vidí seznam tiketů | dle rozsahu ⁶ | přiřazené + všechny Nové ⁴ | jen přiřazené | všechny ¹ | všechny |
| Vidí detail tiketu | dle rozsahu ⁶ | přiřazený + každý Nový ⁴ | jen přiřazený | všechny ¹ | všechny |
| Vidí záznamy času a celkové hodiny | — | ✓ | ✓ | ✓ | — |
| **Tikety — vytvoření a editace** | | | | | |
| Vytvořit tiket | ✓ | — | — | ✓ | — |
| Editovat tiket (název, popis, typ, oblast, priorita) | — | přiřazený ² | — | ✓ ¹ ² | — |
| Změnit typ tiketu | — | přiřazený ² | — | ✓ ¹ ² | — |
| Nastavit kategorii práce | — | přiřazený ² | — | ✓ ¹ ² | — |
| **Tikety — komentáře, čas a přílohy** | | | | | |
| Komentovat tiket | jen vlastní ⁵ | přiřazený (jen otevřený) | přiřazený (jen otevřený) | ✓ ¹ | — |
| Zapsat čas | — | přiřazený | přiřazený | jen pokud přiřazen ³ | — |
| Přidat přílohu | jen vlastní | přiřazený | přiřazený | ✓ ¹ | — |
| Smazat přílohu | vlastní přílohy | vlastní přílohy | vlastní přílohy | ✓ ¹ | ✓ |
| **Tikety — akce** | | | | | |
| Převzít tiket (přiřadit se sám sobě) | — | Nový, Řeší se ⁴ | — | — | — |
| Přiřadit řešitele | — | — | — | ✓ ¹ | — |
| Přiřadit obchodníka | — | — | — | ✓ ¹ | — |
| Vyřešit tiket | — | přiřazený | — | ✓ ¹ | — |
| Zamítnout tiket | — | — | — | ✓ ¹ | — |
| Znovu otevřít tiket | — | — | — | ✓ ¹ | — |
| **Statistiky** | | | | | |
| Vidí vlastní statistiky | — | ✓ | — | — | — |
| Vidí statistiky všech uživatelů a firem | — | — | — | ✓ ¹ | — |
| **Administrace** | | | | | |
| Spravovat uživatele a jejich role | — | — | — | — | ✓ |
| Spravovat firmy | — | — | — | — | ✓ |
| Spravovat oblasti | — | — | — | — | ✓ |
| Nastavit omezení správcům (oblasti, firmy) | — | — | — | — | ✓ |
| Nastavit oblasti řešitelům | — | — | — | — | ✓ |
| Nastavit rozsah viditelnosti žadatelům | — | — | — | — | ✓ |
| Spravovat kategorie práce | — | — | — | — | ✓ |

¹ V rámci nastaveného omezení oblasti a firem správce (pokud není omezení nastaveno, platí pro všechny tikety).

² Nelze v uzamčeném stavu — „Vyřešeno" nebo „Zamítnuto".

³ Správce smí zapisovat čas průběžně pouze tehdy, je-li k danému tiketu zároveň přiřazen jako řešitel nebo obchodník.

⁴ Řešitel vidí (a může převzít) nové tikety v rámci svých oblastí (nebo všechny, pokud nemá omezení), ale komentovat je může až po přiřazení. Přiřazené tikety vidí vždy bez ohledu na oblast. Převzít lze i tiket ve stavu „Řeší se" — v takovém případě se změní pouze přiřazený řešitel, stav zůstane.

⁵ Žadatel může komentovat vlastní tiket i ve stavu „Vyřešeno" nebo „Zamítnuto" (může nesouhlasit s uzavřením). Řešitel a obchodník komentovat uzavřený tiket nemohou. Správce uzavřený tiket komentovat může (může reagovat nebo tiket znovu otevřít).

⁶ Rozsah viditelnosti žadatele nastavuje administrátor per-uživatel: (a) pouze vlastní tikety, (b) všechny tikety firmy, (c) tikety firmy v konkrétních oblastech (vlastní tikety jsou vždy viditelné). Právo komentovat má žadatel vždy jen u tiketů, které sám založil.

## Požadavky

Požadavky zakládá žadatel a musí vyplnit

- Typ požadavku

- Název

- Popis

- Oblast (výběr z administrátorem definovaných oblastí)

- Prioritu (Vysoká, Střední, Nízká)

Požadavek může žadatel založit i odesláním na předdefinovanou e-mailovou
adresu. V takovém případě se požadavek založí následovně:

- Typ požadavku = Hlášení problému

- Název = Předmět e-mailu

- Popis = Tělo e-mailu (plain text)

- Oblast = oblast označená jako neznámá (pokud existuje)

- Priorita = Střední

- Přílohy = soubory přiložené k e-mailu jsou uloženy jako přílohy tiketu
  (stejná pravidla jako při ručním nahrání: povolené typy, max 5 MB;
  soubory s nepovolenou příponou nebo překračující limit jsou přeskočeny)

E-mail zpracuje pouze systém, pokud odesílatel odpovídá aktivnímu
uživateli s rolí Žadatel. Neznámí odesílatelé jsou ignorováni.

Ochrana proti zneužití:

- Deduplikace — každý e-mail je identifikován hlavičkou Message-ID;
  e-mail se stejným Message-ID je zpracován pouze jednou (TTL 30 dní).

- Rate limiting — jeden žadatel může prostřednictvím e-mailu vytvořit
  nejvýše 10 tiketů za hodinu; další e-maily jsou v daném okně ignorovány.

### Automatické zamítací odpovědi

Pokud systém e-mail zamítne a odesílatel je rozpoznán jako registrovaný
uživatel, odešle mu systém automatickou odpověď s důvodem zamítnutí.
Neznámým odesílatelům se odpověď neposílá (ochrana před backscatter
spamem).

| Důvod zamítnutí | Komu se odpověď posílá |
|---|---|
| Uživatel nemá roli Žadatel (zakládání tiketu) | Registrovaný uživatel s jinou rolí |
| Překročen rate limit | Registrovaný uživatel — pouze první zamítnutí v hodinovém okně; další jsou ignorována, aby nedošlo k zahlcení e-maily |
| Tiket z tokenu neexistuje (odpověď) | Odesílatel odpovědi |
| Nedostatečná oprávnění ke komentáři (odpověď) | Odesílatel odpovědi |
| Prázdné tělo zprávy po odebrání citace (odpověď) | Odesílatel odpovědi |
| Nekonzistentní token — jiné ID v předmětu a těle | Registrovaný uživatel |
| Neznámý odesílatel | — (tiché ignorování) |

### Odpověď na notifikaci → komentář (reply-to-ticket)

Každý odchozí notifikační e-mail obsahuje v předmětu i těle token ve
tvaru `[#42#]` (číslo tiketu). Odesílatel může na notifikaci odpovědět
a systém odpověď automaticky přidá jako komentář k danému tiketu.

Pravidla zpracování příchozí odpovědi:

- Token `[#42#]` je hledán v předmětu i těle e-mailu (plain text).
  Pokud je přítomen v obou a čísla se liší, e-mail je ignorován.

- Odesílatel musí být libovolný aktivní uživatel systému (nejen Žadatel).

- Platí stejná oprávnění jako při komentování na webu — viz sekci
  Komentáře níže.

- Z těla odpovědi je automaticky odstraněn citovaný text (quoted reply),
  komentář obsahuje pouze nový obsah.

- Přílohy jsou uloženy jako přílohy tiketu (stejná pravidla jako jiné
  přílohy z e-mailu).

- Rate limiting je sdílený s vytváříním tiketů (10 e-mailových akcí/hod
  na odesílatele).

- Po přidání komentáře se odešle standardní notifikace o novém komentáři.

Požadavky mohu být typu

- Hlášení problému

  - Hotline problém, nefakturuje se

  - Stavy

    - Nový, Řeší se, Vyřešeno, Zamítnuto

  - Přechody mezi stavy

    - Založení požadavku: Nový

    - Přiřazení řešitele: Nový -> Řeší se

    - Vyřešení: Řeší se -> Vyřešeno (musí se zadat způsob vyřešení a
      spotřebovaný čas)

    - Zamítnutí: jakýkoliv stav -> Zamítnuto

- Požadavek na vývoj

  - Fakturovaný požadavek

  - Může k němu být přiřazen Obchodník, pokud je potřeba

  - Stavy

    - Nový, Příprava nabídky, Řeší se, Vyřešeno, Zamítnuto

  - Přechody mezi stavy

    - Založení požadavku: Nový

    - Přiřazení obchodníka: Nový -> Příprava nabídky

    - Přiřazení řešitele: Nový nebo Příprava nabídky -> Řeší se

    - Vyřešení: Řeší se -> Vyřešeno (musí se zadat způsob vyřešení a
      spotřebovaný čas)

    - Zamítnutí: jakýkoliv stav -> Zamítnuto

- Námět na zlepšení

  - Odkladiště nápadů, je potřeba jej změnit na jeden z předchozích typů,
    aby bylo možné jej vyřešit

  - Stavy

    - Nový, Zamítnuto

  - Přechody mezi stavy

    - Založení požadavku: Nový

    - Zamítnutí: jakýkoliv stav -> Zamítnuto

Když se změní typ požadavku zůstane ve stejném stavu. Pokud cílový typ
nemá stejný stav, nastaví se „Nový".

Ve stavech „Řeší se" nebo „Příprava nabídky" je možné změnit řešitele a
obchodníka bez změny stavu.

Ve stavech „Vyřešeno" a „Zamítnuto" není možné dělat změny, pouze přesun
do stavu „Řeší se" nebo „Příprava nabídky". Při znovuotevření se způsob
vyřešení nebo důvod zamítnutí automaticky přepíše do komentáře (autorem
komentáře je správce provádějící akci) a pole se vymažou.

### Přílohy

K požadavku lze přikládat soubory. Přílohy může přidávat žadatel (ke svému požadavku), přiřazený řešitel, přiřazený obchodník, správce (v rámci svého omezení) a administrátor. Přílohu může smazat ten, kdo ji nahrál, nebo správce/administrátor.

Povolené typy souborů: PDF, obrázky (PNG, JPG, GIF, BMP, WEBP), dokumenty Office (DOCX, XLSX, XLS, PPTX, PPT, ODT, ODS), textové soubory (TXT, CSV, LOG, XML, JSON) a archivy (ZIP, 7Z). Maximální velikost jednoho souboru je 5 MB.

Soubory jsou dostupné ke stažení pouze přihlášeným uživatelům s přístupem k danému požadavku — přímý přístup přes URL je zakázán.

### Historie změn

Každý požadavek má auditní log všech změn. Zaznamenávají se tyto události:

- Vytvoření požadavku
- Změna stavu, typu, priority, oblasti, názvu
- Změna řešitele nebo obchodníka
- Úprava popisu (zaznamenává se i původní znění)
- Přidání nebo smazání přílohy

Každý záznam obsahuje: popis změny, autora změny a čas. Záznamy jsou řazeny od nejnovějšího.

Historie změn je viditelná všem uživatelům s přístupem k danému požadavku, s výjimkou interních záznamů (záznamy hodin), které žadatel nevidí.

### Zápis času

Čas může průběžně zapisovat řešitel, obchodník a správce (pokud je
zároveň přiřazen jako řešitel nebo obchodník). Záznamy jsou viditelné
řešiteli, obchodníkovi a správci; žadatel čas nevidí.

Při vyřešení požadavku je pole „Hodiny" povinné, pokud k požadavku dosud
neexistuje žádný záznam času. Pokud již záznamy existují, pole je
volitelné.

### Kategorie práce

Každý tiket může mít přiřazenu interní kategorii práce (např. instalace
kabeláže, vývoj, implementace, analýza, konfigurace HW). Kategorie je
interní — žadatel ji nevidí ani v detailu, ani v přehledu.

Kategorii může nastavit přiřazený řešitel nebo správce (v rámci svého
omezení). Kategorie jsou vázány na oblasti — při editaci tiketu se
zobrazí pouze kategorie přiřazené k oblasti daného tiketu; pokud oblast
tiketu nemá přiřazeny žádné kategorie, zobrazí se všechny.

Správa kategorií (přidávání, úprava) je dostupná pouze administrátorovi
přes webové rozhraní. Každá kategorie má název a seznam oblastí, ke
kterým patří. Administrátor může přiřadit kategorie oblasti také přímo
z formuláře editace oblasti.

### Notifikace

| Událost | Příjemci | Obsah e-mailu |
|---------|----------|---------------|
| Vytvořen nový požadavek | Žadatel + oprávnění správci ¹ | Typ, Název, Popis, Oblast, Priorita |
| Stav změněn na „Řeší se" | Žadatel | Název, nový stav |
| Stav změněn na „Příprava nabídky" | Žadatel | Název, nový stav |
| Přiřazen řešitel | Řešitel | Název tiketu |
| Přiřazen obchodník | Obchodník | Název tiketu |
| Přidán komentář | Všichni přiřazení (žadatel, řešitel, obchodník) kromě autora komentáře | Název, text komentáře |
| Požadavek vyřešen | Žadatel | Název, stav „Vyřešeno", způsob vyřešení |
| Požadavek zamítnut | Žadatel | Název, stav „Zamítnuto", důvod zamítnutí |
| Výzva k hodnocení po vyřešení | Žadatel (samostatný e-mail) | Klikatelné hvězdičky 0–5 s jednorázovými odkazy |

¹ **Výběr oprávněných správců** se řídí jejich omezeními oblastí a firem:

- Správce bez omezení dostane notifikaci vždy.
- Správce s omezením oblastí dostane notifikaci pouze o požadavcích
  jedné z jeho oblastí. Požadavky s oblastí označenou jako neznámou
  nebo bez oblasti oblast-filtr přeskočí (rozhoduje pouze omezení firem).
- Správce s omezením firem dostane notifikaci pouze o požadavcích
  daných firem.
- Správce s oběma omezeními musí požadavek splňovat zároveň jednu
  z oblastí i jednu z firem.

### Hodnocení spokojenosti

Po vyřešení tiketu obdrží žadatel samostatný e-mail s výzvou k hodnocení.
E-mail obsahuje klikatelné hvězdičky (0–5), každá hvězdička je jednorázový
odkaz — kliknutím se hodnocení okamžitě uloží bez nutnosti přihlášení.
Po kliknutí se zobrazí stránka s potvrzením hodnocení a volitelným polem
pro textový komentář (nepovinný, max. 2 000 znaků). Komentář se odesílá
samostatným tlačítkem a je zabezpečen vlastním jednorázovým tokenem.
Pokud žadatel stránku zavře bez odeslání komentáře, hodnocení zůstane uloženo.

Pravidla hodnocení:

- Hodnotit lze pouze tikety ve stavu „Vyřešeno" (nikoliv „Zamítnuto").
- Každý tiket lze hodnotit právě jednou — odkaz je po použití neplatný.
- Komentář k hodnocení lze přidat právě jednou (druhý token je po odeslání zneplatněn).
- Při znovuotevření tiketu se hodnocení i komentář resetují; po novém vyřešení
  přijde žadateli nová výzva.
- Hodnotící e-mail je odesílán výhradně žadateli tiketu, bez ohledu
  na případné další příjemce uzavíracích notifikací.
- Odkaz je zabezpečen jednorázovým UUID tokenem; neplatný nebo již
  použitý odkaz zobrazí srozumitelnou chybovou stránku.

Hodnocení a komentář jsou viditelné v detailu tiketu (sidebar) a hodnocení
ve statistikách:

- **Řešitel** vidí své průměrné hodnocení za zvolený měsíc.
- **Správce** vidí průměrné hodnocení každého řešitele za zvolený měsíc.

## Přehled požadavků

Každý uživatel vidí pouze požadavky, ke kterým má přístup (viz role).

Přehled obsahuje sloupce: #, Název, Typ, Stav, Priorita, Firma, Vytvořeno.
Správce navíc vidí sloupec Řešitel. Řešitel, obchodník a správce vidí
sloupec Hodiny (součet všech zaznamenaných hodin k danému požadavku).

### Filtry

Všichni uživatelé mohou filtrovat podle: Stav, Typ, Oblast, Priorita,
a textového vyhledávání v názvu a popisu.

Filtr data vytvoření funguje jako rozsah: pole „Vytvořeno od" omezuje
výsledky na tikety vytvořené v daný den nebo později, pole „Vytvořeno do"
na tikety vytvořené v daný den nebo dříve. Obě pole jsou volitelná
a nezávislá — lze zadat jen jedno z nich (filtr od, filtr do) nebo obě
najednou pro přesný rozsah.

Správce a administrátor mohou navíc filtrovat podle: Firma, Žadatel,
Řešitel.

### Export do Excelu

Z přehledu požadavků lze exportovat aktuálně zobrazené tikety (včetně
aplikovaných filtrů) do souboru XLSX. Export respektuje stejná pravidla
viditelnosti jako přehled — každý uživatel exportuje pouze tikety,
ke kterým má přístup.

Sloupce exportu: #, Název, Typ, Stav, Priorita, Oblast, Firma, Žadatel,
Vytvořeno. Správce a administrátor mají navíc sloupec Řešitel. Řešitel,
obchodník a správce mají navíc sloupec Hodiny.

### Navigace v detailu požadavku

V detailu požadavku jsou zobrazeny šipky pro přechod na předchozí a
následující požadavek. Pořadí odpovídá pořadí v přehledu (dle PK).
Uživatel může přejít pouze na požadavek, ke kterému má přístup.
