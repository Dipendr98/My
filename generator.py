import random

def luhn_checksum(card_number):
    """Calculates the Luhn checksum for a card number."""
    digits = [int(d) for d in str(card_number)]
    checksum = 0
    reverse_digits = digits[::-1]
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum

def generate_luhn_last_digit(card_number_prefix):
    """Generates the correct last digit to satisfy the Luhn algorithm."""
    checksum = luhn_checksum(card_number_prefix + "0")
    last_digit = (10 - (checksum % 10)) % 10
    return str(last_digit)

def generate_cards(bin_str, count=10):
    """Generates a list of random credit cards based on a BIN (16 digits)."""
    if len(bin_str) < 6:
        return []
        
    generated_cards = []
    
    # Normalize count
    count = min(max(1, count), 100)
    
    # Identify Card Brand for CVV length (Amex = 4, others = 3)
    # Even if Amex is usually 15 digits, user asked for 16, so we enforce 16 and 4 CVV for 3xx
    cvv_len = 3
    if bin_str.startswith('3'):
        cvv_len = 4
    
    for _ in range(count):
        # Enforce 16 digits: BIN (6) + Random (9) + Checksum (1) = 16
        random_part = "".join([str(random.randint(0, 9)) for _ in range(15 - len(bin_str))])
        
        prefix = bin_str + random_part
        check_digit = generate_luhn_last_digit(prefix)
        
        card_number = prefix + check_digit
        month = str(random.randint(1, 12)).zfill(2)
        year = str(random.randint(2025, 2030))
        cvv = "".join([str(random.randint(0, 9)) for _ in range(cvv_len)])
        
        generated_cards.append(f"{card_number}|{month}|{year}|{cvv}")
        
    return generated_cards
