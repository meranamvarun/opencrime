"""Delhi Police FIR spider.

Portal: https://delhipolice.gov.in/
Flow:
  1. GET citizen services page → discover district-wise FIR search URLs
  2. POST search per district with date range
  3. Parse table → download PDF for each FIR entry
  4. Pagination via page number param

Delhi has 15 districts under a single unified portal — no CAPTCHA on most
search endpoints (as of 2024), but may require a session cookie refresh.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Iterator

from bs4 import BeautifulSoup

from app.crawler.base import BaseSpider, FIRDocument

_BASE = "https://delhipolice.gov.in"
_SEARCH_URL = f"{_BASE}/citizen-services/fir-search"
_WINDOW_DAYS = 8
_PAGE_SIZE = 20


class DelhiPoliceSpider(BaseSpider):
    state = "Delhi"
    state_code = "DL"
    base_url = _BASE
    requires_captcha = False
    rate_limit_rps = 1.5       # Delhi portal is more stable

    # Delhi has 15 police districts; we cover the top 11 by crime volume
    districts = [
        "Central", "New Delhi", "North", "North East", "North West",
        "Outer", "Outer North", "South", "South East", "South West", "West",
    ]

    def crawl_district(self, district: str) -> Iterator[FIRDocument]:
        end = date.today()
        start = end - timedelta(days=_WINDOW_DAYS)
        page = 1

        while True:
            firs, total_pages = self._fetch_page(district, start, end, page)
            for fir in firs:
                yield fir
            if page >= total_pages:
                break
            page += 1

    # ------------------------------------------------------------------

    def _fetch_page(self, district: str, start: date, end: date, page: int) -> tuple[list[FIRDocument], int]:
        params = {
            "district": district,
            "from_date": start.strftime("%Y-%m-%d"),
            "to_date": end.strftime("%Y-%m-%d"),
            "page": page,
            "page_size": _PAGE_SIZE,
        }
        resp = self.get(_SEARCH_URL, params=params)
        return self._parse_results(resp.text, district)

    def _parse_results(self, html: str, district: str) -> tuple[list[FIRDocument], int]:
        soup = BeautifulSoup(html, "html.parser")
        firs: list[FIRDocument] = []

        table = soup.find("table", class_=re.compile(r"fir|result|data", re.I))
        if not table:
            return firs, 1

        rows = table.find_all("tr")[1:]
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue

            fir_number = cols[0].get_text(strip=True)
            ps = cols[1].get_text(strip=True) if len(cols) > 1 else ""
            link_tag = row.find("a", href=re.compile(r"\.(pdf|jpg|jpeg|png)", re.I))

            if not fir_number or not link_tag:
                continue

            href = link_tag["href"]
            doc_url = href if href.startswith("http") else f"{_BASE}{href}"
            ext = re.search(r"\.(pdf|jpg|jpeg|png)", doc_url, re.I)
            file_ext = ext.group(1).lower() if ext else "pdf"

            try:
                doc_resp = self.get(doc_url)
                firs.append(FIRDocument(
                    state=self.state,
                    state_code=self.state_code,
                    district=district,
                    fir_number=fir_number,
                    year=date.today().year,
                    content=doc_resp.content,
                    file_ext=file_ext,
                    source_url=doc_url,
                    police_station=ps,
                ))
            except Exception as exc:
                self.logger.warning("Delhi: download failed %s: %s", fir_number, exc)

        # Total pages from pagination element
        total_pages = self._extract_total_pages(soup)
        return firs, total_pages

    @staticmethod
    def _extract_total_pages(soup: BeautifulSoup) -> int:
        pager = soup.find(class_=re.compile(r"pagination|pager", re.I))
        if not pager:
            return 1
        pages = re.findall(r"\d+", pager.get_text())
        return max((int(p) for p in pages), default=1)
