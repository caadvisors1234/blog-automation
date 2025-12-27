# -*- coding: utf-8 -*-
"""
Utility functions for the blog application.
"""
import re

def smart_truncate(text, max_length):
    """
    Truncate text to max_length, attempting to cut at the nearest punctuation mark
    to avoid mid-word cutoffs.
    
    Args:
        text (str): The text to truncate
        max_length (int): The maximum allowed length
        
    Returns:
        str: The truncated text
    """
    if not text:
        return ""
        
    if len(text) <= max_length:
        return text

    # No suffix needed
    # The original logic for target_length was to reserve space for the suffix.
    # Since there's no suffix, the target_length is simply max_length.
    target_length = max_length 
    
    if target_length <= 0:
        # If max_length is very small, just return prefix
        return text[:max_length]

    # Initial cut
    truncated = text[:target_length]
    
    # Try to find the last punctuation mark
    # Prioritize sentence endings: 。 ? !
    # Then pauses: 、 , 
    # Regex to find last punctuation mark
    # matches unicode punctuation
    
    # Japanese punctuation: 。 、 ！ ？
    # English punctuation: . , ! ?
    
    # Search for the last punctuation in the truncated text
    # We scan backwards
    punct_pattern = r'[。、！？!?,.]'
    matches = list(re.finditer(punct_pattern, truncated))
    
    if matches:
        last_match = matches[-1]
        # Check if cutting here would result in too much loss (e.g. > 30% of target length lost?)
        # User wants to avoid weird cuts, so getting a clean sentence is usually better than filling space with garbage.
        # But if we lose too much, maybe it's better to just hard cut?
        # Let's say if we preserve at least 50% of the target length, it's worth it.
        # Otherwise, just hard cut with suffix.
        
        cut_point = last_match.end()
        if cut_point >= target_length * 0.5:
            # We found a good cut point
            # For sentence endings (。！？!?), we don't necessarily need a suffix if it looks complete
            # But for commas (、,), a suffix is definitely needed.
            
            char = last_match.group()
            is_sentence_end = char in ['。', '！', '？', '!', '?', '.']
            
            if is_sentence_end:
                 # If it ends with a sentence ender, we might not need '...' but sticking to consisteny logic:
                 # If we truncated the ORIGINAL text, we should probably indicate it unless we ended exactly at a sentence end of the original too.
                 # But here we are creating a new string.
                 
                 # If we cut at a sentence end, checking if the NEXT character in original text was also a sentence start?
                 # Actually, usually '...' is good to indicate there was more.
                 pass
            
            # The original code added a suffix here. Now we just return the truncated part.
            return truncated[:cut_point]

    # Fallback: Just hard cut
    return truncated

