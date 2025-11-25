# -*- coding: utf-8 -*-
"""
Hot Pepper Beauty salon scraper
"""

import logging
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class HPBScraper:
    """
    Scraper for Hot Pepper Beauty salon pages
    """

    def __init__(self):
        """Initialize HPB scraper"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def scrape_salon_info(self, salon_url: str) -> Dict[str, Any]:
        """
        Scrape salon information from HPB page

        Args:
            salon_url: URL of the salon page (e.g., https://beauty.hotpepper.jp/slnH000232182/)

        Returns:
            Dictionary containing salon information

        Raises:
            Exception: If scraping fails
        """
        try:
            logger.info(f"Scraping HPB salon info from: {salon_url}")

            # Fetch page
            response = self.session.get(salon_url, timeout=30)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'lxml')

            # Extract salon information
            salon_info = {
                'url': salon_url,
                'name': self._extract_salon_name(soup),
                'description': self._extract_description(soup),
                'address': self._extract_address(soup),
                'access': self._extract_access(soup),
                'images': self._extract_images(soup, salon_url),
                'styles': self._extract_styles(soup, salon_url),
            }

            logger.info(f"Successfully scraped salon: {salon_info['name']}")
            return salon_info

        except requests.RequestException as e:
            logger.error(f"Failed to fetch HPB page: {e}")
            raise Exception(f"HPB scraping failed: {str(e)}")

        except Exception as e:
            logger.error(f"HPB scraping error: {e}")
            raise Exception(f"HPB scraping failed: {str(e)}")

    def _extract_salon_name(self, soup: BeautifulSoup) -> str:
        """Extract salon name"""
        try:
            # Try multiple selectors for salon name
            name_elem = (
                soup.select_one('h1.slnName') or
                soup.select_one('.slnHeader h1') or
                soup.select_one('h1[itemprop="name"]')
            )

            if name_elem:
                return name_elem.get_text(strip=True)

            logger.warning("Salon name not found")
            return "Salon Name Not Found"

        except Exception as e:
            logger.error(f"Error extracting salon name: {e}")
            return "Salon Name Not Found"

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract salon description/concept"""
        try:
            # Try to find concept or description
            desc_elem = (
                soup.select_one('.salonConcept') or
                soup.select_one('.salonInfo') or
                soup.select_one('[itemprop="description"]')
            )

            if desc_elem:
                return desc_elem.get_text(strip=True)

            logger.warning("Salon description not found")
            return ""

        except Exception as e:
            logger.error(f"Error extracting description: {e}")
            return ""

    def _extract_address(self, soup: BeautifulSoup) -> str:
        """Extract salon address"""
        try:
            address_elem = (
                soup.select_one('[itemprop="address"]') or
                soup.select_one('.slnAddr')
            )

            if address_elem:
                return address_elem.get_text(strip=True)

            logger.warning("Address not found")
            return ""

        except Exception as e:
            logger.error(f"Error extracting address: {e}")
            return ""

    def _extract_access(self, soup: BeautifulSoup) -> str:
        """Extract access/directions information"""
        try:
            access_elem = soup.select_one('.slnAccess')

            if access_elem:
                return access_elem.get_text(strip=True)

            logger.warning("Access info not found")
            return ""

        except Exception as e:
            logger.error(f"Error extracting access: {e}")
            return ""

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> list:
        """Extract salon images"""
        try:
            images = []
            img_elements = soup.select('.slnPhoto img, .galleryPhoto img')

            for img in img_elements[:10]:  # Limit to 10 images
                src = img.get('src') or img.get('data-src')
                if src:
                    # Convert relative URLs to absolute
                    full_url = urljoin(base_url, src)
                    images.append(full_url)

            logger.info(f"Found {len(images)} salon images")
            return images

        except Exception as e:
            logger.error(f"Error extracting images: {e}")
            return []

    def _extract_styles(self, soup: BeautifulSoup, base_url: str) -> list:
        """Extract style images and descriptions"""
        try:
            styles = []
            style_elements = soup.select('.stylePhoto')

            for style_elem in style_elements[:10]:  # Limit to 10 styles
                img = style_elem.select_one('img')
                desc = style_elem.select_one('.styleComment')

                if img:
                    src = img.get('src') or img.get('data-src')
                    if src:
                        style_info = {
                            'image_url': urljoin(base_url, src),
                            'description': desc.get_text(strip=True) if desc else '',
                        }
                        styles.append(style_info)

            logger.info(f"Found {len(styles)} hair styles")
            return styles

        except Exception as e:
            logger.error(f"Error extracting styles: {e}")
            return []

    def close(self):
        """Close the session"""
        self.session.close()
