# Volební scraper 2017

## Popis projektu

Tento projekt slouží k extrahování výsledků voleb do Poslanecké sněmovny Parlamentu ČR z roku 2017 z webu `volby.cz`.

Program stáhne výsledky pro zvolený územní celek. Každý řádek výsledného CSV souboru představuje jednu obec a obsahuje:

1. kód obce,
2. název obce,
3. počet voličů v seznamu,
4. počet vydaných obálek,
5. počet platných hlasů,
6. počty hlasů pro jednotlivé kandidující strany.

## Obsah projektu

- `projekt_3.py` – hlavní Python skript,
- `requirements.txt` – seznam použitých knihoven,
- `README.md` – dokumentace projektu,
- `vysledky_prostejov.csv` – ukázkový výstup pro okres Prostějov.

## Instalace knihoven

Doporučený postup je vytvořit si nové virtuální prostředí.

### Windows

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Spuštění projektu

Program se spouští pomocí dvou argumentů:

```bash
python projekt_3.py "<odkaz_na_uzemni_celek>" "<nazev_vystupniho_souboru.csv>"
```

První argument je odkaz na územní celek z webu `volby.cz`.  
Druhý argument je název CSV souboru, do kterého se uloží výsledky.

## Ukázka spuštění

Výsledky pro okres Prostějov:

```bash
python projekt_3.py "https://volby.cz/pls/ps2017nss/ps32?xjazyk=CZ&xkraj=12&xnumnuts=7103" "vysledky_prostejov.csv"
```

## Ukázka průběhu programu

```text
STAHUJI DATA Z VYBRANÉHO URL: https://volby.cz/pls/ps2017nss/ps32?xjazyk=CZ&xkraj=12&xnumnuts=7103
NALEZENO OBCÍ: 97
ZÍSKÁVÁM DATA Z URL: https://volby.cz/pls/ps2017nss/ps311?xjazyk=CZ&xkraj=12&xobec=506761&xvyber=7103
HOTOVO: 1/97 - Alojzov
...
UKLÁDÁM DO SOUBORU: vysledky_prostejov.csv
UKONČUJI projekt_3.py
```

## Ukázka výstupu

```text
code,location,registered,envelopes,valid,Občanská demokratická strana,...
506761,Alojzov,205,145,144,29,...
589268,Bedihošť,834,527,524,51,...
589276,Bílovice-Lutotín,279,279,275,13,...
```

## Ošetření chyb

Program kontroluje:

- jestli uživatel zadal přesně dva argumenty,
- jestli první argument vede na `volby.cz`,
- jestli URL obsahuje parametry územního celku,
- jestli druhý argument končí příponou `.csv`,
- jestli se stránku podařilo stáhnout,
- jestli se v HTML našla potřebná data.

Pokud je vstup špatně, program vypíše chybovou hlášku a nepokračuje.
