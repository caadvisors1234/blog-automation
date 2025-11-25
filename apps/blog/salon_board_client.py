# -*- coding: utf-8 -*-
"""
SALON BOARD automation client using Playwright
"""

import logging
from typing import Optional, Dict, Any
from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError
from cryptography.fernet import Fernet
from django.conf import settings
import time

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

    def login(self, email: str, encrypted_password: str) -> bool:
        """
        Login to SALON BOARD

        Args:
            email: SALON BOARD email
            encrypted_password: Encrypted password

        Returns:
            True if login successful, False otherwise
        """
        try:
            # Decrypt password
            fernet = Fernet(settings.ENCRYPTION_KEY.encode())
            password = fernet.decrypt(encrypted_password.encode()).decode()

            logger.info(f"Attempting to login to SALON BOARD as {email}")

            # Navigate to login page
            self.page.goto(self.LOGIN_URL, wait_until='networkidle', timeout=30000)

            # Fill login form
            self.page.fill('input[name="login_id"], input[type="text"]', email)
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

    def publish_blog_post(
        self,
        title: str,
        content: str,
        salon_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Publish blog post to SALON BOARD

        Args:
            title: Blog post title
            content: Blog post content
            salon_id: Optional salon ID

        Returns:
            Dictionary with publication result

        Raises:
            Exception: If publication fails
        """
        try:
            logger.info(f"Publishing blog post: {title[:50]}...")

            # Navigate to blog creation page
            blog_create_url = f"{self.BLOG_URL}create/"
            self.page.goto(blog_create_url, wait_until='networkidle', timeout=30000)

            # Wait for form to load
            self.page.wait_for_selector('input[name="title"], #title', timeout=10000)

            # Fill title
            title_selector = 'input[name="title"], #title'
            self.page.fill(title_selector, title)

            # Fill content
            # Try multiple common selectors for content editor
            content_selectors = [
                'textarea[name="content"]',
                '#content',
                '.editor textarea',
                'textarea.blog-content',
            ]

            content_filled = False
            for selector in content_selectors:
                if self.page.locator(selector).count() > 0:
                    self.page.fill(selector, content)
                    content_filled = True
                    break

            if not content_filled:
                raise Exception("Could not find content input field")

            # Optional: Handle salon selection if multiple salons
            if salon_id:
                salon_selector = f'select[name="salon_id"], #salon_id'
                if self.page.locator(salon_selector).count() > 0:
                    self.page.select_option(salon_selector, salon_id)

            # Take screenshot before submission for debugging
            screenshot_path = f'/tmp/salon_board_before_submit_{int(time.time())}.png'
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

            # Check for success indicators
            success_indicators = [
                '投稿しました',
                '公開しました',
                '保存しました',
                'success',
                '/blog/',  # URL changed to blog list/detail
            ]

            success = any(
                indicator in self.page.content().lower() or indicator in final_url.lower()
                for indicator in success_indicators
            )

            if success:
                logger.info(f"Blog post published successfully: {final_url}")
                return {
                    'success': True,
                    'url': final_url,
                    'message': 'Blog post published successfully',
                }
            else:
                logger.error("Publication may have failed - no success indicators found")
                return {
                    'success': False,
                    'url': final_url,
                    'message': 'Publication status unclear',
                }

        except Exception as e:
            logger.error(f"Failed to publish blog post: {e}")
            raise Exception(f"SALON BOARD publication failed: {str(e)}")
