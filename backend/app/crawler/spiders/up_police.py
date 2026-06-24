"""Uttar Pradesh Police FIR spider.

Portal: https://uppolice.gov.in/
Flow:
  1. GET search page → extract ASP.NET ViewState tokens
  2. GET CAPTCHA image → solve with EasyOCR (retry up to 3×)
  3. POST search form with district + 7-day date window
  4. Parse results table → collect PDF links
  5. GET each PDF → yield FIRDocument

UP has the highest FIR volume in India (~500k/year across 75 districts).
Rate limit: 1 req/s to stay under the radar.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Iterator

from bs4 import BeautifulSoup

from app.crawler.base import BaseSpider, FIRDocument
from app.crawler import captcha as captcha_mod

_BASE = "https://uppolice.gov.in"
_SEARCH_PATH = "/Pages/en/Citizen-Charter/FIR-Search.aspx"
_CAPTCHA_PATH = "/CaptchaImage.aspx"

# Sliding window: crawl the past 8 days on each weekly run so we never miss
# FIRs registered at week boundaries.
_WINDOW_DAYS = 8


class UPPoliceSpider(BaseSpider):
    state = "Uttar Pradesh"
    state_code = "UP"
    base_url = _BASE
    requires_captcha = True
    rate_limit_rps = 1.0

    districts = [
        "Lucknow", "Kanpur Nagar", "Agra", "Varanasi", "Prayagraj",
        "Gautam Buddha Nagar", "Ghaziabad", "Meerut", "Bareilly", "Gorakhpur",
    ]

    # ------------------------------------------------------------------
    # Main entry
    # ------------------------------------------------------------------

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
    # Page-level helpers
    # ------------------------------------------------------------------

    def _fetch_page(self, district: str, start: date, end: date, page: int) -> tuple[list[FIRDocument], bool]:
        search_url = f"{_BASE}{_SEARCH_PATH}"

        # Step 1 — load form, extract ViewState tokens
        resp = self.get(search_url)
        soup = BeautifulSoup(resp.text, "html.parser")
        viewstate = self._extract_hidden(soup, "__VIEWSTATE")
        vsg = self._extract_hidden(soup, "__VIEWSTATEGENERATOR")
        ev = self._extract_hidden(soup, "__EVENTVALIDATION")

        # Step 2 — solve CAPTCHA (up to 3 attempts)
        captcha_text = self._solve_captcha_with_retry(search_url)
        if not captcha_text:
            self.logger.warning("UP/%s: CAPTCHA unsolvable, skipping page %d", district, page)
            return [], False

        # Step 3 — POST search
        payload = {
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": vsg,
            "__EVENTVALIDATION": ev,
            "ctl00$ContentPlaceHolder1$ddlDistrict": district,
            "ctl00$ContentPlaceHolder1$txtFromDate": start.strftime("%d/%m/%Y"),
            "ctl00$ContentPlaceHolder1$txtToDate": end.strftime("%d/%m/%Y"),
            "ctl00$ContentPlaceHolder1$txtCaptcha": captcha_text,
            "ctl00$ContentPlaceHolder1$btnSearch": "Search",
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
        }
        if page > 1:
            payload["ctl00$ContentPlaceHolder1$GridView1$page"] = str(page)

        resp = self.post(search_url, data=payload)
        return self._parse_results(resp.text, district)

    def _solve_captcha_with_retry(self, referer_url: str, attempts: int = 3) -> str | None:
        captcha_url = f"{_BASE}{_CAPTCHA_PATH}"
        for attempt in range(attempts):
            try:
                img_resp = self.get(captcha_url, headers={"Referer": referer_url})
                text = captcha_mod.solve(img_resp.content)
                if text and len(text) >= 4:
                    return text
                self.logger.debug("UP: CAPTCHA attempt %d empty/short, retrying", attempt + 1)
            except Exception as exc:
                self.logger.debug("UP: CAPTCHA attempt %d failed: %s", attempt + 1, exc)
        return None

    def _parse_results(self, html: str, district: str) -> tuple[list[FIRDocument], bool]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", {"id": re.compile(r"GridView", re.I)})
        firs: list[FIRDocument] = []

        if not table:
            return firs, False

        rows = table.find_all("tr")[1:]   # skip header
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 4:
                continue
            fir_number = cols[0].get_text(strip=True)
            year_text = cols[1].get_text(strip=True)
            ps = cols[2].get_text(strip=True)
            pdf_link = row.find("a", href=re.compile(r"\.pdf", re.I))

            if not fir_number or not pdf_link:
                continue

            year = self._parse_year(year_text)
            href = pdf_link["href"]
            pdf_url = href if href.startswith("http") else f"{_BASE}{href}"

            try:
                pdf_resp = self.get(pdf_url)
                firs.append(FIRDocument(
                    state=self.state,
                    state_code=self.state_code,
                    district=district,
                    fir_number=fir_number,
                    year=year,
                    content=pdf_resp.content,
                    file_ext="pdf",
                    source_url=pdf_url,
                    police_station=ps,
                ))
            except Exception as exc:
                self.logger.warning("UP: could not download FIR %s: %s", fir_number, exc)

        # Check for next-page link
        next_btn = soup.find("a", string=re.compile(r"Next|»|>", re.I))
        has_next = next_btn is not None

        return firs, has_next

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_hidden(soup: BeautifulSoup, name: str) -> str:
        tag = soup.find("input", {"name": name, "type": "hidden"})
        return tag["value"] if tag else ""

    @staticmethod
    def _parse_year(text: str) -> int:
        m = re.search(r"\d{4}", text)
        return int(m.group()) if m else date.today().year
