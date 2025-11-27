# -*- coding: utf-8 -*-
"""
Hot Pepper Beauty salon scraper

要件定義書に基づき、スタイリスト情報とクーポン情報を取得する。
"""

import logging
import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin
from django.core.cache import cache

logger = logging.getLogger(__name__)

STYLIST_CACHE_TIMEOUT = 60 * 60 * 6  # 6 hours
COUPON_CACHE_TIMEOUT = 60 * 60 * 6   # 6 hours


class HPBScraper:
    """
    Scraper for Hot Pepper Beauty salon pages
    """

    def __init__(self):
        """Initialize HPB scraper"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
        })

    def _extract_salon_id(self, salon_url: str) -> Optional[str]:
        """
        Extract salon ID from URL

        Args:
            salon_url: Salon URL (e.g., https://beauty.hotpepper.jp/slnH000232182/)

        Returns:
            Salon ID (e.g., H000232182) or None if not found
        """
        match = re.search(r'(?:sln|slnH)(H\d+)', salon_url)
        if match:
            return match.group(1)
        return None

    def scrape_stylists(self, salon_url: str) -> List[Dict[str, str]]:
        """
        Scrape stylist information from HPB stylist page

        Args:
            salon_url: Base salon URL (e.g., https://beauty.hotpepper.jp/slnH000232182/)

        Returns:
            List of dictionaries containing stylist information:
            [
                {'stylist_id': 'T000123456', 'name': 'スタイリスト名'},
                ...
            ]

        Raises:
            Exception: If scraping fails
        """
        try:
            # Construct stylist page URL
            stylist_url = urljoin(salon_url.rstrip('/') + '/', 'stylist/')
            logger.info(f"Scraping stylist information from: {stylist_url}")

            # Fetch page
            response = self.session.get(stylist_url, timeout=30)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'lxml')

            # Extract stylist information
            stylists = []
            seen_ids = set()  # Track seen IDs to avoid duplicates
            stylist_id_pattern = re.compile(r'/stylist/([^/]+)/')

            # Find all stylist links
            all_links = soup.find_all('a', href=stylist_id_pattern)

            # First pass: collect links with names (parent is <p> tag)
            # These links contain the actual stylist names
            for link in all_links:
                # Links with parent <p> tag typically contain the actual name
                if link.parent and link.parent.name == 'p':
                    href = link.get('href', '')
                    match = stylist_id_pattern.search(href)
                    if match:
                        stylist_id = match.group(1)

                        # Skip if already seen
                        if stylist_id in seen_ids:
                            continue
                        seen_ids.add(stylist_id)

                        # Get stylist name from link text
                        stylist_name = link.get_text(strip=True)

                        stylists.append({
                            'stylist_id': stylist_id,
                            'name': stylist_name or f'スタイリスト {stylist_id}'
                        })

            # Second pass: collect any remaining stylists from table elements
            # (in case some stylists are only listed in tables)
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    for cell in cells:
                        links = cell.find_all('a', href=stylist_id_pattern)
                        for link in links:
                            href = link.get('href', '')
                            match = stylist_id_pattern.search(href)
                            if match:
                                stylist_id = match.group(1)

                                # Skip if already seen
                                if stylist_id in seen_ids:
                                    continue
                                seen_ids.add(stylist_id)

                                # Get stylist name
                                stylist_name = link.get_text(strip=True)
                                if not stylist_name and link.parent:
                                    stylist_name = link.parent.get_text(strip=True)

                                stylists.append({
                                    'stylist_id': stylist_id,
                                    'name': stylist_name or f'スタイリスト {stylist_id}'
                                })

            logger.info(f"Found {len(stylists)} stylists")
            return stylists

        except requests.RequestException as e:
            logger.error(f"Failed to fetch stylist page: {e}")
            raise Exception(f"Stylist scraping failed: {str(e)}")

        except Exception as e:
            logger.error(f"Stylist scraping error: {e}")
            raise Exception(f"Stylist scraping failed: {str(e)}")

    def _get_total_pages(self, soup: BeautifulSoup) -> int:
        """
        Extract total number of pages from pagination info

        Args:
            soup: BeautifulSoup object of the page

        Returns:
            Total number of pages (default: 1)
        """
        # Try multiple selectors for pagination info
        pagination_selectors = [
            '.preListHead div.fs10',
            '#mainContents div.pa.bottom0.right0',
        ]

        page_text = None

        for selector in pagination_selectors:
            elem = soup.select_one(selector)
            if elem:
                page_text = elem.get_text(strip=True)
                break

        # If not found with selectors, search by text pattern
        if not page_text:
            page_pattern = re.compile(r'\d+/\d+ページ')
            for elem in soup.find_all(string=page_pattern):
                page_text = elem.strip()
                break

        if page_text:
            # Extract page info: "Y/Zページ" or "全X件（Y/Zページ）"
            match = re.search(r'(\d+)/(\d+)ページ', page_text)
            if match:
                total_pages = int(match.group(2))
                logger.debug(f"Pagination info found: {page_text}, total pages: {total_pages}")
                return total_pages

        return 1

    def scrape_coupons(self, salon_url: str) -> List[str]:
        """
        Scrape coupon information from HPB coupon pages (all pages)

        Args:
            salon_url: Base salon URL (e.g., https://beauty.hotpepper.jp/slnH000232182/)

        Returns:
            List of coupon names (strings)

        Raises:
            Exception: If scraping fails
        """
        try:
            # Construct coupon page base URL
            coupon_base_url = urljoin(salon_url.rstrip('/') + '/', 'coupon/')
            logger.info(f"Scraping coupon information from: {coupon_base_url}")

            all_coupons = []
            seen_coupons = set()  # Track seen coupons to avoid duplicates

            # First, get page 1 to determine total pages
            first_page_url = coupon_base_url
            logger.debug(f"Fetching coupon page 1: {first_page_url}")

            response = self.session.get(first_page_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')

            # Get total pages
            total_pages = self._get_total_pages(soup)
            logger.info(f"Total coupon pages: {total_pages}")

            # Extract coupons from first page
            page_coupons = self._extract_coupons_from_page(soup)
            for coupon in page_coupons:
                if coupon not in seen_coupons:
                    seen_coupons.add(coupon)
                    all_coupons.append(coupon)

            logger.info(f"Found {len(page_coupons)} coupons on page 1")

            # Fetch remaining pages (2 to total_pages)
            for page in range(2, total_pages + 1):
                # HPB uses /coupon/PN{page}.html format for page 2 onwards
                page_url = f"{coupon_base_url}PN{page}.html"
                logger.debug(f"Fetching coupon page {page}: {page_url}")

                try:
                    response = self.session.get(page_url, timeout=30)
                    response.raise_for_status()

                    soup = BeautifulSoup(response.content, 'lxml')
                    page_coupons = self._extract_coupons_from_page(soup)

                    for coupon in page_coupons:
                        if coupon not in seen_coupons:
                            seen_coupons.add(coupon)
                            all_coupons.append(coupon)

                    logger.info(f"Found {len(page_coupons)} coupons on page {page}")

                except requests.RequestException as e:
                    logger.warning(f"Failed to fetch coupon page {page}: {e}")
                    break

            logger.info(f"Found total {len(all_coupons)} unique coupons across {total_pages} page(s)")
            return all_coupons

        except requests.RequestException as e:
            logger.error(f"Failed to fetch coupon page: {e}")
            raise Exception(f"Coupon scraping failed: {str(e)}")

        except Exception as e:
            logger.error(f"Coupon scraping error: {e}")
            raise Exception(f"Coupon scraping failed: {str(e)}")

    def _extract_coupons_from_page(self, soup: BeautifulSoup) -> List[str]:
        """
        Extract coupon names from a single page

        Args:
            soup: BeautifulSoup object of the coupon page

        Returns:
            List of coupon names found on the page
        """
        coupons = []

        # Try multiple selectors for coupon names (in order of priority)
        coupon_selectors = [
            'p.couponMenuName:not(.fl)',  # Primary: exclude floating elements
            'div.mT5.b > p.couponMenuName',  # Alternative layout 1
            '.bgLightOrange p.couponMenuName',  # Alternative layout 2 (in coupon container)
        ]

        for selector in coupon_selectors:
            elements = soup.select(selector)
            if elements:
                for elem in elements:
                    coupon_name = elem.get_text(strip=True)
                    if coupon_name and self._is_valid_coupon_name(coupon_name):
                        coupons.append(coupon_name)
                break  # Use first selector that finds elements

        # If no coupons found with specific selectors, try to find within coupon containers
        if not coupons:
            # Find coupon containers
            containers = soup.select('#mainContents > div.bgLightOrange, #mainContents > div.mT20 > div.bgLightOrange')
            for container in containers:
                coupon_elements = container.select('p.couponMenuName')
                for elem in coupon_elements:
                    coupon_name = elem.get_text(strip=True)
                    if coupon_name and self._is_valid_coupon_name(coupon_name):
                        coupons.append(coupon_name)

        return coupons

    def _is_valid_coupon_name(self, name: str) -> bool:
        """
        Check if a string is a valid coupon name

        Args:
            name: String to check

        Returns:
            True if valid coupon name, False otherwise
        """
        # Exclude common non-coupon strings
        invalid_patterns = [
            r'^次へ$',
            r'^前へ$',
            r'^\d+$',  # Just numbers (page numbers)
            r'^次の\d+件$',
            r'^前の\d+件$',
            r'^\d+/\d+ページ$',
            r'^クーポンメニュー$',  # Section header
            r'^初来店時クーポン$',  # Section header
            r'^2回目以降クーポン$',  # Section header
            r'^メニュー$',  # Section header
        ]

        for pattern in invalid_patterns:
            if re.match(pattern, name):
                return False

        # Coupon name should have reasonable length
        if len(name) < 2 or len(name) > 200:
            return False

        return True

    def close(self):
        """Close the session"""
        self.session.close()


# Module-level convenience functions (for compatibility with docs/technical_integration_guide.md)
def scrape_stylists(salon_url: str) -> List[Dict[str, str]]:
    """
    Scrape stylist information from HPB stylist page

    Args:
        salon_url: Base salon URL (e.g., https://beauty.hotpepper.jp/slnH000232182/)

    Returns:
        List of dictionaries containing stylist information:
        [
            {'stylist_id': 'T000123456', 'name': 'スタイリスト名'},
            ...
        ]
    """
    cache_key = f"hpb:stylists:{salon_url.rstrip('/')}"
    cached = cache.get(cache_key)
    if cached is not None:
        logger.info(f"Using cached stylists for {salon_url}")
        return cached

    scraper = HPBScraper()
    try:
        stylists = scraper.scrape_stylists(salon_url)
        cache.set(cache_key, stylists, timeout=STYLIST_CACHE_TIMEOUT)
        return stylists
    finally:
        scraper.close()


def scrape_coupons(salon_url: str) -> List[str]:
    """
    Scrape coupon information from HPB coupon pages (all pages)

    Args:
        salon_url: Base salon URL (e.g., https://beauty.hotpepper.jp/slnH000232182/)

    Returns:
        List of coupon names (strings)
    """
    cache_key = f"hpb:coupons:{salon_url.rstrip('/')}"
    cached = cache.get(cache_key)
    if cached is not None:
        logger.info(f"Using cached coupons for {salon_url}")
        return cached

    scraper = HPBScraper()
    try:
        coupons = scraper.scrape_coupons(salon_url)
        cache.set(cache_key, coupons, timeout=COUPON_CACHE_TIMEOUT)
        return coupons
    finally:
        scraper.close()
