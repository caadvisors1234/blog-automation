# -*- coding: utf-8 -*-
"""
Google Gemini AI client for content generation
"""

import logging
import json
import re
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, List
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
        self.model_id = 'gemini-3-flash-preview'

    def _extract_json_from_text(self, text: str) -> Optional[Any]:
        """
        Extract JSON from text response, handling various formats.
        
        Args:
            text: Raw response text that may contain JSON
            
        Returns:
            Parsed JSON object or None if parsing fails
        """
        if not text:
            return None
            
        # Clean up the text
        text = text.strip()
        
        # Try direct parsing first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code blocks
        patterns = [
            r'```json\s*([\s\S]*?)\s*```',  # ```json ... ```
            r'```\s*([\s\S]*?)\s*```',       # ``` ... ```
            r'\{[\s\S]*\}',                   # Raw JSON object
            r'\[[\s\S]*\]',                   # Raw JSON array
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            for match in matches:
                try:
                    # For regex groups
                    json_str = match if isinstance(match, str) else match[0]
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue
        
        # Last resort: try to find JSON-like structure and fix common issues
        try:
            # Remove potential leading/trailing non-JSON content
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            if start_idx != -1 and end_idx != -1:
                json_str = text[start_idx:end_idx + 1]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
            
        return None

    def _clean_content(self, content: str) -> str:
        """
        Clean and format content string.
        Converts escaped newlines to actual newlines.
        
        Args:
            content: Raw content string
            
        Returns:
            Cleaned content string
        """
        if not content:
            return ""
        
        # Replace literal \n with actual newlines if they're escaped
        # This handles cases where the JSON has \\n instead of actual newlines
        content = content.replace('\\n', '\n')
        
        # Remove excessive whitespace while preserving intentional line breaks
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            # Preserve empty lines (for paragraph breaks) but remove excessive ones
            if line.strip() or (cleaned_lines and cleaned_lines[-1].strip()):
                cleaned_lines.append(line.rstrip())
        
        return '\n'.join(cleaned_lines).strip()

    def _ensure_image_placeholders(self, content: str, image_count: int) -> str:
        """
        Ensure content contains all required image placeholders.
        If any placeholders are missing, append them at appropriate positions.
        
        Args:
            content: Article content
            image_count: Number of images that need placeholders
            
        Returns:
            Content with all image placeholders guaranteed
        """
        if image_count <= 0:
            return content
        
        # Find which placeholders are already present
        existing_placeholders = set()
        for i in range(1, image_count + 1):
            # Check for various placeholder formats
            patterns = [
                f'{{{{image_{i}}}}}',
                f'{{image_{i}}}',
                f'[[image_{i}]]',
                f'[image_{i}]',
            ]
            for pattern in patterns:
                if pattern in content:
                    existing_placeholders.add(i)
                    break
        
        # Find missing placeholders
        missing = [i for i in range(1, image_count + 1) if i not in existing_placeholders]
        
        if not missing:
            return content
        
        logger.info(f"Adding missing image placeholders: {missing}")
        
        # Split content into paragraphs
        paragraphs = content.split('\n\n')
        
        # Calculate positions to insert missing placeholders
        # Distribute them evenly throughout the content
        if len(paragraphs) > 1:
            # Insert placeholders between paragraphs
            for idx, img_num in enumerate(missing):
                # Calculate position (distribute evenly)
                insert_pos = min(
                    (idx + 1) * len(paragraphs) // (len(missing) + 1),
                    len(paragraphs) - 1
                )
                # Insert after the paragraph at insert_pos
                placeholder = f'\n\n{{{{image_{img_num}}}}}'
                paragraphs[insert_pos] = paragraphs[insert_pos] + placeholder
            
            content = '\n\n'.join(paragraphs)
        else:
            # Single paragraph or no paragraph breaks - append at end
            placeholder_block = '\n\n' + '\n\n'.join([f'{{{{image_{i}}}}}' for i in missing])
            content = content + placeholder_block
        
        return content

    def generate_blog_content_variations(
        self,
        prompt: str,
        num_variations: int = 3,
        image_count: int = 0,
        image_paths: Optional[List[str]] = None,
        temperature: float = 0.9,
        max_output_tokens: int = 8192,
    ) -> Dict[str, Any]:
        """
        Generate multiple blog post content variations using Gemini.
        
        Args:
            prompt: User's content generation prompt
            num_variations: Number of variations to generate (default: 3)
            image_count: Number of images to include placeholders for (default: 0)
            image_paths: Optional list of image file paths to include as context
            temperature: Creativity level (0.0-1.0), higher for more variety
            max_output_tokens: Maximum length of generated content
            
        Returns:
            Dictionary containing list of variations with title and content
            
        Raises:
            Exception: If generation fails
        """
        try:
            # Build image placeholder instruction if images exist
            image_instruction = ""
            if image_count > 0:
                placeholder_list = ', '.join([f'{{{{image_{i}}}}}' for i in range(1, image_count + 1)])
                image_instruction = f"""

【画像プレースホルダー - 必須】
この記事には{image_count}枚の画像が添付されています。
本文中に以下の{image_count}個のプレースホルダーを【必ず全て】配置してください：
{placeholder_list}

配置ルール：
- 全てのプレースホルダーを必ず使用すること（省略厳禁）
- 記事の流れに合った適切な位置に配置する
- プレースホルダーは単独の行に配置する（文中には入れない）
- 画像はヘアスタイルやサロンの雰囲気を伝えるものです"""

            system_instruction = f"""あなたは美容サロンのブログライターです。
ユーザーからのリクエストに基づいて、{num_variations}種類の異なる魅力的なブログ記事を作成してください。

各記事の要件：
- タイトルは20文字以内で、クリックを誘うワード（例: 失敗しない/〇選/人気/最新版/簡単 等）を1つ以上入れる
- 本文は400-500文字程度（最大800文字厳守）
- How to/ポイント解説系かスタイルまとめ系のいずれかに適切に振り分け、読者が実行しやすい・イメージしやすい構成にする
- 読みやすい段落構成（適切に改行を入れる）
- 専門用語は適度に説明を加える
- ポジティブで親しみやすいトーン
- 3つの記事はそれぞれ異なる切り口・アプローチで書く{image_instruction}

出力形式：
必ず以下のJSON形式のみで返してください（説明文は不要）：
{{
  "variations": [
    {{
      "title": "記事タイトル1",
      "content": "記事本文1（改行は\\nで表現）"
    }},
    {{
      "title": "記事タイトル2",
      "content": "記事本文2（改行は\\nで表現）"
    }},
    {{
      "title": "記事タイトル3",
      "content": "記事本文3（改行は\\nで表現）"
    }}
  ]
}}

重要：
- JSON以外の文字列は出力しないでください
- 必ず{num_variations}個の記事を生成してください
- 各記事は必ずtitleとcontentを含めてください"""

            logger.info(f"Generating {num_variations} content variations with Gemini (images: {image_count}) for prompt: {prompt[:100]}...")

            # Build contents with optional image parts
            contents: List[Any] = [prompt]

            if image_paths:
                for idx, image_path in enumerate(image_paths, start=1):
                    try:
                        data = Path(image_path).read_bytes()
                        mime_type, _ = mimetypes.guess_type(image_path)
                        mime_type = mime_type or 'image/jpeg'

                        contents.append(
                            types.Part.from_bytes(
                                data=data,
                                mime_type=mime_type,
                            )
                        )
                        # Provide lightweight text context for the image order/name
                        contents.append(f"Image {idx}: {Path(image_path).name}")
                    except Exception as img_err:
                        logger.warning(f"Failed to attach image {image_path}: {img_err}")

                logger.info(f"Attached {len(contents) - 1} content parts to Gemini (including images).")

            response = self.client.models.generate_content(
                model=self.model_id,
                contents=contents if len(contents) > 1 else prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    response_mime_type="application/json",
                    system_instruction=system_instruction,
                )
            )

            logger.debug(f"Response type: {type(response)}")
            logger.debug(f"Response text: {response.text[:500] if response and response.text else 'None'}...")

            if not response or not response.text:
                logger.error(f"Empty response from Gemini API. Response: {response}")
                raise Exception("Empty response from Gemini API")

            # Parse response with robust JSON extraction
            result = self._extract_json_from_text(response.text)
            
            if result is None:
                logger.error(f"Failed to extract JSON from response: {response.text[:500]}...")
                raise Exception("Failed to parse Gemini response as JSON")

            # Validate and clean the result
            variations = []
            raw_variations = result.get('variations', [])
            
            if not raw_variations:
                # Handle case where result is a single article
                if 'title' in result and 'content' in result:
                    raw_variations = [result]
                else:
                    raise Exception("No variations found in response")
            
            for i, var in enumerate(raw_variations[:num_variations]):
                title = var.get('title', f'記事案 {i + 1}')
                content = var.get('content', '')
                
                # Clean and format content
                cleaned_content = self._clean_content(content)
                
                # Ensure all image placeholders are present
                if image_count > 0:
                    cleaned_content = self._ensure_image_placeholders(cleaned_content, image_count)
                
                variations.append({
                    'id': i + 1,
                    'title': title[:25] if title else f'記事案 {i + 1}',  # Ensure max 25 chars
                    'content': cleaned_content,
                })

            # Ensure we have the requested number of variations
            while len(variations) < num_variations:
                variations.append({
                    'id': len(variations) + 1,
                    'title': f'記事案 {len(variations) + 1}',
                    'content': '生成に失敗しました。再度お試しください。',
                })

            logger.info(f"Successfully generated {len(variations)} content variations")

            return {
                'variations': variations,
                'model': self.model_id,
                'success': True,
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.error(f"Response text: {response.text if response else 'None'}")
            raise Exception(f"AI response parsing failed: {str(e)}")

        except Exception as e:
            logger.error(f"Gemini content generation failed: {e}")
            raise Exception(f"AI content generation failed: {str(e)}")
