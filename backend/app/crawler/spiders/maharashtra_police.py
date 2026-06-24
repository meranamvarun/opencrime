"""Maharashtra Police FIR spider.

Portal: https://mahapolice.gov.in/
Maharashtra uses e-FIR portal with district and police-station selectors.
Heavy CAPTCHA on search form (image CAPTCHA, 5–6 char alphanumeric).
Results returned as paginated HTML; each row has a PDF download link.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Iterator

from bs4 import BeautifulSoup

from app.crawler.base import BaseSpider, FIRDocument
from app.crawler import captcha as captcha_mod

_BASE = "https://mahapolice.gov.in"
_SEARCH_PATH = "/efir/fir_search.do"
_CAPTCHA_PATH = "/efir/captchaImage.do"
_WINDOW_DAYS = 8


class MaharashtraPoliceSpider(BaseSpider):
    state = "Maharashtra"
    state_code = "MH"
    base_url = _BASE
    requires_captcha = True
    rate_limit_rps = 0.8      # portal is slow, be gentle

    districts = [
        "Mumbai City", "Mumbai Suburban", "Pune City", "Nagpur City",
        "Thane", "Nashik", "Aurangabad", "Solapur",
    ]

    def crawl_district(self, district: str) -> Iterator[FIRDocument]:
        end = date.today()
        start = end - timedelta(days=_WINDOW_DAYS)
        page = 1

        while True:
            firs, has_next = self._fetch_page(district, start, end, page)
            for fir in firs:
                yield fir
            if not has_next:
                break
            page += 1

    # ------------------------------------------------------------------

    def _fetch_page(self, district: str, start: date, end: date, page: int) -> tuple[list[FIRDocument], bool]:
        search_url = f"{_BASE}{_SEARCH_PATH}"

        # Get session cookie + CSRF token
        resp = self.get(search_url)
        soup = BeautifulSoup(resp.text, "html.parser")
        token = self._extract_token(soup)

        captcha_text = self._solve_captcha(search_url)
        if not captcha_text:
            self.logger.warning("MH/%s: CAPTCHA unsolvable, skipping", district)
            return [], False

        payload = {
            "districtName": district,
            "fromDate": start.strftime("%d/%m/%Y"),
            "toDate": end.strftime("%d/%m/%Y"),
            "captchaText": captcha_text,
            "pageNo": page,
            "_token": token,
            "submit": "Search",
        }
        resp = self.post(search_url, data=payload)
        return self._parse(resp.text, district)

    def _solve_captcha(self, referer: str) -> str | None:
        for _ in range(3):
            try:
                img = self.get(f"{_BASE}{_CAPTCHA_PATH}", headers={"Referer": referer})
                text = captcha_mod.solve(img.content)
                if text and len(text) >= 4:
                    return text
            except Exception:
                pass
        return None

    def _parse(self, html: str, district: str) -> tuple[list[FIRDocument], bool]:
        soup = BeautifulSoup(html, "html.parser")
        firs: list[FIRDocument] = []

        rows = soup.select("table.fir-results tr, table#tblFIR tr")
        for row in rows[1:]:
            cols = row.find_all("td")
            if len(cols) < 4:
                continue
            fir_number = cols[0].get_text(strip=True)
            ps = cols[2].get_text(strip=True) if len(cols) > 2 else ""
            year_text = cols[3].get_text(strip=True) if len(cols) > 3 else ""
            year = self._parse_year(year_text)

            link = row.find("a", href=re.compile(r"download|pdf|fir", re.I))
            if not fir_number or not link:
                continue

            href = link["href"]
            url = href if href.startswith("http") else f"{_BASE}{href}"
            try:
                doc = self.get(url)
                firs.append(FIRDocument(
                    state=self.state, state_code=self.state_code,
                    district=district, fir_number=fir_number, year=year,
                    content=doc.content, file_ext="pdf",
                    source_url=url, police_station=ps,
                ))
            except Exception as exc:
                self.logger.warning("MH: download %s failed: %s", fir_number, exc)

        has_next = bool(soup.find("a", string=re.compile(r"Next|»", re.I)))
        return firs, has_next

    @staticmethod
    def _extract_token(soup: BeautifulSoup) -> str:
        tag = soup.find("input", {"name": re.compile(r"token|csrf", re.I)})
        return tag["value"] if tag else ""

    @staticmethod
    def _parse_year(text: str) -> int:
        m = re.search(r"\d{4}", text)
        return int(m.group()) if m else date.today().year
