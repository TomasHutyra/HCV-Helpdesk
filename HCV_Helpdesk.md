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

  - Vidí pouze požadavky, které sám založil

  - Může komentovat požadavky, které založil

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

  - Může převzít požadavek ve stavu „Nový" — přiřadí se sám sobě
    a požadavek přejde do stavu „Řeší se"; převzít lze pouze tiket
    z oblasti, kterou řešitel spravuje (nebo neznámé oblasti)

  - Může změnit typ požadavku, prioritu, oblast a stav požadavku

  - Může průběžně zapisovat čas řešení

  - Může vyřešit požadavek -- při vyřešení požadavku musí zapsat způsob
    vyřešení a čas strávený řešením požadavku

  - Vidí své statistiky za období (měsíc) - kolik vyřešil požadavků,
    kolik jich má přiřazeno, jak dlouho trvá jeden požadavek, kolik času
    celkem strávil řešením požadavků, kolik má požadavků v jednotlivých
    stavech

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

  - Vidí veškeré statistiky za období (měsíc) -- statistiky uživatelů,
    přehledy pro jednotlivé firmy (počet požadavků, počet otevřených
    požadavků, čas strávený na požadavcích) v rámci svého omezení

- Administrátor

  - Zakládá nové uživatele

  - Přiřazuje role uživatelům

  - Zakládá firmy

  - Přiřazuje žadatele k firmám

  - Zakládá a spravuje oblasti (název, příznak „neznámá")

  - Nastavuje omezení správcům — seznam oblastí a/nebo firem přímo
    na stránce „Upravit uživatele" (pole se zobrazí pouze pokud má
    uživatel přiřazenu roli Správce)

  - Nastavuje oblasti řešitelům přímo na stránce „Upravit uživatele"
    (pole se zobrazí pouze pokud má uživatel přiřazenu roli Řešitel)

### Tabulka práv

| Funkce | Žadatel | Řešitel | Obchodník | Správce | Administrátor |
|--------|:-------:|:-------:|:---------:|:-------:|:-------------:|
| **Tikety — čtení** | | | | | |
| Vidí seznam tiketů | jen vlastní | přiřazené + všechny Nové ⁴ | jen přiřazené | všechny ¹ | všechny |
| Vidí detail tiketu | jen vlastní | přiřazený + každý Nový ⁴ | jen přiřazený | všechny ¹ | všechny |
| Vidí záznamy času a celkové hodiny | — | ✓ | ✓ | ✓ | — |
| **Tikety — vytvoření a editace** | | | | | |
| Vytvořit tiket | ✓ | — | — | ✓ | — |
| Editovat tiket (název, popis, typ, oblast, priorita) | — | přiřazený ² | — | ✓ ¹ ² | — |
| Změnit typ tiketu | — | přiřazený ² | — | ✓ ¹ ² | — |
| **Tikety — komentáře, čas a přílohy** | | | | | |
| Komentovat tiket | jen vlastní | přiřazený | přiřazený | ✓ ¹ | — |
| Zapsat čas | — | přiřazený | přiřazený | jen pokud přiřazen ³ | — |
| Přidat přílohu | jen vlastní | přiřazený | přiřazený | ✓ ¹ | — |
| Smazat přílohu | vlastní přílohy | vlastní přílohy | vlastní přílohy | ✓ ¹ | ✓ |
| **Tikety — akce** | | | | | |
| Převzít tiket (přiřadit se sám sobě) | — | Nový ⁴ | — | — | — |
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

¹ V rámci nastaveného omezení oblasti a firem správce (pokud není omezení nastaveno, platí pro všechny tikety).

² Nelze v uzamčeném stavu — „Vyřešeno" nebo „Zamítnuto".

³ Správce smí zapisovat čas průběžně pouze tehdy, je-li k danému tiketu zároveň přiřazen jako řešitel nebo obchodník.

⁴ Řešitel vidí (a může převzít) nové tikety v rámci svých oblastí (nebo všechny, pokud nemá omezení), ale komentovat je může až po přiřazení. Přiřazené tikety vidí vždy bez ohledu na oblast.

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
do stavu „Řeší se" nebo „Příprava nabídky".

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

¹ **Výběr oprávněných správců** se řídí jejich omezeními oblastí a firem:

- Správce bez omezení dostane notifikaci vždy.
- Správce s omezením oblastí dostane notifikaci pouze o požadavcích
  jedné z jeho oblastí. Požadavky s oblastí označenou jako neznámou
  nebo bez oblasti oblast-filtr přeskočí (rozhoduje pouze omezení firem).
- Správce s omezením firem dostane notifikaci pouze o požadavcích
  daných firem.
- Správce s oběma omezeními musí požadavek splňovat zároveň jednu
  z oblastí i jednu z firem.

## Přehled požadavků

Každý uživatel vidí pouze požadavky, ke kterým má přístup (viz role).

Přehled obsahuje sloupce: #, Název, Typ, Stav, Priorita, Firma, Vytvořeno.
Správce navíc vidí sloupec Řešitel. Řešitel, obchodník a správce vidí
sloupec Hodiny (součet všech zaznamenaných hodin k danému požadavku).

### Filtry

Všichni uživatelé mohou filtrovat podle: Stav, Typ, Oblast, Priorita,
Vytvořeno od, Vytvořeno do (výběr konkrétního data nebo rozsahu),
a textového vyhledávání v názvu a popisu.

Správce a administrátor mohou navíc filtrovat podle: Firma, Žadatel,
Řešitel.

### Navigace v detailu požadavku

V detailu požadavku jsou zobrazeny šipky pro přechod na předchozí a
následující požadavek. Pořadí odpovídá pořadí v přehledu (dle PK).
Uživatel může přejít pouze na požadavek, ke kterému má přístup.
