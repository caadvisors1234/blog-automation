# -*- coding: utf-8 -*-
from django.test import SimpleTestCase
from ..utils import smart_truncate

class SmartTruncateTests(SimpleTestCase):
    def test_smart_truncate_english(self):
        text = "This is a test. But a long one."
        self.assertEqual(smart_truncate(text, 18), "This is a test.")


    def test_smart_truncate_japanese(self):
        text = "これがテストです。でも長い文章です。"
        # Cut at first sentence period.
        # "これがテストです。" is 9 chars.
        self.assertEqual(smart_truncate(text, 12), "これがテストです。") # Assuming "This is..." was a comment or typo

    def test_truncation_with_japanese_punct(self):
        text = "これは、長い文章です。ここで終わります。"
        # Length is 19 chars.
        # Target 15 chars. "...” takes 3. Text space 12.
        # "これは、長い文章で" (10 chars) -> "これは、" (4 chars) is too short (< 50% of 12).
        # Wait, "これは、" is 4 chars. 12 * 0.5 = 6. So 4 < 6. It should fallback to hard cut.
        # "これは、長い文章で..."
        
        # Let's try target 12 chars. Suffix 3. Available 9.
        # "これは、長い文" -> Last punct at index 3 (、). 3+1=4. 4 >= 9*0.5 (4.5)? No.
        # Hard cut: "これは、長い文..."
        
        # Let's try text with good punct.
        text2 = "短い文。そして続く。"
        # Length 10.
        # Target 8 chars. Suffix "...". Available 5.
        # "短い文。そ" -> Punct at 3 (。). Length 4. 4 >= 5*0.5(2.5). Yes.
        # Result "短い文。..."

    def test_truncation_exact_fit_with_punct(self):
        text = "ちょうどいい。"
        # Length 7. Target 7.
        self.assertEqual(smart_truncate(text, 7), "ちょうどいい。")


    def test_japanese_splitting(self):
        text = "春の訪れを感じる、素敵な季節になりましたね。"
        # Length 21.
        # Max 15. Available 15.
        # "春の訪れを感じる、素敵な" -> last punct "、" at index 9.
        # 9+1 = 10 chars. 10 >= 15*0.5 (7.5). Good.
        # Returns "春の訪れを感じる、"
        self.assertEqual(smart_truncate(text, 15), "春の訪れを感じる、")

    def test_no_change_needed(self):
        text = "Short text"
        self.assertEqual(smart_truncate(text, 20), "Short text")

    def test_truncation_very_short_space(self):
        """
        Test verification: When max_length is very small,
        it should return text[:max_length].
        """
        text = "Important content"
        # max_length (2)
        self.assertEqual(smart_truncate(text, 2), "Im")
        
        # Another case: max_length (1)
        self.assertEqual(smart_truncate(text, 1), "I")

