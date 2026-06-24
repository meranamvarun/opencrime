"""Rajasthan Police FIR spider.

Portal: https://police.rajasthan.gov.in/
Uses citizen services portal — district + date range, CAPTCHA present.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Iterator

from bs4 import BeautifulSoup

from app.crawler.base import BaseSpider, FIRDocument
from app.crawler import captcha as captcha_mod

_BASE = "https://police.rajasthan.gov.in"
_SEARCH_PATH = "/citizen/fir-search.aspx"
_CAPTCHA_PATH = "/Handlers/CaptchaHandler.ashx"
_WINDOW_DAYS = 8


class RajasthanPoliceSpider(BaseSpider):
    state = "Rajasthan"
    state_code = "RJ"
    base_url = _BASE
    requires_captcha = True
    rate_limit_rps = 0.8

    districts = [
        "Jaipur", "Jodhpur", "Udaipur", "Kota", "Ajmer",
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

    def _fetch_page(self, district: str, start: date, end: date, page: int) -> tuple[list[FIRDocument], bool]:
        url = f"{_BASE}{_SEARCH_PATH}"
        resp = self.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        viewstate = self._hidden(soup, "__VIEWSTATE")
        ev = self._hidden(soup, "__EVENTVALIDATION")
        vsg = self._hidden(soup, "__VIEWSTATEGENERATOR")

        captcha_text = self._captcha(url)
        if not captcha_text:
            return [], False

        data = {
            "__VIEWSTATE": viewstate,
            "__EVENTVALIDATION": ev,
            "__VIEWSTATEGENERATOR": vsg,
            "ctl00$MainContent$ddlDistrict": district,
            "ctl00$MainContent$txtFromDate": start.strftime("%d/%m/%Y"),
            "ctl00$MainContent$txtToDate": end.strftime("%d/%m/%Y"),
            "ctl00$MainContent$txtCaptcha": captcha_text,
            "ctl00$MainContent$btnSearch": "Search",
        }
        if page > 1:
            data["ctl00$MainContent$hdnPage"] = str(page)

        resp = self.post(url, data=data)
        return self._parse(resp.text, district)

    def _captcha(self, referer: str) -> str | None:
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
        table = soup.find("table", id=re.compile(r"gv|grid|fir", re.I))
        if not table:
            return firs, False

        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue
            fir_number = cols[0].get_text(strip=True)
            ps = cols[1].get_text(strip=True) if len(cols) > 1 else ""
            link = row.find("a", href=re.compile(r"\.pdf|download", re.I))
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
                self.logger.warning("RJ: %s download failed: %s", fir_number, exc)

        has_next = bool(soup.find("a", string=re.compile(r"Next|»", re.I)))
        return firs, has_next

    @staticmethod
    def _hidden(soup: BeautifulSoup, name: str) -> str:
        tag = soup.find("input", {"name": name, "type": "hidden"})
        return tag["value"] if tag else ""
