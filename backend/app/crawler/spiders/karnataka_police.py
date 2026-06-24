"""Karnataka State Police FIR spider.

Portal: https://ksp.karnataka.gov.in/
KSP has a cleaner portal structure — district selector, no CAPTCHA on public
search (verified as of 2024), JSON or HTML response.
Returns FIR summaries with direct PDF links.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Iterator

from bs4 import BeautifulSoup

from app.crawler.base import BaseSpider, FIRDocument

_BASE = "https://ksp.karnataka.gov.in"
_SEARCH_URL = f"{_BASE}/citizen/fir-search"
_WINDOW_DAYS = 8
_PAGE_SIZE = 25


class KarnatakaPoliceSpider(BaseSpider):
    state = "Karnataka"
    state_code = "KA"
    base_url = _BASE
    requires_captcha = False
    rate_limit_rps = 1.0

    districts = [
        "Bengaluru City", "Bengaluru District", "Mysuru",
        "Belagavi", "Mangaluru", "Hubballi-Dharwad",
    ]

    def crawl_district(self, district: str) -> Iterator[FIRDocument]:
        end = date.today()
        start = end - timedelta(days=_WINDOW_DAYS)
        offset = 0

        while True:
            firs, total = self._fetch_batch(district, start, end, offset)
            for fir in firs:
                yield fir
            offset += _PAGE_SIZE
            if offset >= total:
                break

    # ------------------------------------------------------------------

    def _fetch_batch(self, district: str, start: date, end: date, offset: int) -> tuple[list[FIRDocument], int]:
        params = {
            "district": district,
            "from": start.isoformat(),
            "to": end.isoformat(),
            "offset": offset,
            "limit": _PAGE_SIZE,
        }
        resp = self.get(_SEARCH_URL, params=params)

        content_type = resp.headers.get("content-type", "")
        if "json" in content_type:
            return self._parse_json(resp.json(), district)
        return self._parse_html(resp.text, district)

    # ------------------------------------------------------------------
    # Parsers
    # ------------------------------------------------------------------

    def _parse_json(self, data: dict, district: str) -> tuple[list[FIRDocument], int]:
        firs: list[FIRDocument] = []
        records = data.get("records", data.get("data", []))
        total = data.get("total", len(records))

        for rec in records:
            fir_number = rec.get("fir_no") or rec.get("firNumber", "")
            ps = rec.get("police_station") or rec.get("policeStation", "")
            year = rec.get("year", date.today().year)
            pdf_url = rec.get("pdf_url") or rec.get("pdfUrl", "")

            if not fir_number or not pdf_url:
                continue
            if not pdf_url.startswith("http"):
                pdf_url = f"{_BASE}{pdf_url}"

            try:
                doc = self.get(pdf_url)
                firs.append(FIRDocument(
                    state=self.state, state_code=self.state_code,
                    district=district, fir_number=str(fir_number), year=int(year),
                    content=doc.content, file_ext="pdf",
                    source_url=pdf_url, police_station=ps,
                ))
            except Exception as exc:
                self.logger.warning("KA: download %s failed: %s", fir_number, exc)

        return firs, int(total)

    def _parse_html(self, html: str, district: str) -> tuple[list[FIRDocument], int]:
        soup = BeautifulSoup(html, "html.parser")
        firs: list[FIRDocument] = []

        table = soup.find("table")
        if not table:
            return firs, 0

        rows = table.find_all("tr")[1:]
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue
            fir_number = cols[0].get_text(strip=True)
            ps = cols[1].get_text(strip=True) if len(cols) > 1 else ""
            link = row.find("a", href=re.compile(r"\.pdf", re.I))
            if not fir_number or not link:
                continue

            href = link["href"]
            url = href if href.startswith("http") else f"{_BASE}{href}"
            try:
                doc = self.get(url)
                firs.append(FIRDocument(
                    state=self.state, state_code=self.state_code,
                    district=district, fir_number=fir_number,
                    year=date.today().year,
                    content=doc.content, file_ext="pdf",
                    source_url=url, police_station=ps,
                ))
            except Exception as exc:
                self.logger.warning("KA: download %s failed: %s", fir_number, exc)

        # Try to extract total from a "Showing X of Y" text
        total_text = soup.get_text()
        m = re.search(r"of\s+(\d+)\s+results?", total_text, re.I)
        total = int(m.group(1)) if m else len(firs)
        return firs, total
