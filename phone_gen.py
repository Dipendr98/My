import random

AREA_CODES = [
    202, 212, 213, 312, 305, 415, 602, 404, 503, 
    617, 702, 214, 303, 313, 512, 615,
]

def generate_phone_number():
    area_code = random.choice(AREA_CODES)
    phone = f"+1{area_code}{random.randint(200, 999)}{random.randint(1000, 9999)}"
    return phone
