"""
projekt_3.py: třetí projekt do Engeto Online Python Akademie

author: Michal Stefanov
email: michal8stefanov@gmail.com
discord: Majklik 232
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag


BASE_COLUMNS = ["code", "location", "registered", "envelopes", "valid"]
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}


class ScraperError(Exception):
    """Chyba, kterou program vypíše uživateli a poté bezpečně skončí."""


@dataclass(frozen=True)
class Municipality:
    """Základní údaje o obci z hlavní stránky okresu."""

    code: str
    name: str
    url: str


def clean_text(value: str) -> str:
    """Vyčistí text z HTML tabulky."""
    return value.replace("\xa0", " ").strip()


def clean_number(value: str) -> str:
    """Odstraní mezery používané v českém zápisu tisíců."""
    return clean_text(value).replace(" ", "")


def header_contains(tag: Tag, searched_header: str) -> bool:
    """Zjistí, jestli buňka tabulky obsahuje konkrétní hodnotu atributu headers."""
    headers = tag.get("headers", [])
    if isinstance(headers, str):
        headers = headers.split()
    return searched_header in headers


def validate_arguments(arguments: list[str]) -> tuple[str, Path]:
    """Zkontroluje počet a formát argumentů ze spuštění programu."""
    if len(arguments) != 2:
        raise ScraperError(
            "Program potřebuje právě 2 argumenty: "
            "1) URL územního celku, 2) název výstupního CSV souboru."
        )

    url = arguments[0].replace("&amp;", "&").strip()
    output_file = Path(arguments[1].strip())

    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)

    if not parsed_url.scheme.startswith("http"):
        raise ScraperError("První argument musí být platná URL adresa.")

    if "volby.cz" not in parsed_url.netloc:
        raise ScraperError("První argument musí odkazovat na web volby.cz.")

    if "ps32" not in parsed_url.path:
        raise ScraperError(
            "První argument musí být odkaz na územní celek, "
            "například stránka obsahující parametr ps32."
        )

    if "xkraj" not in query or "xnumnuts" not in query:
        raise ScraperError(
            "URL musí obsahovat parametry xkraj a xnumnuts "
            "(odkaz na konkrétní územní celek)."
        )

    if output_file.suffix.lower() != ".csv":
        raise ScraperError("Druhý argument musí být název souboru s příponou .csv.")

    return url, output_file


def fetch_soup(url: str) -> BeautifulSoup:
    """Stáhne HTML stránku a vrátí objekt BeautifulSoup."""
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ScraperError(f"Nepodařilo se stáhnout URL: {url}") from exc

    # Web volby.cz používá české kódování Windows-1250.
    response.encoding = "windows-1250"
    return BeautifulSoup(response.text, "html.parser")


def get_municipality_name(code_cell: Tag) -> str | None:
    """Najde název obce v řádku za buňkou s kódem obce."""
    name_cell = code_cell.find_next_sibling("td", class_="overflow_name")
    if name_cell is None:
        row = code_cell.find_parent("tr")
        if isinstance(row, Tag):
            name_cell = row.find("td", class_="overflow_name")

    if not isinstance(name_cell, Tag):
        return None

    return clean_text(name_cell.get_text(" ", strip=True))


def get_municipalities(main_soup: BeautifulSoup, main_url: str) -> list[Municipality]:
    """Z hlavní stránky okresu vytáhne kódy obcí, názvy obcí a detailní odkazy."""
    municipalities: list[Municipality] = []
    used_codes: set[str] = set()

    for link in main_soup.select("td.cislo a[href]"):
        code = clean_text(link.get_text(strip=True))
        href = link.get("href", "")

        if not code.isdigit() or "ps311" not in href:
            continue

        code_cell = link.find_parent("td")
        if not isinstance(code_cell, Tag):
            continue

        name = get_municipality_name(code_cell)
        if not name or code in used_codes:
            continue

        municipalities.append(
            Municipality(
                code=code,
                name=name,
                url=urljoin(main_url, href),
            )
        )
        used_codes.add(code)

    if not municipalities:
        raise ScraperError(
            "Na zadané stránce se nepodařilo najít žádné obce. "
            "Zkontroluj, že odkaz vede na výběr obce/okrsku."
        )

    return municipalities


def get_stat_value(soup: BeautifulSoup, header_name: str) -> str:
    """Z detailu obce získá číselnou hodnotu podle atributu headers."""
    cell = soup.find(
        "td",
        attrs={"headers": lambda value: value and header_name in str(value).split()},
    )

    if not isinstance(cell, Tag):
        raise ScraperError(f"Na detailní stránce chybí hodnota '{header_name}'.")

    return clean_number(cell.get_text(strip=True))


def get_basic_stats(soup: BeautifulSoup) -> list[str]:
    """Vrátí hodnoty: voliči v seznamu, vydané obálky, platné hlasy."""
    registered = get_stat_value(soup, "sa2")
    envelopes = get_stat_value(soup, "sa3")
    valid = get_stat_value(soup, "sa6")
    return [registered, envelopes, valid]


def get_party_results(soup: BeautifulSoup) -> dict[str, str]:
    """Z detailu obce získá názvy kandidujících stran a počet hlasů."""
    party_results: dict[str, str] = {}

    for name_cell in soup.find_all("td", class_="overflow_name"):
        if not isinstance(name_cell, Tag):
            continue

        # Názvy stran jsou v tabulkách s hlavičkou t1sb2/t2sb2.
        headers = " ".join(name_cell.get("headers", []))
        if "sb2" not in headers:
            continue

        party_name = clean_text(name_cell.get_text(" ", strip=True))
        votes_cell = name_cell.find_next_sibling("td", class_="cislo")

        if not party_name or not isinstance(votes_cell, Tag):
            continue

        party_results[party_name] = clean_number(votes_cell.get_text(strip=True))

    if not party_results:
        raise ScraperError("Na detailní stránce se nepodařilo najít výsledky stran.")

    return party_results


def scrape_results(municipalities: Iterable[Municipality]) -> tuple[list[str], list[list[str]]]:
    """Postupně stáhne všechny obce a připraví řádky pro CSV."""
    municipalities = list(municipalities)
    rows: list[list[str]] = []

    party_names: list[str] | None = None

    for index, municipality in enumerate(municipalities, start=1):
        print(f"ZÍSKÁVÁM DATA Z URL: {municipality.url}")
        detail_soup = fetch_soup(municipality.url)

        basic_stats = get_basic_stats(detail_soup)
        party_results = get_party_results(detail_soup)

        if party_names is None:
            party_names = list(party_results.keys())

        row = [
            municipality.code,
            municipality.name,
            *basic_stats,
            *[party_results.get(party, "0") for party in party_names],
        ]
        rows.append(row)

        print(f"HOTOVO: {index}/{len(municipalities)} - {municipality.name}")

    if party_names is None:
        raise ScraperError("Nepodařilo se získat názvy kandidujících stran.")

    return party_names, rows


def save_to_csv(output_file: Path, party_names: list[str], rows: list[list[str]]) -> None:
    """Uloží výsledky do CSV souboru."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(BASE_COLUMNS + party_names)
        writer.writerows(rows)


def main() -> None:
    """Hlavní běh programu."""
    try:
        url, output_file = validate_arguments(sys.argv[1:])

        print(f"STAHUJI DATA Z VYBRANÉHO URL: {url}")
        main_soup = fetch_soup(url)

        municipalities = get_municipalities(main_soup, url)
        print(f"NALEZENO OBCÍ: {len(municipalities)}")

        party_names, rows = scrape_results(municipalities)

        print(f"UKLÁDÁM DO SOUBORU: {output_file}")
        save_to_csv(output_file, party_names, rows)

        print("UKONČUJI projekt_3.py")
    except ScraperError as error:
        print(f"CHYBA: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
