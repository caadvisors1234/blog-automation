# -*- coding: utf-8 -*-
"""
Google Gemini AI client for content generation
"""

import logging
import json
from typing import Optional, Dict, Any
from django.conf import settings
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Client for Google Gemini AI API
    """

    def __init__(self):
        """Initialize Gemini client"""
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_id = 'gemini-2.5-flash'

    def generate_blog_content(
        self,
        prompt: str,
        title: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """
        Generate blog post content using Gemini

        Args:
            prompt: User's content generation prompt
            title: Optional existing title to enhance
            temperature: Creativity level (0.0-1.0)
            max_output_tokens: Maximum length of generated content

        Returns:
            Dictionary containing generated title and content

        Raises:
            Exception: If generation fails
        """
        try:
            # Construct system prompt for blog content generation
            system_instruction = """
あなたは美容サロンのブログライターです。
ユーザーからのリクエストに基づいて、魅力的で読みやすいブログ記事を作成してください。

記事の要件：
- タイトルは40文字以内で、興味を引くものにする
- 本文は800-1200文字程度
- 読みやすい段落構成
- 専門用語は適度に説明を加える
- ポジティブで親しみやすいトーン

出力形式：
必ず以下のJSON形式で返してください：
{
  "title": "記事タイトル",
  "content": "記事本文（改行を含む）"
}
"""

            # Enhance prompt with title if provided
            full_prompt = prompt
            if title:
                full_prompt = f"既存のタイトル「{title}」を参考に、以下のリクエストで記事を作成してください：\n\n{prompt}"

            # Generate content
            logger.info(f"Generating content with Gemini for prompt: {prompt[:100]}...")

            response = self.client.models.generate_content(
                model=self.model_id,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    response_mime_type="application/json",
                    system_instruction=system_instruction,
                )
            )

            # Debug: log response
            logger.debug(f"Response type: {type(response)}")
            logger.debug(f"Response: {response}")

            # Parse response
            if not response or not response.text:
                logger.error(f"Empty response from Gemini API. Response: {response}")
                raise Exception("Empty response from Gemini API")

            # Extract JSON from response
            result = json.loads(response.text)

            logger.info("Content generation successful")

            return {
                'title': result.get('title', title or 'Untitled'),
                'content': result.get('content', ''),
                'model': self.model_id,
                'prompt_tokens': 0,
                'completion_tokens': 0,
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            # Fallback: treat entire response as content
            return {
                'title': title or 'AI Generated Post',
                'content': response.text if response else '',
                'model': 'gemini-2.5-flash',
                'error': 'JSON parse error',
            }

        except Exception as e:
            logger.error(f"Gemini content generation failed: {e}")
            raise Exception(f"AI content generation failed: {str(e)}")

    def enhance_title(self, current_title: str, content: str) -> str:
        """
        Enhance or generate a better title based on content

        Args:
            current_title: Current title
            content: Blog post content

        Returns:
            Enhanced title
        """
        try:
            prompt = f"""
以下のブログ記事に最適なタイトルを生成してください。

現在のタイトル: {current_title}
記事内容（抜粋）: {content[:500]}

要件：
- 40文字以内
- 興味を引く
- 内容を適切に表現

タイトルのみを返してください。
"""

            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.8,
                    max_output_tokens=100,
                )
            )

            if response and response.text:
                return response.text.strip()

            return current_title

        except Exception as e:
            logger.error(f"Title enhancement failed: {e}")
            return current_title
