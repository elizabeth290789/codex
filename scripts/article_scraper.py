#!/usr/bin/env python3
import argparse
import dataclasses
from datetime import datetime, timedelta, timezone
import sys
from typing import Iterable
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import xml.etree.ElementTree as ET


@dataclasses.dataclass
class Article:
    site: str
    title: str
    published_at: datetime
    url: str
    description: str


DEFAULT_SITES = [
    "https://adoric.com/blog/",
    "https://cxl.com/blog/category/cro-testing/",
    "https://epicgrowth.io/",
    "https://www.abtasty.com/experience-hub/search/?format=Article",
    "https://www.advance-metrics.com/de/category/conversion-optimization-de/",
    "https://vwo.com/blog/",
    "https://sitetuners.com/resources/case-studies/",
    "https://www.crazyegg.com/blog/",
    "https://www.invespcro.com/blog/",
    "https://monetate.com/resources/",
    "https://getuplift.co/blog/",
    "https://crometrics.com/articles/",
    "https://baymard.com/blog",
    "https://outgrow.co/blog/",
    "http://thisisdata.ru/",
    "https://medium.com/",
    "https://www.leadfeeder.com/blog/",
    "https://mindbox.ru/journal/cases",
    "https://econsultancy.com/articles/",
    "https://www.insiderintelligence.com/topics/industry/b2b",
    "https://neilpatel.com/blog/",
    "https://exp-platform.com/talks/",
    "https://ai.stanford.edu/~ronnyk/ronnyk-bib.html",
    "https://blog.hubspot.com/",
    "https://unbounce.com/resources/",
    "https://www.convert.com/blog/optimization/think-like-cro-pro-jon-crowder/",
    "https://growthrocks.com/blog/",
]


def parse_month(month: str) -> tuple[datetime, datetime]:
    start = datetime.strptime(month, "%Y-%m").replace(tzinfo=timezone.utc)
    next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return start, next_month


