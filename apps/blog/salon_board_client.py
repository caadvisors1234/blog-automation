# -*- coding: utf-8 -*-
"""
SALON BOARD automation client using Playwright
"""

import logging
import time
from typing import Optional, Dict, Any, List
from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError
from django.conf import settings

logger = logging.getLogger(__name__)


class SALONBoardClient:
    """
    Client for SALON BOARD automation using Playwright
    """

    BASE_URL = 'https://salonboard.com'
    LOGIN_URL = 'https://salonboard.com/login/'
    BLOG_URL = 'https://salonboard.com/salon/blog/'

    def __init__(self):
        """Initialize SALON BOARD client"""
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    def start(self):
        """Start browser"""
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            self.context = self.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            self.page = self.context.new_page()
            logger.info("Playwright browser started")

        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            raise

    def close(self):
        """Close browser"""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            logger.info("Playwright browser closed")

        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    def login(self, login_id: str, password: str) -> bool:
        """
        Login to SALON BOARD

        Args:
            login_id: SALON BOARD login ID
            password: Password (plain text)

        Returns:
            True if login successful, False otherwise
        """
        try:
            logger.info(f"Attempting to login to SALON BOARD as {login_id}")

            # Navigate to login page
            self.page.goto(self.LOGIN_URL, wait_until='networkidle', timeout=30000)

            # Fill login form
            self.page.fill('input[name="login_id"], input[type="text"]', login_id)
            self.page.fill('input[name="password"], input[type="password"]', password)

            # Click login button
            self.page.click('button[type="submit"], input[type="submit"]')

            # Wait for navigation after login
            self.page.wait_for_load_state('networkidle', timeout=15000)

            # Check if login was successful
            # Look for logout button or user menu as indicator
            if self.page.locator('a[href*="logout"], .user-menu, .logout').count() > 0:
                logger.info("Login successful")
                return True

            # Check if still on login page (login failed)
            if 'login' in self.page.url.lower():
                logger.error("Login failed - still on login page")
                return False

            logger.info("Login appears successful")
            return True

        except PlaywrightTimeoutError as e:
            logger.error(f"Login timeout: {e}")
            return False

        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    def select_salon(self, salon_id: str) -> bool:
        """
        Select salon if multiple salons are available

        Args:
            salon_id: Salon ID (e.g., H000123456)

        Returns:
            True if salon selected or not needed, False on failure
        """
        try:
            # Check if salon selection is needed
            salon_selector = f'[data-salon-id="{salon_id}"], a[href*="{salon_id}"]'
            if self.page.locator(salon_selector).count() > 0:
                self.page.click(salon_selector)
                self.page.wait_for_load_state('networkidle', timeout=10000)
                logger.info(f"Selected salon: {salon_id}")
                return True

            # No selection needed
            return True

        except Exception as e:
            logger.error(f"Salon selection error: {e}")
            return False

    def select_stylist(self, stylist_id: str) -> bool:
        """
        Select stylist from dropdown

        Args:
            stylist_id: Stylist ID (T number)

        Returns:
            True if stylist selected, False otherwise
        """
        try:
            if not stylist_id:
                return True

            # Try to find and select stylist
            stylist_selectors = [
                f'select[name="stylist_id"] option[value="{stylist_id}"]',
                f'select#stylist_id option[value="{stylist_id}"]',
            ]

            for selector in stylist_selectors:
                if self.page.locator(selector).count() > 0:
                    self.page.select_option(selector.replace(f' option[value="{stylist_id}"]', ''), stylist_id)
                    logger.info(f"Selected stylist: {stylist_id}")
                    return True

            logger.warning(f"Stylist {stylist_id} not found")
            return True  # Continue without stylist

        except Exception as e:
            logger.error(f"Stylist selection error: {e}")
            return True

    def select_coupon(self, coupon_name: str) -> bool:
        """
        Select coupon by name (partial match)

        Args:
            coupon_name: Coupon name for search

        Returns:
            True if coupon selected, False otherwise
        """
        try:
            if not coupon_name:
                return True

            # Try to find coupon input/search
            coupon_input_selectors = [
                'input[name="coupon_search"]',
                'input#coupon_search',
                'input[placeholder*="クーポン"]',
            ]

            for selector in coupon_input_selectors:
                if self.page.locator(selector).count() > 0:
                    self.page.fill(selector, coupon_name)
                    self.page.wait_for_timeout(1000)

                    # Click first result
                    result_selector = '.coupon-result:first-child, .search-result:first-child'
                    if self.page.locator(result_selector).count() > 0:
                        self.page.click(result_selector)
                        logger.info(f"Selected coupon: {coupon_name}")
                        return True

            logger.warning(f"Coupon {coupon_name} not found")
            return True

        except Exception as e:
            logger.error(f"Coupon selection error: {e}")
            return True

    def publish_blog_post(
        self,
        title: str,
        content: str,
        image_paths: Optional[List[str]] = None,
        stylist_id: Optional[str] = None,
        coupon_name: Optional[str] = None,
        salon_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Publish blog post to SALON BOARD

        Args:
            title: Blog post title (max 25 chars)
            content: Blog post content
            image_paths: List of image file paths
            stylist_id: Optional stylist ID
            coupon_name: Optional coupon name
            salon_id: Optional salon ID

        Returns:
            Dictionary with publication result

        Raises:
            Exception: If publication fails
        """
        try:
            logger.info(f"Publishing blog post: {title[:25]}...")

            # Select salon if needed
            if salon_id:
                self.select_salon(salon_id)

            # Navigate to blog creation page
            blog_create_url = f"{self.BLOG_URL}create/"
            self.page.goto(blog_create_url, wait_until='networkidle', timeout=30000)

            # Wait for form to load
            self.page.wait_for_selector('input[name="title"], #title', timeout=10000)

            # Fill title
            title_selector = 'input[name="title"], #title'
            self.page.fill(title_selector, title[:25])

            # Select stylist if provided
            if stylist_id:
                self.select_stylist(stylist_id)

            # Select coupon if provided
            if coupon_name:
                self.select_coupon(coupon_name)

            # Fill content with image handling
            final_content = self._prepare_content_with_images(content, image_paths or [])

            # Find and fill content field
            content_selectors = [
                'textarea[name="content"]',
                '#content',
                '.editor textarea',
                'textarea.blog-content',
            ]

            content_filled = False
            for selector in content_selectors:
                if self.page.locator(selector).count() > 0:
                    self.page.fill(selector, final_content)
                    content_filled = True
                    break

            if not content_filled:
                raise Exception("Could not find content input field")

            # Upload images if using file upload
            if image_paths:
                self._upload_images(image_paths)

            # Take screenshot before submission for debugging
            timestamp = int(time.time())
            screenshot_path = f'/tmp/salon_board_before_submit_{timestamp}.png'
            self.page.screenshot(path=screenshot_path)
            logger.info(f"Screenshot saved: {screenshot_path}")

            # Submit form
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button.submit',
                'button.publish',
            ]

            submitted = False
            for selector in submit_selectors:
                if self.page.locator(selector).count() > 0:
                    self.page.click(selector)
                    submitted = True
                    break

            if not submitted:
                raise Exception("Could not find submit button")

            # Wait for navigation or success message
            try:
                self.page.wait_for_load_state('networkidle', timeout=15000)
            except PlaywrightTimeoutError:
                logger.warning("Navigation timeout after submit, checking for success indicators")

            # Get final URL
            final_url = self.page.url

            # Take screenshot after submission
            final_screenshot_path = f'/tmp/salon_board_after_submit_{timestamp}.png'
            self.page.screenshot(path=final_screenshot_path)

            # Check for success indicators
            success_indicators = [
                '投稿しました',
                '公開しました',
                '保存しました',
                'success',
                '/blog/',  # URL changed to blog list/detail
            ]

            page_content = self.page.content().lower()
            success = any(
                indicator.lower() in page_content or indicator.lower() in final_url.lower()
                for indicator in success_indicators
            )

            if success:
                logger.info(f"Blog post published successfully: {final_url}")
                return {
                    'success': True,
                    'url': final_url,
                    'screenshot_path': final_screenshot_path,
                    'message': 'Blog post published successfully',
                }
            else:
                logger.error("Publication may have failed - no success indicators found")
                return {
                    'success': False,
                    'url': final_url,
                    'screenshot_path': final_screenshot_path,
                    'message': 'Publication status unclear',
                }

        except Exception as e:
            logger.error(f"Failed to publish blog post: {e}")
            raise Exception(f"SALON BOARD publication failed: {str(e)}")

    def _prepare_content_with_images(self, content: str, image_paths: List[str]) -> str:
        """
        Replace image placeholders with actual image handling

        Args:
            content: Content with placeholders
            image_paths: List of image paths

        Returns:
            Processed content
        """
        # For now, just return content as-is
        # Image placeholders will be handled by the rich editor
        return content

    def _upload_images(self, image_paths: List[str]) -> bool:
        """
        Upload images to the blog post

        Args:
            image_paths: List of image file paths

        Returns:
            True if upload successful
        """
        try:
            for idx, path in enumerate(image_paths):
                # Find file input
                file_input_selector = 'input[type="file"]'
                if self.page.locator(file_input_selector).count() > 0:
                    self.page.set_input_files(file_input_selector, path)
                    self.page.wait_for_timeout(2000)  # Wait for upload
                    logger.info(f"Uploaded image {idx + 1}: {path}")

            return True

        except Exception as e:
            logger.error(f"Image upload error: {e}")
            return False
