# -*- coding: utf-8 -*-
"""
SALON BOARD automation client using Playwright

This module implements browser automation for SALON BOARD (salonboard.com)
following the specifications defined in docs/playwright_automation_spec.md
"""

import json
import logging
import re
import time
import uuid
from typing import Optional, Dict, Any, List
from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError
from django.conf import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Custom Exception Classes (Section 4 of playwright_automation_spec.md)
# =============================================================================

class SALONBoardError(Exception):
    """Base exception for SALON BOARD automation errors"""
    pass


class LoginError(SALONBoardError):
    """ログイン失敗時のエラー"""
    pass


class RobotDetectionError(SALONBoardError):
    """CAPTCHA検知時のエラー"""
    pass


class SalonSelectionError(SALONBoardError):
    """指定されたサロンIDが見つからない場合のエラー"""
    pass


class ElementNotFoundError(SALONBoardError):
    """必須セレクタが見つからない場合のエラー"""
    pass


class UploadError(SALONBoardError):
    """画像アップロード処理のエラー"""
    pass


# =============================================================================
# Selector Definitions (Section 2 of playwright_automation_spec.md)
# =============================================================================

class Selectors:
    """SALON BOARD selector definitions from selectors.yaml"""
    
    # Base URLs
    BASE_URL = 'https://salonboard.com'
    LOGIN_URL = 'https://salonboard.com/login/'
    
    # Login selectors
    LOGIN = {
        'user_input': "input[name='userId']",
        'password_input': "#jsiPwInput",
        'password_input_alt': "input[name='password']",
        'submit_btn': "#idPasswordInputForm > div > div > a",
        'submit_btn_alt': "a.common-CNCcommon__primaryBtn.loginBtnSize",
    }
    
    # Blocking widgets to hide
    BLOCKERS = [
        ".karte-widget__container",
        "[class*='_reception-Skin']",
        "[class*='_reception-MinimumWidget']",
        "[id^='karte-']",
    ]
    
    # Robot detection selectors
    ROBOT_DETECTION = [
        "iframe[src*='recaptcha']",
        "div.g-recaptcha",
        "img[alt*='認証']",
        "form[action*='auth']",
    ]
    
    # Navigation selectors
    NAV = {
        'salon_table': "#biyouStoreInfoArea",
        'publish_manage': "#globalNavi > ul.common-CLPcommon__globalNavi > li:nth-child(2) > a",
        'blog_menu': "#cmsForm > div > div > ul > li:nth-child(9) > a",
        'new_post_btn': "#newPosts",
    }
    
    # Blog form selectors
    FORM = {
        'stylist': "select#stylistId",
        'category': "select#blogCategoryCd",
        'title': "input#blogTitle",
        'editor_div': "div.nicEdit-main[contenteditable='true']",
        'editor_textarea': "textarea#blogContents",
    }
    
    # Image upload selectors
    IMAGE = {
        'trigger_btn': "a#upload",
        'modal': "div.imageUploaderModal",
        'file_input': "input#sendFile",
        'thumbnail': "img.imageUploaderModalThumbnail",
        'submit_btn': "input.imageUploaderModalSubmitButton.isActive",
    }
    
    # Coupon selectors
    COUPON = {
        'trigger_btn': "a.jsc_SB_modal_trigger",
        'modal': "div#couponWrap",
        'label_list': "div#couponWrap label",
        'setting_btn': "a.jsc_SB_modal_setting_btn",
    }
    
    # Action buttons
    ACTIONS = {
        'confirm_btn': "a#confirm",
        'reflect_btn': "a#reflect",
    }


# =============================================================================
# JavaScript for cursor control (Section 3.4 of playwright_automation_spec.md)
# =============================================================================

JS_MOVE_CURSOR_TO_END = """
(body) => {
    const doc = body.ownerDocument;
    const win = doc.defaultView || doc.parentWindow;
    
    body.focus();
    const range = doc.createRange();
    const selection = win.getSelection();
    
    range.selectNodeContents(body);
    range.collapse(false); // false = 末尾
    
    selection.removeAllRanges();
    selection.addRange(range);
}
"""

JS_GET_PRIMARY_NICEDIT = """
function getPrimaryNiceditElement() {
    const preferredSelectors = [
        "#blog .editWrap div.nicEdit-main[contenteditable='true']",
        "#blog div.nicEdit-main[contenteditable='true']",
        "form#blog div.nicEdit-main[contenteditable='true']"
    ];
    for (const selector of preferredSelectors) {
        const el = document.querySelector(selector);
        if (el) {
            return el;
        }
    }
    const editors = Array.from(document.querySelectorAll("div.nicEdit-main[contenteditable='true']"));
    if (editors.length === 1) {
        return editors[0];
    }
    const withinForm = editors.find(el => el.closest('#blog'));
    if (withinForm) {
        return withinForm;
    }
    return editors[0] || null;
}
"""


# =============================================================================
# Main Client Class
# =============================================================================

