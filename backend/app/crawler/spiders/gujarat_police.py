"""Gujarat Police FIR spider.

Portal: https://police.gujarat.gov.in/  (also: gujhome.gujarat.gov.in)
Gujarat uses an ASP.NET WebForms portal with CAPTCHA.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Iterator

from bs4 import BeautifulSoup

from app.crawler.base import BaseSpider, FIRDocument
from app.crawler import captcha as captcha_mod

_BASE = "https://police.gujarat.gov.in"
_SEARCH_PATH = "/citizen/fir_search.aspx"
_CAPTCHA_PATH = "/captcha/captcha.aspx"
_WINDOW_DAYS = 8


class GujaratPoliceSpider(BaseSpider):
    state = "Gujarat"
    state_code = "GJ"
    base_url = _BASE
    requires_captcha = True
    rate_limit_rps = 0.8

    districts = [
        "Ahmedabad City", "Surat City", "Vadodara City", "Rajkot City",
    ]

    def crawl_district(self, district: str) -> Iterator[FIRDocument]:
        end = date.today()
        start = end - timedelta(days=_WINDOW_DAYS)
        page = 1
        while True:
            firs, has_next = self._fetch(district, start, end, page)
            for fir in firs:
                yield fir
            if not has_next:
                break
            page += 1

    def _fetch(self, district: str, start: date, end: date, page: int) -> tuple[list[FIRDocument], bool]:
        url = f"{_BASE}{_SEARCH_PATH}"
        resp = self.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        vs = self._h(soup, "__VIEWSTATE")
        ev = self._h(soup, "__EVENTVALIDATION")
        vsg = self._h(soup, "__VIEWSTATEGENERATOR")

        cap = self._captcha(url)
        if not cap:
            return [], False

        data = {
            "__VIEWSTATE": vs, "__EVENTVALIDATION": ev, "__VIEWSTATEGENERATOR": vsg,
            "ctl00$ContentPlaceHolder1$ddlDistrict": district,
            "ctl00$ContentPlaceHolder1$txtFrom": start.strftime("%d/%m/%Y"),
            "ctl00$ContentPlaceHolder1$txtTo": end.strftime("%d/%m/%Y"),
            "ctl00$ContentPlaceHolder1$txtCaptcha": cap,
            "ctl00$ContentPlaceHolder1$btnSearch": "Search",
        }
        if page > 1:
            data["ctl00$ContentPlaceHolder1$hfPage"] = str(page)

        resp = self.post(url, data=data)
        return self._parse(resp.text, district)

    def _captcha(self, ref: str) -> str | None:
        for _ in range(3):
            try:
                img = self.get(f"{_BASE}{_CAPTCHA_PATH}", headers={"Referer": ref})
                t = captcha_mod.solve(img.content)
                if t and len(t) >= 4:
                    return t
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
                self.logger.warning("GJ: %s failed: %s", fir_no, exc)

        has_next = bool(soup.find("a", string=re.compile(r"Next|»", re.I)))
        return firs, has_next

    @staticmethod
    def _h(soup: BeautifulSoup, name: str) -> str:
        tag = soup.find("input", {"name": name, "type": "hidden"})
        return tag["value"] if tag else ""
