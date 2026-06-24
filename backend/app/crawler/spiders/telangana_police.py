"""Telangana Police FIR spider.

Portals: Hyderabad (https://hcpd.gov.in/), Cyberabad, Rachakonda.
Each commissionerate has its own sub-portal.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Iterator

from bs4 import BeautifulSoup

from app.crawler.base import BaseSpider, FIRDocument

_PORTALS = {
    "Hyderabad": "https://hcpd.gov.in",
    "Cyberabad": "https://cyberabadpolice.gov.in",
    "Rachakonda": "https://rachakondapolice.gov.in",
}
_SEARCH_PATH = "/citizen/fir-search"
_WINDOW_DAYS = 8


class TelanganaPoliceSpider(BaseSpider):
    state = "Telangana"
    state_code = "TS"
    base_url = "https://tgpolice.gov.in"
    requires_captcha = False
    rate_limit_rps = 1.0

    districts = list(_PORTALS.keys())

    def crawl_district(self, district: str) -> Iterator[FIRDocument]:
        base = _PORTALS.get(district, self.base_url)
        end = date.today()
        start = end - timedelta(days=_WINDOW_DAYS)
        page = 1

        while True:
            firs, has_next = self._fetch(base, district, start, end, page)
            for fir in firs:
                yield fir
            if not has_next:
                break
            page += 1

    def _fetch(self, base: str, district: str, start: date, end: date, page: int) -> tuple[list[FIRDocument], bool]:
        params = {
            "fromDate": start.strftime("%d/%m/%Y"),
            "toDate": end.strftime("%d/%m/%Y"),
            "page": page,
        }
        resp = self.get(f"{base}{_SEARCH_PATH}", params=params)
        return self._parse(resp.text, base, district)

    def _parse(self, html: str, base: str, district: str) -> tuple[list[FIRDocument], bool]:
        soup = BeautifulSoup(html, "html.parser")
        firs: list[FIRDocument] = []

        for row in soup.select("table.fir-table tr, table tr")[1:]:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue
            fir_no = cols[0].get_text(strip=True)
            ps = cols[2].get_text(strip=True) if len(cols) > 2 else ""
            link = row.find("a", href=re.compile(r"\.pdf|fir", re.I))
            if not fir_no or not link:
                continue
            href = link["href"]
            url = href if href.startswith("http") else f"{base}{href}"
            try:
                doc = self.get(url)
                firs.append(FIRDocument(
                    state=self.state, state_code=self.state_code,
                    district=district, fir_number=fir_no,
                    year=date.today().year, content=doc.content,
                    file_ext="pdf", source_url=url, police_station=ps,
                ))
            except Exception as exc:
                self.logger.warning("TS/%s: %s failed: %s", district, fir_no, exc)

        has_next = bool(soup.find("a", string=re.compile(r"Next|»", re.I)))
        return firs, has_next