def normalize_domain(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.replace("www.", "")


def fetch_text(session: requests.Session, url: str) -> str | None:
    response = session.get(url, timeout=30)
    if response.status_code != 200:
        return None
    return response.text


def discover_sitemaps(session: requests.Session, base_url: str) -> list[str]:
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    robots_text = fetch_text(session, robots_url)
    sitemaps: list[str] = []
    if robots_text:
        for line in robots_text.splitlines():
            if line.lower().startswith("sitemap:"):
                sitemap_url = line.split(":", 1)[1].strip()
                if sitemap_url:
                    sitemaps.append(sitemap_url)
    if not sitemaps:
        sitemaps.append(f"{parsed.scheme}://{parsed.netloc}/sitemap.xml")
    return sitemaps


def strip_namespace(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def collect_sitemap_entries(
    session: requests.Session,
    sitemap_url: str,
    path_prefix: str,
) -> list[tuple[str, str | None]]:
    entries: list[tuple[str, str | None]] = []
    queue = [sitemap_url]
    seen = set()

    while queue:
        current = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        xml_text = fetch_text(session, current)
        if not xml_text:
            continue
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            continue

        root_tag = strip_namespace(root.tag)
        if root_tag == "sitemapindex":
            for child in root:
                if strip_namespace(child.tag) != "sitemap":
                    continue
                loc = child.findtext(".//{*}loc")
                if loc:
                    queue.append(loc.strip())
        elif root_tag == "urlset":
            for child in root:
                if strip_namespace(child.tag) != "url":
                    continue
                loc = child.findtext(".//{*}loc")
                if not loc:
                    continue
                loc = loc.strip()
                parsed_loc = urlparse(loc)
                if path_prefix and not parsed_loc.path.startswith(path_prefix):
                    continue
                lastmod = child.findtext(".//{*}lastmod")
                entries.append((loc, lastmod.strip() if lastmod else None))
    return entries


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = date_parser.parse(value)
    except (ValueError, TypeError):
        return None
    if not parsed.tzinfo:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def extract_description(soup: BeautifulSoup) -> str:
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return meta["content"].strip()
    paragraph = soup.find("p")
    if paragraph:
        return " ".join(paragraph.get_text(" ", strip=True).split())
    return ""


def shorten_description(text: str) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return ""
    sentences: list[str] = []
    buffer = ""
    for char in cleaned:
        buffer += char
        if char in ".!?":
            sentences.append(buffer.strip())
            buffer = ""
        if len(sentences) == 2:
            break
    if buffer and len(sentences) < 2:
        sentences.append(buffer.strip())
    return " ".join(sentence for sentence in sentences if sentence)


def extract_article_data(session: requests.Session, url: str) -> Article | None:
    html = fetch_text(session, url)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(" ", strip=True)
    if not title and soup.title:
        title = soup.title.get_text(" ", strip=True)

    published_at = None
    meta_time = soup.find("meta", property="article:published_time")
    if meta_time and meta_time.get("content"):
        published_at = parse_datetime(meta_time["content"])
    if not published_at:
        time_tag = soup.find("time")
        if time_tag:
            published_at = parse_datetime(time_tag.get("datetime") or time_tag.get_text(strip=True))

    description = shorten_description(extract_description(soup))

    if not (title and published_at):
        return None

    return Article(
        site=normalize_domain(url),
        title=title,
        published_at=published_at,
        url=url,
        description=description,
    )


def month_matches(date: datetime, start: datetime, end: datetime) -> bool:
    return start <= date < end


def month_tokens(month: str) -> set[str]:
    year, month_num = month.split("-")
    month_two = f"{int(month_num):02d}"
    return {
        f"/{year}/{month_two}",
        f"/{year}-{month_two}",
        f"/{year}/{int(month_num)}",
    }


def is_candidate_url(url: str, tokens: set[str]) -> bool:
    path = urlparse(url).path
    return any(token in path for token in tokens)


def collect_articles(
    session: requests.Session,
    site_url: str,
    month: str,
) -> list[Article]:
    parsed_site = urlparse(site_url)
    base_url = f"{parsed_site.scheme}://{parsed_site.netloc}"
    path_prefix = parsed_site.path.rstrip("/")
    start, end = parse_month(month)
    tokens = month_tokens(month)

    sitemap_urls = discover_sitemaps(session, base_url)
    entries: list[tuple[str, str | None]] = []
    for sitemap_url in sitemap_urls:
        entries.extend(collect_sitemap_entries(session, sitemap_url, path_prefix))

    articles: list[Article] = []
    seen_urls = set()
    for loc, lastmod in entries:
        if loc in seen_urls:
            continue
        seen_urls.add(loc)
        lastmod_date = parse_datetime(lastmod) if lastmod else None
        if lastmod_date and not month_matches(lastmod_date, start, end):
            continue
        if not lastmod_date and not is_candidate_url(loc, tokens):
            continue
        article = extract_article_data(session, loc)
        if not article:
            continue
        if month_matches(article.published_at, start, end):
            articles.append(article)

    return sorted(articles, key=lambda item: item.published_at)


def render_markdown(articles_by_site: dict[str, list[Article]], month: str) -> str:
    lines: list[str] = []
    for site, articles in articles_by_site.items():
        lines.append(f"## {site}")
        if not articles:
            lines.append(f"Нет статей за {month}.")
            lines.append("")
            continue
        lines.append("| Сайт | Название статьи | Дата публикации | Ссылка | Описание |")
        lines.append("| --- | --- | --- | --- | --- |")
        for article in articles:
            published = article.published_at.strftime("%d.%m.%Y")
            lines.append(
                "| {site} | {title} | {date} | {url} | {description} |".format(
                    site=article.site,
                    title=article.title.replace("|", "\\|"),
                    date=published,
                    url=article.url,
                    description=article.description.replace("|", "\\|"),
                )
            )
        lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Собирает список статей за выбранный месяц по сайтам.",
    )
    parser.add_argument(
        "--month",
        default=datetime.now(timezone.utc).strftime("%Y-%m"),
        help="Месяц в формате YYYY-MM (например, 2026-01).",
    )
    parser.add_argument(
        "--sites",
        nargs="*",
        default=DEFAULT_SITES,
        help="Список стартовых URL для блогов.",
    )
    parser.add_argument(
        "--output",
        help="Путь для сохранения Markdown-отчета.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    month = args.month
    articles_by_site: dict[str, list[Article]] = {}

    with requests.Session() as session:
        session.headers.update(
            {"User-Agent": "Mozilla/5.0 (compatible; ArticleScraper/1.0)"}
        )
        for site_url in args.sites:
            site_name = normalize_domain(site_url)
            articles_by_site[site_name] = collect_articles(session, site_url, month)

    output = render_markdown(articles_by_site, month)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(output)
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
