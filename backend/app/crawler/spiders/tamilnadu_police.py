"""Tamil Nadu Police FIR spider.

Portal: https://eservices.tnpolice.gov.in/
TN has a clean e-services portal with district-wise FIR search.
No CAPTCHA on public listing pages (as of 2024).
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Iterator

from bs4 import BeautifulSoup

from app.crawler.base import BaseSpider, FIRDocument

_BASE = "https://eservices.tnpolice.gov.in"
_SEARCH_URL = f"{_BASE}/CCTNSNICSDC/GetFirDetails"
_WINDOW_DAYS = 8


class TamilNaduPoliceSpider(BaseSpider):
    state = "Tamil Nadu"
    state_code = "TN"
    base_url = _BASE
    requires_captcha = False
    rate_limit_rps = 1.0

    districts = [
        "Chennai", "Coimbatore", "Madurai", "Salem", "Tiruchirappalli",
    ]

    def crawl_district(self, district: str) -> Iterator[FIRDocument]:
        end = date.today()
        start = end - timedelta(days=_WINDOW_DAYS)
        page_no = 1

        while True:
            firs, total_pages = self._fetch(district, start, end, page_no)
            for fir in firs:
                yield fir
            if page_no >= total_pages:
                break
            page_no += 1

    def _fetch(self, district: str, start: date, end: date, page: int) -> tuple[list[FIRDocument], int]:
        # TN portal uses a JSON API in some versions, form POST in others
        payload = {
            "districtName": district,
            "fromDate": start.strftime("%d-%m-%Y"),
            "toDate": end.strftime("%d-%m-%Y"),
            "pageIndex": page,
            "pageSize": 20,
        }
        resp = self.post(_SEARCH_URL, json=payload)
        ctype = resp.headers.get("content-type", "")

        if "json" in ctype:
            return self._from_json(resp.json(), district)
        return self._from_html(resp.text, district)

    def _from_json(self, data, district: str) -> tuple[list[FIRDocument], int]:
        firs: list[FIRDocument] = []
        items = data.get("firDetails", data.get("data", []))
        total = data.get("totalCount", len(items))
        page_size = 20
        total_pages = max(1, -(-total // page_size))

        for item in items:
            fir_no = item.get("firNumber", item.get("FIRNumber", ""))
            ps = item.get("policeStation", "")
            year = item.get("year", date.today().year)
            pdf = item.get("pdfUrl", item.get("documentUrl", ""))
            if not fir_no or not pdf:
                continue
            if not pdf.startswith("http"):
                pdf = f"{_BASE}{pdf}"
            try:
                doc = self.get(pdf)
                firs.append(FIRDocument(
                    state=self.state, state_code=self.state_code,
                    district=district, fir_number=str(fir_no), year=int(year),
                    content=doc.content, file_ext="pdf",
                    source_url=pdf, police_station=ps,
                ))
            except Exception as exc:
                self.logger.warning("TN: %s failed: %s", fir_no, exc)

        return firs, total_pages

    def _from_html(self, html: str, district: str) -> tuple[list[FIRDocument], int]:
        soup = BeautifulSoup(html, "html.parser")
        firs: list[FIRDocument] = []

        for row in soup.select("table tr")[1:]:
            cols = row.find_all("td")
            if len(cols) < 2:
                continue
            fir_no = cols[0].get_text(strip=True)
            ps = cols[1].get_text(strip=True) if len(cols) > 1 else ""
            link = row.find("a", href=re.compile(r"\.pdf|download", re.I))
            if not fir_no or not link:
                continue
            href = link["href"]
            url = href if href.startswith("http") else f"{_BASE}{href}"
            try:
                doc = self.get(url)
                firs.append(FIRDocument(
                    state=self.state, state_code=self.state_code,
                    district=district, fir_number=fir_no,
                    year=date.today().year, content=doc.content,
                    file_ext="pdf", source_url=url, police_station=ps,
                ))
            except Exception as exc:
                self.logger.warning("TN: %s download failed: %s", fir_no, exc)

        pager = soup.find(class_=re.compile(r"pag", re.I))
        pages = re.findall(r"\d+", pager.get_text()) if pager else []
        total_pages = max((int(p) for p in pages), default=1)
        return firs, total_pages
