import re

def extract_cards(text):
    """
    Extracts cards in various formats: cc|mm|yy|cvv, cc:mm:yy:cvv, cc mm yy cvv
    Returns a list of tuples: (cc, mm, yy, cvv)
    """
    if not text:
        return []
        
    # Pattern to match CC|MM|YY|CVV with various delimiters
    # Supports 13-19 digit CC, 2 digit MM, 2 or 4 digit YY, 3-4 digit CVV
    pattern = r'(\d{13,19})[\s\|/:;,\\-]*(\d{2})[\s\|/:;,\\-]*(\d{2,4})[\s\|/:;,\\-]*(\d{3,4})'
    
    matches = re.findall(pattern, text)
    
    results = []
    for m in matches:
        cc, mm, yy, cvv = m
        # Normalize year to 2 digits for consistency if needed, but let's keep it as is for now
        # or normalize to 4 digits for the API
        if len(yy) == 2:
            yy = "20" + yy
        results.append((cc, mm, yy, cvv))
        
    return results
