# -*- coding: utf-8 -*-
"""
SALON BOARD automation client using Playwright

This module implements browser automation for SALON BOARD (salonboard.com)
following the specifications defined in docs/playwright_automation_spec.md
"""

import logging
import re
import time
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
        """
        Fill content in nicEdit editor with image insertion
        (Section 3.4 of playwright_automation_spec.md)

        Processing flow:
        1. Split content by image placeholders
        2. For each part: insert text, move cursor, upload image, move cursor

        Args:
            content: Blog content with {{image_N}} placeholders
            image_paths: List of image file paths
        """
        try:
            # Split content by image placeholders
            # Pattern: {{image_1}}, {{image_2}}, etc.
            parts = re.split(r'\{\{image_(\d+)\}\}', content)

            # Method 1: Try nicEditor API (most reliable)
            try:
                # Clear editor using nicEditor API
                js_script = f"""
                (function() {{
                    try {{
                        var editorInstance = nicEditors.findEditor('blogContents');
                        if (editorInstance) {{
                            editorInstance.setContent('');
                            return true;
                        }}
                        return false;
                    }} catch(e) {{
                        console.error('nicEditor API error:', e);
                        return false;
                    }}
                }})();
                """
                result = self.page.evaluate(js_script)

                if result:
                    # nicEditor API available, process content
                    for i, part in enumerate(parts):
                        if i % 2 == 0:
                            # Text content (even indices)
                            if part.strip():
                                html_content = part.replace('\n', '<br>').replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')
                                append_script = f"""
                                (function() {{
                                    try {{
                                        var editorInstance = nicEditors.findEditor('blogContents');
                                        if (editorInstance) {{
                                            var currentContent = editorInstance.getContent();
                                            editorInstance.setContent(currentContent + `{html_content}`);
                                            return true;
                                        }}
                                        return false;
                                    }} catch(e) {{
                                        console.error('nicEditor append error:', e);
                                        return false;
                                    }}
                                }})();
                                """
                                self.page.evaluate(append_script)
                        else:
                            # Image placeholder (odd indices contain the image number)
                            image_index = int(part) - 1
                            if 0 <= image_index < len(image_paths):
                                self._set_cursor_at_end_nicedit()
                                self._upload_single_image(image_paths[image_index])
                                self._set_cursor_at_end_nicedit()

                    logger.debug("Content filled using nicEditor API")
                    return
                else:
                    logger.warning("nicEditor API not available, trying fallback methods")
            except Exception as api_err:
                logger.warning(f"nicEditor API method failed: {api_err}")

            # Method 2: Try direct DOM manipulation on contenteditable div
            try:
                editor_div = self.page.locator(Selectors.FORM['editor_div'])
                if editor_div.count() > 0:
                    editor_div.evaluate("el => el.innerHTML = ''")

                    for i, part in enumerate(parts):
                        if i % 2 == 0:
                            if part.strip():
                                html_content = part.replace('\n', '<br>').replace('`', '\\`').replace('${', '\\${')
                                editor_div.evaluate(f"el => el.innerHTML += `{html_content}`")
                                editor_div.evaluate(JS_MOVE_CURSOR_TO_END)
                        else:
                            image_index = int(part) - 1
                            if 0 <= image_index < len(image_paths):
                                editor_div.evaluate(JS_MOVE_CURSOR_TO_END)
                                self._upload_single_image(image_paths[image_index])
                                editor_div.evaluate(JS_MOVE_CURSOR_TO_END)

                    logger.debug("Content filled using contenteditable div")
                    return
            except Exception as div_err:
                logger.warning(f"Contenteditable div method failed: {div_err}")

            # Method 3: Fallback to textarea
            raise Exception("All primary methods failed, using fallback")

        except Exception as e:
            logger.warning(f"Error filling content in nicEdit: {e}")
            self._fill_content_fallback(content, image_paths)

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
        try:
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
                self.page.wait_for_selector(thumbnail, timeout=10000)
            except PlaywrightTimeoutError:
                raise UploadError("Thumbnail did not appear - upload may have failed")
            
            # Step 4: Click submit button when active
            submit_btn = Selectors.IMAGE['submit_btn']
            try:
                self.page.wait_for_selector(submit_btn, timeout=5000)
                self.page.click(submit_btn)
            except PlaywrightTimeoutError:
                raise UploadError("Submit button did not become active")
            
            # Step 5: Wait for modal to close
            modal = Selectors.IMAGE['modal']
            try:
                self.page.wait_for_selector(modal, state="hidden", timeout=10000)
            except PlaywrightTimeoutError:
                logger.warning("Modal did not close, continuing anyway")
            
            logger.info(f"Uploaded image: {image_path}")
            return True

        except UploadError:
            raise
        except Exception as e:
            logger.warning(f"Failed to upload image {image_path}: {e}")
            raise UploadError(f"Image upload failed: {e}")

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
                try {
                    // Find the nicEdit contenteditable div (the actual editing area)
                    var editor = document.querySelector("div.nicEdit-main[contenteditable='true']");
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
            result = self.page.evaluate(js_script)
            if result:
                logger.debug("Moved cursor to end of nicEdit contenteditable div")
            else:
                logger.debug("Failed to move cursor in nicEdit contenteditable div")
            return result
        except Exception as e:
            logger.warning(f"Error moving cursor in nicEdit: {e}")
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
                self._post_navigation_processing()
                logger.debug("Navigated to publish management")
            
            # Navigate to blog menu
            blog_menu = Selectors.NAV['blog_menu']
            if self.page.locator(blog_menu).count() > 0:
                self.page.click(blog_menu)
                self.page.wait_for_load_state('networkidle', timeout=15000)
                self._post_navigation_processing()
                logger.debug("Navigated to blog menu")
            
            # Click new post button
            new_post = Selectors.NAV['new_post_btn']
            if self.page.locator(new_post).count() > 0:
                self.page.click(new_post)
                self.page.wait_for_load_state('networkidle', timeout=15000)
                self._post_navigation_processing()
                logger.debug("Clicked new post button")

        except Exception as e:
            logger.warning(f"Navigation to blog form failed: {e}")
            raise ElementNotFoundError(f"Could not navigate to blog form: {e}")

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
        logger.info(f"Checking publication success at URL: {final_url}")

        # Primary success indicators from completion page
        success_indicators = [
            'ブログの登録が完了しました',  # Main success message
            '投稿しました',
            '公開しました',
            '登録しました',
            '保存しました',
        ]

        # Check for success message in page content
        page_content = self.page.content()
        success = any(indicator in page_content for indicator in success_indicators)

        # Additional check: Look for completion page button
        back_button_exists = self.page.locator("a#back").count() > 0

        # Log details for debugging
        if back_button_exists:
            logger.debug("Found 'ブログ一覧へ' button (a#back) - likely on completion page")

        if success or back_button_exists:
            logger.info(f"Blog post published successfully: {final_url}")
            return {
                'success': True,
                'url': final_url,
                'screenshot_path': screenshot_path,
                'message': 'Blog post published successfully',
            }
        else:
            logger.error(f"Publication may have failed - no success indicators found. URL: {final_url}")
            logger.error(f"Back button exists: {back_button_exists}")
            logger.debug(f"Checked for indicators: {success_indicators}")
            return {
                'success': False,
                'url': final_url,
                'screenshot_path': screenshot_path,
                'message': 'Publication status unclear',
            }