class SALONBoardClient:
    """
    Client for SALON BOARD automation using Playwright
    
    This class implements the automation logic defined in:
    - docs/playwright_automation_spec.md
    - docs/system_requirements.md
    """

    def __init__(self):
        """Initialize SALON BOARD client"""
        self.playwright = None
        self.browser = None
        self.context = None
        self.page: Optional[Page] = None

    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    def start(self):
        """Start browser with appropriate settings for bot detection avoidance"""
        try:
            self.playwright = sync_playwright().start()

            # Launch browser with anti-detection arguments
            self.browser = self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',  # Hide automation
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                ]
            )

            # Create context with realistic browser fingerprint
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},  # Common desktop resolution
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',  # Latest Chrome
                locale='ja-JP',  # Japanese locale
                timezone_id='Asia/Tokyo',  # Japan timezone
                extra_http_headers={
                    'Accept-Language': 'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                }
            )

            # Create new page
            self.page = self.context.new_page()

            # Inject scripts to hide automation markers
            self.page.add_init_script("""
                // Override the navigator.webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false
                });

                // Override the navigator.plugins to appear more realistic
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });

                // Override the navigator.languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ja-JP', 'ja', 'en-US', 'en']
                });

                // Add chrome object
                window.chrome = {
                    runtime: {}
                };

                // Override permissions API
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)

            logger.info("Playwright browser started with anti-detection settings")

        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            raise

    def close(self):
        """Close browser and cleanup resources"""
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

    # =========================================================================
    # Common Processing (Section 3.1 of playwright_automation_spec.md)
    # =========================================================================

    def _post_navigation_processing(self):
        """
        Execute common processing after every page navigation
        (Section 3.1 of playwright_automation_spec.md)
        
        1. Robot detection check
        2. Hide blocking widgets
        """
        self._check_robot_detection()
        self._hide_blockers()

    def _check_robot_detection(self):
        """
        Check for CAPTCHA or robot detection
        
        Raises:
            RobotDetectionError: If robot detection is detected
        """
        for selector in Selectors.ROBOT_DETECTION:
            try:
                if self.page.locator(selector).count() > 0:
                    # Take screenshot for debugging
                    timestamp = int(time.time())
                    screenshot_path = f'/tmp/salon_board_captcha_{timestamp}.png'
                    self.page.screenshot(path=screenshot_path)
                    logger.error(f"Robot detection detected: {selector}. Screenshot: {screenshot_path}")
                    raise RobotDetectionError(f"CAPTCHA detected: {selector}")
            except RobotDetectionError:
                raise
            except Exception:
                # Selector check failed, continue
                pass

    def _hide_blockers(self):
        """
        Hide blocking widgets that may interfere with automation
        (Section 3.1 of playwright_automation_spec.md)
        """
        blockers_css = ", ".join(Selectors.BLOCKERS) + " { display: none !important; }"
        try:
            self.page.add_style_tag(content=blockers_css)
            logger.debug("Injected CSS to hide blocking widgets")
        except Exception as e:
            logger.warning(f"Failed to inject blocker CSS: {e}")

    def _take_screenshot(self, name: str) -> str:
        """Take screenshot for debugging"""
        timestamp = int(time.time())
        screenshot_path = f'/tmp/salon_board_{name}_{timestamp}.png'
        try:
            self.page.screenshot(path=screenshot_path)
            logger.info(f"Screenshot saved: {screenshot_path}")
        except Exception as e:
            logger.warning(f"Failed to take screenshot: {e}")
        return screenshot_path

    # =========================================================================
    # Login and Salon Selection (Section 3.2 of playwright_automation_spec.md)
    # =========================================================================

    def login(self, login_id: str, password: str) -> bool:
        """
        Login to SALON BOARD
        (Section 3.2 of playwright_automation_spec.md)

        Args:
            login_id: SALON BOARD login ID
            password: Password (plain text)

        Returns:
            True if login successful

        Raises:
            LoginError: If login fails
            RobotDetectionError: If CAPTCHA is detected
        """
        try:
            logger.info(f"Attempting to login to SALON BOARD as {login_id}")

            # Navigate to login page (extended timeout for slow networks)
            self.page.goto(Selectors.LOGIN_URL, wait_until='networkidle', timeout=60000)

            # Post-navigation processing
            self._post_navigation_processing()

            # Fill user ID
            user_filled = False
            for selector in [Selectors.LOGIN['user_input'], "input[name='login_id']", "input[type='text']"]:
                try:
                    if self.page.locator(selector).count() > 0:
                        self.page.fill(selector, login_id)
                        user_filled = True
                        logger.debug(f"Filled user ID using selector: {selector}")
                        break
                except Exception:
                    continue
            
            if not user_filled:
                raise ElementNotFoundError("Could not find user ID input field")
            
            # Fill password
            password_filled = False
            for selector in [Selectors.LOGIN['password_input'], Selectors.LOGIN['password_input_alt'], "input[type='password']"]:
                try:
                    if self.page.locator(selector).count() > 0:
                        self.page.fill(selector, password)
                        password_filled = True
                        logger.debug(f"Filled password using selector: {selector}")
                        break
                except Exception:
                    continue
            
            if not password_filled:
                raise ElementNotFoundError("Could not find password input field")

            # Take pre-login screenshot
            self._take_screenshot('pre_login')

            # Click login button
            clicked = False
            for selector in [Selectors.LOGIN['submit_btn'], Selectors.LOGIN['submit_btn_alt'], "button[type='submit']"]:
                try:
                    if self.page.locator(selector).count() > 0:
                        self.page.click(selector)
                        clicked = True
                        logger.info(f"Clicked login button using selector: {selector}")
                        break
                except Exception:
                    continue

            if not clicked:
                raise ElementNotFoundError("Could not find login button")

            # Wait for navigation after login (extended timeout)
            logger.info("Waiting for navigation after login...")
            try:
                self.page.wait_for_load_state('networkidle', timeout=30000)
                logger.info(f"Navigation completed, current URL: {self.page.url}")
            except PlaywrightTimeoutError as e:
                logger.error(f"Navigation timeout after login. Current URL: {self.page.url}")
                self._take_screenshot('navigation_timeout')
                raise
            
            # Post-navigation processing
            self._post_navigation_processing()

            # Wait a bit for page to fully stabilize after login
            self.page.wait_for_timeout(2000)

            # Check login success indicators
            success_indicators = [
                '#globalNavi',
                Selectors.NAV['salon_table'],
                'a[href*="logout"]',
            ]

            for indicator in success_indicators:
                try:
                    if self.page.locator(indicator).count() > 0:
                        logger.info(f"Login successful (found: {indicator})")
                        # Wait a bit more if we detected salon selection screen
                        if indicator == Selectors.NAV['salon_table']:
                            logger.info("Salon selection screen detected, waiting for page to stabilize...")
                            self.page.wait_for_timeout(2000)
                        return True
                except Exception:
                    continue

            # If we're on the intermediate /login/doLogin/ page, wait for redirect
            current_url = self.page.url.lower()
            if 'login/dologin' in current_url:
                logger.info("Login redirect page detected, waiting for final destination...")
                try:
                    self.page.wait_for_timeout(2000)
                    self.page.wait_for_url(re.compile(r".*/(CNC|CLP)/.*"), timeout=15000)
                    logger.debug(f"Redirect finished at {self.page.url}")
                    self._post_navigation_processing()
                    self.page.wait_for_timeout(2000)
                    # Re-check success indicators after redirect
                    for indicator in success_indicators:
                        try:
                            if self.page.locator(indicator).count() > 0:
                                logger.info(f"Login successful after redirect (found: {indicator})")
                                if indicator == Selectors.NAV['salon_table']:
                                    logger.info("Salon selection screen detected after redirect")
                                    self.page.wait_for_timeout(1500)
                                return True
                        except Exception:
                            continue
                except PlaywrightTimeoutError:
                    logger.warning("Login redirect did not complete within expected time")

            # Look for explicit login error messages
            error_indicators = [
                "#errMsg",
                "div.errorMessage",
                "p.error",
                ".loginError",
            ]
            for indicator in error_indicators:
                try:
                    locator = self.page.locator(indicator)
                    if locator.count() > 0:
                        error_text = (locator.first.text_content() or "").strip()
                        if error_text:
                            logger.error(f"Login error message detected ({indicator}): {error_text}")
                            self._take_screenshot('login_failed')
                            raise LoginError(error_text)
                except LoginError:
                    raise
                except Exception:
                    continue

            # Detect CAPTCHA / secondary authentication
            captcha_indicators = [
                "div.capy-captcha",
                "#avatar_image",
                "input[name='capy_captchakey']",
                "div#capy-captcha-caption",
                "div:has-text('画像認証')",
            ]
            for indicator in captcha_indicators:
                try:
                    if self.page.locator(indicator).count() > 0:
                        logger.error("CAPTCHA detected on login page")
                        self._take_screenshot('captcha_detected')
                        raise RobotDetectionError("CAPTCHA detected during login")
                except RobotDetectionError:
                    raise
                except Exception:
                    continue

            # Check if still on login page
            if 'login' in self.page.url.lower():
                self._take_screenshot('login_failed')
                raise LoginError("Login failed - still on login page")

            logger.info("Login appears successful")
            return True

        except (LoginError, RobotDetectionError, ElementNotFoundError):
            raise
        except PlaywrightTimeoutError as e:
            logger.error(f"Login timeout: {e}")
            raise LoginError(f"Login timeout: {e}")
        except Exception as e:
            logger.error(f"Login error: {e}")
            raise LoginError(f"Login error: {e}")

    def select_salon(self, salon_id: str) -> bool:
        """
        Select salon if multiple salons are available
        (Section 3.2 of playwright_automation_spec.md)

        Uses selector: a[id='{target_salon_id}']

        Args:
            salon_id: Salon ID (e.g., H000123456)

        Returns:
            True if salon selected or not needed

        Raises:
            SalonSelectionError: If salon cannot be selected
        """
        try:
            logger.info(f"Attempting to select salon: {salon_id}")

            # Check if salon selection screen is displayed
            if self.page.locator(Selectors.NAV['salon_table']).count() == 0:
                logger.debug("Salon selection not needed - not on selection screen")
                return True

            logger.info(f"Salon selection screen detected, searching for salon {salon_id}")

            # Take screenshot before selection for debugging
            self._take_screenshot('before_salon_selection')

            # Use ID attribute selector as per spec (most robust)
            # セレクタ戦略: ID属性がサロンIDと一致するaタグをクリック
            salon_selector = f"a[id='{salon_id}']"

            logger.debug(f"Trying primary selector: {salon_selector}")
            if self.page.locator(salon_selector).count() > 0:
                logger.info(f"Found salon with primary selector, clicking...")

                # Add random delay before click to appear more human-like
                import random
                delay = random.uniform(0.5, 1.5)
                self.page.wait_for_timeout(int(delay * 1000))

                self.page.click(salon_selector)
                logger.info("Clicked salon link, waiting for navigation...")

                # Use more flexible waiting strategy
                try:
                    # First wait for domcontentloaded (faster than networkidle)
                    self.page.wait_for_load_state('domcontentloaded', timeout=15000)
                    logger.info("DOM loaded, waiting for page to stabilize...")

                    # Then wait for page to be somewhat stable
                    self.page.wait_for_timeout(3000)

                    # Check if we successfully navigated away from selection screen
                    if self.page.locator(Selectors.NAV['salon_table']).count() == 0:
                        logger.info("Successfully navigated away from salon selection screen")
                    else:
                        logger.warning("Still on salon selection screen, waiting more...")
                        self.page.wait_for_timeout(2000)

                except PlaywrightTimeoutError:
                    logger.warning("Navigation timeout, but continuing anyway...")

                self._post_navigation_processing()
                logger.info(f"Selected salon: {salon_id}")
                return True

            # Fallback: try href-based selector
            fallback_selector = f"a[href*='{salon_id}']"
            logger.debug(f"Trying fallback selector: {fallback_selector}")
            if self.page.locator(fallback_selector).count() > 0:
                logger.info(f"Found salon with fallback selector, clicking...")

                # Add random delay before click
                import random
                delay = random.uniform(0.5, 1.5)
                self.page.wait_for_timeout(int(delay * 1000))

                self.page.click(fallback_selector)
                logger.info("Clicked salon link (fallback), waiting for navigation...")

                # Use more flexible waiting strategy
                try:
                    self.page.wait_for_load_state('domcontentloaded', timeout=15000)
                    logger.info("DOM loaded (fallback), waiting for page to stabilize...")
                    self.page.wait_for_timeout(3000)

                    if self.page.locator(Selectors.NAV['salon_table']).count() == 0:
                        logger.info("Successfully navigated away from salon selection screen (fallback)")
                    else:
                        logger.warning("Still on salon selection screen (fallback), waiting more...")
                        self.page.wait_for_timeout(2000)

                except PlaywrightTimeoutError:
                    logger.warning("Navigation timeout (fallback), but continuing anyway...")

                self._post_navigation_processing()
                logger.info(f"Selected salon (fallback): {salon_id}")
                return True

            # Salon not found - try to list available salons for debugging
            logger.error(f"Salon {salon_id} not found. Checking available salon links...")
            all_links = self.page.locator("#biyouStoreInfoArea a")
            link_count = all_links.count()
            logger.error(f"Found {link_count} salon links on selection screen")
            for i in range(min(link_count, 5)):  # Log first 5 links
                try:
                    link_id = all_links.nth(i).get_attribute('id')
                    link_href = all_links.nth(i).get_attribute('href')
                    logger.error(f"  Link {i}: id='{link_id}', href='{link_href}'")
                except Exception:
                    pass

            # Salon not found
            self._take_screenshot('salon_selection_failed')
            raise SalonSelectionError(f"Salon {salon_id} not found in selection screen")

        except SalonSelectionError:
            raise
        except Exception as e:
            logger.error(f"Salon selection error: {e}")
            self._take_screenshot('salon_selection_error')
            raise SalonSelectionError(f"Salon selection error: {e}")

    # =========================================================================
    # Coupon Selection (Section 3.3 of playwright_automation_spec.md)
    # =========================================================================

    def select_coupon(self, coupon_name: str) -> bool:
        """
        Select coupon by partial name match (First Match)
        (Section 3.3 of playwright_automation_spec.md)

        Args:
            coupon_name: Coupon name for partial matching

        Returns:
            True if coupon selected
        """
        if not coupon_name:
            return True

        try:
            # Click coupon trigger button
            trigger_btn = Selectors.COUPON['trigger_btn']
            if self.page.locator(trigger_btn).count() == 0:
                logger.warning("Coupon trigger button not found")
                return False
            
            self.page.click(trigger_btn)
            self.page.wait_for_timeout(1000)
            
            # Wait for modal to appear
            modal = Selectors.COUPON['modal']
            try:
                self.page.wait_for_selector(modal, timeout=5000)
            except PlaywrightTimeoutError:
                logger.warning("Coupon modal did not appear")
                return False
            
            # Find and click coupon by partial text match (Section 3.3)
            # テキストを含むラベルを検索し、最初の要素をクリック
            coupon_label = self.page.locator(Selectors.COUPON['label_list']).filter(has_text=coupon_name).first
            
            if coupon_label.count() > 0:
                coupon_label.click()
                
                # Click setting button
                setting_btn = Selectors.COUPON['setting_btn']
                if self.page.locator(setting_btn).count() > 0:
                    self.page.click(setting_btn)
                    self.page.wait_for_timeout(500)
                    logger.info(f"Selected coupon: {coupon_name}")
                    return True
            
            logger.warning(f"Coupon '{coupon_name}' not found")
            return False

        except Exception as e:
            logger.warning(f"Could not select coupon: {e}")
            return False

    # =========================================================================
    # Content and Image Handling (Section 3.4 of playwright_automation_spec.md)
    # =========================================================================

    def _fill_content_with_images(self, content: str, image_paths: List[str]) -> None:
        """Fill nicEdit editor with text and images while keeping placeholder order."""
        try:
            if self._fill_content_dom(content, image_paths):
                return
            logger.warning("[nicedit] DOM-based content fill failed, falling back to textarea method")
        except UploadError:
            raise
        except Exception as fill_error:
            logger.warning(f"[nicedit] Unexpected error during DOM fill: {fill_error}")

        self._fill_content_fallback(content, image_paths)

    def _fill_content_dom(self, content: str, image_paths: List[str]) -> bool:
        """Primary DOM-driven filling strategy with anchor based image placement."""
        parts = re.split(r'\{\{image_(\d+)\}\}', content)
        placeholder_count = max((len(parts) - 1) // 2, 0)
        logger.info(
            "[nicedit] Preparing content fill: text_segments=%s, placeholders=%s, images=%s",
            len(parts) - placeholder_count,
            placeholder_count,
            len(image_paths),
        )

        editor_div = self.page.locator(Selectors.FORM['editor_div'])
        if editor_div.count() == 0:
            logger.warning("[nicedit] Contenteditable editor not found")
            return False

        editor_div.evaluate("el => el.innerHTML = ''")
        self._mark_existing_editor_images()

        for i, part in enumerate(parts):
            if i % 2 == 0:
                if part.strip():
                    logger.info(
                        "[nicedit-dom] Appending text segment index=%s len=%s preview=%r",
                        i // 2,
                        len(part),
                        part[:30],
                    )
                    if not self._append_text_to_editor(part):
                        raise Exception("Failed to append text segment")
            else:
                image_index = int(part) - 1
                if 0 <= image_index < len(image_paths):
                    logger.info("[nicedit-dom] Handling image_%s", image_index + 1)
                    anchor_id = self._generate_anchor_id(image_index + 1)
                    if not self._create_image_anchor(anchor_id):
                        raise Exception("Failed to insert image anchor")

                    cursor_moved = self._set_cursor_at_end_nicedit()
                    logger.info(
                        "[nicedit-dom] Cursor move before upload image_%s success=%s",
                        image_index + 1,
                        cursor_moved,
                    )
                    previous_count = self._get_editor_image_count()
                    self._upload_single_image(image_paths[image_index])
                    if not self._wait_for_editor_image_count(previous_count + 1):
                        raise UploadError(f"Image {image_index + 1} did not appear in editor after upload")
                    if not self._move_new_image_to_anchor(anchor_id):
                        raise UploadError(f"Failed to position image {image_index + 1} at anchor")
                    cursor_moved = self._set_cursor_at_end_nicedit()
                    logger.info(
                        "[nicedit-dom] Cursor move after upload image_%s success=%s",
                        image_index + 1,
                        cursor_moved,
                    )

        logger.info("[nicedit-dom] Content filled using DOM anchoring method")
        self._sync_nicedit_content()
        self._log_editor_state("after_fill_dom")
        return True

    def _upload_single_image(self, image_path: str) -> bool:
        """
        Upload a single image using SALON BOARD's image uploader
        (Section 3.4 Step 4 of playwright_automation_spec.md)
        
        Steps:
        1. Click upload button (a#upload)
        2. Set file input (input#sendFile)
        3. Wait for thumbnail (img.imageUploaderModalThumbnail)
        4. Click submit button when active
        5. Wait for modal to close
        
        Args:
            image_path: Path to the image file
            
        Returns:
            True if upload successful
            
        Raises:
            UploadError: If upload fails
        """
        attempts = 2
        last_error: Optional[Exception] = None

        for attempt in range(1, attempts + 1):
            try:
                logger.info(f"[upload] Attempt {attempt}/{attempts} for {image_path}")

                # Step 1: Click upload button
                upload_btn = Selectors.IMAGE['trigger_btn']
                if self.page.locator(upload_btn).count() == 0:
                    raise UploadError("Upload button not found")

                self.page.click(upload_btn)
                self.page.wait_for_timeout(500)

                # Step 2: Set file input
                file_input = Selectors.IMAGE['file_input']
                if self.page.locator(file_input).count() == 0:
                    raise UploadError("File input not found")

                self.page.set_input_files(file_input, image_path)

                # Step 3: Wait for thumbnail to appear
                thumbnail = Selectors.IMAGE['thumbnail']
                try:
                    self.page.wait_for_selector(thumbnail, timeout=30000)
                except PlaywrightTimeoutError:
                    raise UploadError("Thumbnail did not appear within 30s")

                # Step 4: Click submit button when active
                submit_btn = Selectors.IMAGE['submit_btn']
                try:
                    self.page.wait_for_selector(submit_btn, timeout=20000)
                    self.page.click(submit_btn)
                except PlaywrightTimeoutError:
                    raise UploadError("Submit button did not become active")

                # Step 5: Wait for modal to close
                modal = Selectors.IMAGE['modal']
                try:
                    self.page.wait_for_selector(modal, state="hidden", timeout=30000)
                except PlaywrightTimeoutError:
                    raise UploadError("Image modal did not close in time")

                cursor_restored = self._set_cursor_at_end_nicedit()
                logger.info(
                    "[nicedit] Restored cursor after modal close success=%s",
                    cursor_restored,
                )

                logger.info(f"Uploaded image: {image_path}")
                return True

            except UploadError as upload_error:
                last_error = upload_error
                logger.warning(f"[upload] Attempt {attempt} failed: {upload_error}")
                self.page.wait_for_timeout(1000)
            except Exception as e:
                last_error = UploadError(f"Image upload failed: {e}")
                logger.warning(f"Failed to upload image {image_path}: {e}")
                self.page.wait_for_timeout(1000)

        raise UploadError(str(last_error))

    def _get_editor_image_count(self) -> int:
        """Return number of <img> tags currently in the nicEdit editor."""
        script = """
        () => {
            __NICEDIT_HELPER__
            try {
                const editorInstance = typeof nicEditors !== 'undefined'
                    ? nicEditors.findEditor('blogContents')
                    : null;
                let source = '';
                if (editorInstance) {
                    source = editorInstance.getContent() || '';
                } else {
                    const editorDiv = getPrimaryNiceditElement();
                    source = editorDiv ? editorDiv.innerHTML : '';
                }
                if (!source) {
                    return 0;
                }
                const matches = source.match(/<img\\b/gi);
                return matches ? matches.length : 0;
            } catch (error) {
                console.error('Failed to count editor images', error);
                return 0;
            }
        }
        """
        script = script.replace("__NICEDIT_HELPER__", JS_GET_PRIMARY_NICEDIT)
        try:
            count = self.page.evaluate(script)
            return int(count or 0)
        except Exception as count_error:
            logger.debug(f"Could not determine editor image count: {count_error}")
            return 0

    def _wait_for_editor_image_count(self, expected_count: int, timeout: int = 8000) -> bool:
        """Wait until the nicEdit editor reports at least expected_count images."""
        if expected_count <= 0:
            return True

        wait_script = """
        ({ expected }) => {
            __NICEDIT_HELPER__
            try {
                const editorInstance = typeof nicEditors !== 'undefined'
                    ? nicEditors.findEditor('blogContents')
                    : null;
                let source = '';
                if (editorInstance) {
                    source = editorInstance.getContent() || '';
                } else {
                    const editorDiv = getPrimaryNiceditElement();
                    source = editorDiv ? editorDiv.innerHTML : '';
                }
                if (!source) {
                    return false;
                }
                const matches = source.match(/<img\\b/gi);
                const count = matches ? matches.length : 0;
                return count >= expected;
            } catch (error) {
                console.error('Failed to evaluate editor image count', error);
                return false;
            }
        }
        """
        wait_script = wait_script.replace("__NICEDIT_HELPER__", JS_GET_PRIMARY_NICEDIT)
        try:
            self.page.wait_for_function(wait_script, arg={'expected': expected_count}, timeout=timeout)
            logger.debug(f"Editor image count reached {expected_count}")
            return True
        except PlaywrightTimeoutError:
            logger.warning(f"Image insertion verification timed out (expected count: {expected_count})")
            return False

    def _sync_nicedit_content(self) -> None:
        """Ensure nicEditor content is synced back to the underlying textarea."""
        sync_script = """
        () => {
            __NICEDIT_HELPER__
            try {
                const editorInstance = typeof nicEditors !== 'undefined'
                    ? nicEditors.findEditor('blogContents')
                    : null;
                if (editorInstance) {
                    editorInstance.saveContent();
                    return true;
                }
                const textarea = document.querySelector('textarea#blogContents');
                const editorDiv = getPrimaryNiceditElement();
                if (textarea && editorDiv) {
                    textarea.value = editorDiv.innerHTML;
                    return true;
                }
                return false;
            } catch (error) {
                console.error('Failed to sync nicEdit content', error);
                return false;
            }
        }
        """
        sync_script = sync_script.replace("__NICEDIT_HELPER__", JS_GET_PRIMARY_NICEDIT)
        try:
            synced = self.page.evaluate(sync_script)
            if not synced:
                logger.debug("nicEdit content synchronization skipped (editor instance not available)")
        except Exception as sync_error:
            logger.warning(f"Failed to synchronize nicEdit content: {sync_error}")

    def _log_editor_state(self, stage: str = "") -> None:
        """Log editor HTML/textareas to help verify publication content."""
        if not logger.isEnabledFor(logging.DEBUG):
            return
        script = """
        () => {
            __NICEDIT_HELPER__
            try {
                const editorInstance = typeof nicEditors !== 'undefined'
                    ? nicEditors.findEditor('blogContents')
                    : null;
                let html = '';
                if (editorInstance) {
                    html = editorInstance.getContent() || '';
                } else {
                    const editorDiv = getPrimaryNiceditElement();
                    html = editorDiv ? editorDiv.innerHTML : '';
                }
                const textarea = document.querySelector('textarea#blogContents');
                const textareaValue = textarea ? textarea.value : '';
                const htmlImages = html ? (html.match(/<img\\b/gi) || []).length : 0;
                return {
                    htmlLength: html.length,
                    textareaLength: textareaValue.length,
                    htmlPreview: html.slice(0, 200),
                    textareaPreview: textareaValue.slice(0, 200),
                    imageCount: htmlImages
                };
            } catch (error) {
                return { error: error?.message || String(error) };
            }
        }
        """
        script = script.replace("__NICEDIT_HELPER__", JS_GET_PRIMARY_NICEDIT)
        try:
            info = self.page.evaluate(script)
            if info.get('error'):
                logger.warning(f"[debug-editor] {stage} failed: {info['error']}")
            else:
                logger.debug(
                    f"[debug-editor] {stage}: html_len={info['htmlLength']}, "
                    f"textarea_len={info['textareaLength']}, images={info['imageCount']}, "
                    f"html_preview={info['htmlPreview']!r}"
                )
        except Exception as log_error:
            logger.warning(f"Unable to log editor state ({stage}): {log_error}")

    def _set_cursor_at_end_nicedit(self) -> bool:
        """
        Move cursor to the end of nicEdit editor

        nicEdit creates a contenteditable div (div.nicEdit-main) where actual editing happens.
        We need to move the cursor in this div, not in the textarea.

        Returns:
            True if successful, False otherwise
        """
        try:
            js_script = """
            (function() {
                __NICEDIT_HELPER__
                try {
                    // Find the nicEdit contenteditable div (the actual editing area)
                    var editor = getPrimaryNiceditElement();
                    if (editor) {
                        // Move cursor to end of the contenteditable div
                        var range = document.createRange();
                        range.selectNodeContents(editor);
                        range.collapse(false); // false = move to end
                        var selection = window.getSelection();
                        selection.removeAllRanges();
                        selection.addRange(range);
                        editor.focus();
                        return true;
                    }
                        return false;
                } catch(e) {
                    console.error('Cursor control error:', e);
                    return false;
                }
            })();
            """
            js_script = js_script.replace("__NICEDIT_HELPER__", JS_GET_PRIMARY_NICEDIT)
            result = self.page.evaluate(js_script)
            if result:
                logger.debug("Moved cursor to end of nicEdit contenteditable div")
            else:
                logger.debug("Failed to move cursor in nicEdit contenteditable div")
            return result
        except Exception as e:
            logger.warning(f"Error moving cursor in nicEdit: {e}")
            return False

    def _mark_existing_editor_images(self) -> None:
        """Add a data marker to all existing images so new uploads can be detected."""
        script = """
        () => {
            __NICEDIT_HELPER__
            try {
                const editor = getPrimaryNiceditElement();
                if (!editor) {
                    return false;
                }
                editor.querySelectorAll('img').forEach(img => {
                    if (!img.hasAttribute('data-image-bound')) {
                        img.setAttribute('data-image-bound', 'existing');
                    }
                });
                return true;
            } catch (error) {
                console.error('Failed to mark existing images', error);
                return false;
            }
        }
        """
        script = script.replace("__NICEDIT_HELPER__", JS_GET_PRIMARY_NICEDIT)
        try:
            self.page.evaluate(script)
        except Exception as err:
            logger.debug(f"Could not mark existing images: {err}")

    def _append_text_to_editor(self, raw_text: str) -> bool:
        """Append sanitized HTML converted from raw_text to the editor."""
        html_content = raw_text.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '<br>')
        script = f"""
        () => {{
            __NICEDIT_HELPER__
            try {{
                const editor = getPrimaryNiceditElement();
                if (!editor) {{
                    return false;
                }}
                const temp = document.createElement('div');
                temp.innerHTML = {json.dumps(html_content)};
                while (temp.firstChild) {{
                    editor.appendChild(temp.firstChild);
                }}
                return true;
            }} catch (error) {{
                console.error('Append text error', error);
                return false;
            }}
        }}
        """
        script = script.replace("__NICEDIT_HELPER__", JS_GET_PRIMARY_NICEDIT)
        try:
            result = self.page.evaluate(script)
            if not result:
                logger.warning("Failed to append text segment to editor")
            return result
        except Exception as err:
            logger.warning(f"Append text execution failed: {err}")
            return False

    def _generate_anchor_id(self, index: int) -> str:
        return f"nicedit-image-anchor-{index}-{uuid.uuid4().hex}"

    def _create_image_anchor(self, anchor_id: str) -> bool:
        """Insert a zero-sized span that marks where an image should be placed."""
        script = f"""
        () => {{
            __NICEDIT_HELPER__
            try {{
                const editor = getPrimaryNiceditElement();
                if (!editor) {{
                    return false;
                }}
                const anchor = document.createElement('span');
                anchor.setAttribute('data-image-anchor', {json.dumps(anchor_id)});
                anchor.style.display = 'inline-block';
                anchor.style.width = '0px';
                anchor.style.height = '0px';
                anchor.style.lineHeight = '0';
                editor.appendChild(anchor);
                return true;
            }} catch (error) {{
                console.error('Create anchor error', error);
                return false;
            }}
        }}
        """
        script = script.replace("__NICEDIT_HELPER__", JS_GET_PRIMARY_NICEDIT)
        try:
            result = self.page.evaluate(script)
            if not result:
                logger.warning(f"Failed to create image anchor {anchor_id}")
            return result
        except Exception as err:
            logger.warning(f"Create anchor execution failed: {err}")
            return False

    def _move_new_image_to_anchor(self, anchor_id: str) -> bool:
        """Move the most recent image upload to the specified anchor location."""
        if not self._wait_for_unbound_editor_image(timeout=10000):
            logger.warning("[nicedit] No unbound image detected before anchor move")
            return False

        script = f"""
        () => {{
            __NICEDIT_HELPER__
            try {{
                const editor = getPrimaryNiceditElement();
                if (!editor) {{
                    return false;
                }}
                const anchor = editor.querySelector(`[data-image-anchor="{anchor_id}"]`);
                if (!anchor) {{
                    return false;
                }}
                const images = Array.from(editor.querySelectorAll('img'));
                if (!images.length) {{
                    return false;
                }}
                const target = images.find(img => !img.hasAttribute('data-image-bound')) || images[images.length - 1];
                if (!target) {{
                    return false;
                }}
                anchor.parentNode.insertBefore(target, anchor);
                target.setAttribute('data-image-bound', anchor_id);
                anchor.remove();
                return true;
            }} catch (error) {{
                console.error('Move image to anchor error', error);
                return false;
            }}
        }}
        """
        script = script.replace("__NICEDIT_HELPER__", JS_GET_PRIMARY_NICEDIT)
        try:
            result = self.page.evaluate(script)
            if not result:
                logger.warning(f"Could not move uploaded image to anchor {anchor_id}")
            else:
                logger.info(f"[nicedit] Forced image to anchor {anchor_id}")
            return result
        except Exception as err:
            logger.warning(f"Anchor relocation failed: {err}")
            return False

    def _wait_for_unbound_editor_image(self, timeout: int = 10000) -> bool:
        script = """
        () => {
            __NICEDIT_HELPER__
            try {
                const editor = getPrimaryNiceditElement();
                if (!editor) {
                    return false;
                }
                return Array.from(editor.querySelectorAll('img')).some(img => !img.hasAttribute('data-image-bound'));
            } catch (error) {
                console.error('Unbound image wait error', error);
                return false;
            }
        }
        """
        script = script.replace("__NICEDIT_HELPER__", JS_GET_PRIMARY_NICEDIT)
        try:
            self.page.wait_for_function(script, timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            logger.warning("[nicedit] Waiting for unbound image timed out")
            return False

    def _fill_content_fallback(self, content: str, image_paths: List[str]) -> None:
        """
        Fallback method to fill content when nicEdit is not available
        
        Args:
            content: Blog content
            image_paths: List of image file paths
        """
        # Remove image placeholders for fallback
        clean_content = re.sub(r'\{\{image_\d+\}\}', '', content)
        
        content_selectors = [
            'textarea[name="content"]',
            '#content',
            '.editor textarea',
            'textarea.blog-content',
        ]
        
        for selector in content_selectors:
            try:
                if self.page.locator(selector).count() > 0:
                    self.page.fill(selector, clean_content)
                    logger.debug(f"Filled content using fallback selector: {selector}")
                    break
            except Exception:
                continue
        
        # Try to upload images sequentially
        for image_path in image_paths:
            try:
                self._upload_single_image(image_path)
            except UploadError as e:
                logger.warning(f"Fallback image upload failed: {e}")
        self._sync_nicedit_content()
        self._log_editor_state("after_fill_fallback")

    # =========================================================================
    # Blog Publication (Section 3.5 of playwright_automation_spec.md)
    # =========================================================================

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
        (Section 3.5 of playwright_automation_spec.md)

        Args:
            title: Blog post title (max 25 chars)
            content: Blog post content with {{image_N}} placeholders
            image_paths: List of image file paths
            stylist_id: Optional stylist T number
            coupon_name: Optional coupon name for partial match
            salon_id: Optional salon H number

        Returns:
            Dictionary with publication result

        Raises:
            Various SALONBoardError subclasses on failure
        """
        try:
            logger.info(f"Publishing blog post: {title[:25]}...")
            image_paths = image_paths or []

            # Select salon if needed
            if salon_id:
                self.select_salon(salon_id)
            
            # Navigate to publish management (掲載管理)
            self._navigate_to_blog_form()

            # Wait for form to load
            try:
                self.page.wait_for_selector(Selectors.FORM['title'], timeout=10000)
            except PlaywrightTimeoutError:
                raise ElementNotFoundError("Blog form title field not found")

            # Fill title (max 25 chars as per system_requirements.md)
            self.page.fill(Selectors.FORM['title'], title[:25])
            logger.debug(f"Filled title: {title[:25]}")

            # Select stylist if provided
            if stylist_id:
                self._select_stylist(stylist_id)
            
            # Select category (default to BL02 - おすすめメニューなど)
            self._select_category("BL02")

            # Select coupon if provided
            if coupon_name:
                self.select_coupon(coupon_name)

            # Handle content with images using nicEdit
            self._fill_content_with_images(content, image_paths)
            try:
                current_title = self.page.input_value(Selectors.FORM['title'])
            except Exception:
                current_title = ''
            logger.debug(
                f"[debug-form] Prepared blog form: title={current_title!r}, "
                f"content_len={len(content)}, image_files={len(image_paths)}"
            )

            # Take screenshot before confirmation
            self._take_screenshot('before_confirm')

            # Click confirm button (確認画面へ)
            self._click_confirm_button()

            # Check for errors on confirmation page (Section 3.5 Step 2)
            self._check_form_errors()

            # Take screenshot of confirmation page
            self._take_screenshot('confirm_page')

            # Click reflect button (登録・反映する) (Section 3.5 Step 3)
            self._click_reflect_button()

            # Wait for completion
            try:
                self.page.wait_for_load_state('networkidle', timeout=15000)
            except PlaywrightTimeoutError:
                logger.warning("Navigation timeout after submit")

            # Take final screenshot (Section 3.5 Step 4)
            final_screenshot = self._take_screenshot('completed')

            # Check for success
            return self._check_publication_success(final_screenshot)

        except SALONBoardError:
            raise
        except Exception as e:
            logger.error(f"Failed to publish blog post: {e}")
            raise SALONBoardError(f"SALON BOARD publication failed: {str(e)}")

    def _navigate_to_blog_form(self):
        """Navigate to blog creation form"""
        try:
            # Navigate to publish management (掲載管理)
            publish_manage = Selectors.NAV['publish_manage']
            if self.page.locator(publish_manage).count() > 0:
                self.page.click(publish_manage)
                self.page.wait_for_load_state('networkidle', timeout=15000)
                self.page.wait_for_url(re.compile(r".*/CNB/reflect/reflectTop/.*"), timeout=15000)
                self._post_navigation_processing()
                self.page.wait_for_timeout(1000)
                logger.debug("Navigated to publish management")
            
            # Navigate to blog menu (ブログ一覧)
            blog_menu = Selectors.NAV['blog_menu']
            if self.page.locator(blog_menu).count() > 0:
                self.page.click(blog_menu)
                self.page.wait_for_load_state('networkidle', timeout=15000)
                self.page.wait_for_url(re.compile(r".*/CLP/bt/blog/blogList/.*"), timeout=15000)
                self._post_navigation_processing()
                logger.debug("Navigated to blog list")
            
            # Click new post button
            new_post = Selectors.NAV['new_post_btn']
            if self.page.locator(new_post).count() > 0:
                self.page.click(new_post)
                self.page.wait_for_load_state('networkidle', timeout=15000)
                self.page.wait_for_url(re.compile(r".*/CLP/bt/blog/blog/.*"), timeout=15000)
                self._post_navigation_processing()
                self.page.wait_for_timeout(1500)
                logger.debug("Clicked new post button and waiting for blog form")

        except Exception as e:
            current_url = self.page.url if self.page else 'unknown'
            logger.warning(f"Navigation to blog form failed at {current_url}: {e}")
            raise ElementNotFoundError(
                f"Could not navigate to blog form: {e}\n"\
                f"=========================== logs ===========================\n"\
                f"last_url={current_url}\n"\
                f"============================================================"
            )

    def _select_stylist(self, stylist_id: str) -> bool:
        """
        Select stylist by T number
        
        Args:
            stylist_id: Stylist T number (e.g., T123456)
        """
        try:
            stylist_selector = Selectors.FORM['stylist']
            if self.page.locator(stylist_selector).count() > 0:
                self.page.select_option(stylist_selector, stylist_id)
                logger.info(f"Selected stylist: {stylist_id}")
                return True
            logger.warning(f"Stylist selector not found")
            return False
        except Exception as e:
            logger.warning(f"Could not select stylist: {e}")
            return False

    def _select_category(self, category_code: str) -> bool:
        """Select blog category"""
        try:
            category_selector = Selectors.FORM['category']
            if self.page.locator(category_selector).count() > 0:
                self.page.select_option(category_selector, category_code)
                logger.debug(f"Selected category: {category_code}")
                return True
            return False
        except Exception as e:
            logger.warning(f"Could not select category: {e}")
            return False

    def _click_confirm_button(self):
        """Click the confirm button to go to confirmation page"""
        confirm_btn = Selectors.ACTIONS['confirm_btn']
        if self.page.locator(confirm_btn).count() > 0:
            self.page.click(confirm_btn)
            self.page.wait_for_load_state('networkidle', timeout=15000)
            self._post_navigation_processing()
            logger.debug("Clicked confirm button")
        else:
            # Fallback
            for selector in ['button[type="submit"]', 'input[type="submit"]']:
                if self.page.locator(selector).count() > 0:
                    self.page.click(selector)
                    self.page.wait_for_load_state('networkidle', timeout=15000)
                    break

    def _check_form_errors(self):
        """Check for form validation errors on confirmation page"""
        error_indicators = [
            '.error',
            '.alert-error',
            '.validation-error',
            '[class*="error"]',
        ]
        
        for indicator in error_indicators:
            try:
                error_elements = self.page.locator(indicator)
                if error_elements.count() > 0:
                    error_text = error_elements.first.text_content()
                    logger.warning(f"Form error detected: {error_text}")
            except Exception:
                pass

    def _click_reflect_button(self):
        """
        Click the reflect button (登録・反映する)
        Note: Be careful not to click 「登録・反映しない」button
        """
        reflect_btn = Selectors.ACTIONS['reflect_btn']
        if self.page.locator(reflect_btn).count() > 0:
            self.page.click(reflect_btn)
            logger.debug("Clicked reflect button")
        else:
            # Fallback
            for selector in ['button[type="submit"]', 'input[type="submit"]']:
                if self.page.locator(selector).count() > 0:
                    self.page.click(selector)
                    break

    def _check_publication_success(self, screenshot_path: str) -> Dict[str, Any]:
        """
        Check if publication was successful

        Based on the completion page HTML, the success message is:
        'ブログの登録が完了しました。'

        Args:
            screenshot_path: Path to screenshot for reference

        Returns:
            Dictionary with success status and details
        """
        final_url = self.page.url
        final_url_lower = final_url.lower()
        completion_markers = [
            '/clp/bt/blog/blog/complete',
            '/blog/complete',
        ]
        confirm_markers = [
            '/clp/bt/blog/blog/confirm',
            '/blog/confirm',
        ]
        is_completion_page = any(marker in final_url_lower for marker in completion_markers)
        is_confirm_page = any(marker in final_url_lower for marker in confirm_markers)
        logger.info(
            "Checking publication success at URL: %s (completion=%s, confirm=%s)",
            final_url,
            is_completion_page,
            is_confirm_page,
        )

        # Primary success indicators from completion page
        success_indicators = [
            'ブログの登録が完了しました',  # Main success message
            'ブログの登録が完了しました。',  # Message with punctuation
            'ブログ登録が完了しました',
            'ブログ登録が完了しました。',
            'ブログの登録が完了いたしました',
            '投稿しました',
            '公開しました',
            '登録しました',
            '保存しました',
        ]

        page_content = ''
        page_text = ''
        try:
            page_content = self.page.content() or ''
        except Exception as content_error:
            logger.debug(f"Failed to read completion HTML: {content_error}")

        try:
            page_text = self.page.evaluate("() => document.body ? document.body.innerText : ''") or ''
        except Exception as text_error:
            logger.debug(f"Failed to read completion text: {text_error}")

        if page_text:
            preview = page_text.replace('\n', ' ').strip()
            if preview:
                logger.debug(f"Completion text preview: {preview[:200]}")

        # Check both HTML and extracted text
        sources = [src for src in (page_content, page_text) if src]
        success = any(indicator in source for source in sources for indicator in success_indicators)

        # Normalized text check (handles spans splitting characters)
        if not success and page_text:
            normalized_text = ''.join(page_text.split())
            normalized_indicators = [''.join(ind.split()) for ind in success_indicators]
            success = any(ind in normalized_text for ind in normalized_indicators)

        # Fallback: direct locator search for success strings
        if not success:
            for indicator in success_indicators:
                selector = f"xpath=//*[contains(normalize-space(.), \"{indicator}\")]"
                try:
                    if self.page.locator(selector).count() > 0:
                        success = True
                        logger.debug(f"Detected success indicator via locator: {indicator}")
                        break
                except Exception as locator_error:
                    logger.debug(f"Success locator check failed for {indicator}: {locator_error}")

        # Additional check: Look for completion page navigation controls
        back_button_selectors = [
            "a#back",
            "a:has-text(\"ブログ一覧\")",
            "a:has-text(\"ブログ一覧へ\")",
            "a:has-text(\"一覧へ\")",
            "a[href*='blogList']",
        ]

        back_button_exists = False
        for selector in back_button_selectors:
            try:
                locator = self.page.locator(selector)
                if locator.count() > 0:
                    back_button_exists = True
                    logger.debug(f"Detected completion navigation control via selector: {selector}")
                    break
            except Exception as selector_error:
                logger.debug(f"Back button detection failed for {selector}: {selector_error}")

        should_treat_as_success = False
        if success and (is_completion_page or not is_confirm_page):
            should_treat_as_success = True
        elif back_button_exists and is_completion_page:
            logger.debug(
                "Found completion back button on completion page; treating as success"
            )
            should_treat_as_success = True
        elif back_button_exists:
            logger.debug(
                "Back button detected outside completion page; ignoring"
            )

        if should_treat_as_success:
            logger.info(f"Blog post published successfully: {final_url}")
            logger.debug(
                f"[debug-publish] success indicators matched, screenshot={screenshot_path}"
            )
            return {
                'success': True,
                'url': final_url,
                'screenshot_path': screenshot_path,
                'message': 'Blog post published successfully',
            }

        logger.error(
            f"Publication may have failed - no completion page detected. URL: {final_url}"
        )
        if page_text:
            logger.error(f"Completion text sample: {page_text[:160].replace(chr(10), ' ')}")
        logger.debug(f"Checked for indicators: {success_indicators}")

        return {
            'success': False,
            'url': final_url,
            'screenshot_path': screenshot_path,
            'message': 'Publication status unclear',
        }
