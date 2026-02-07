import random

class UserAgentGenerator:
    def __init__(self):
        self.browsers = ["chrome", "firefox", "safari"]
        self.os_list = ["windows", "mac", "linux"]

    def generate(self, os_type=None):
        if not os_type:
            os_type = random.choice(self.os_list)
        
        if os_type == "windows":
            ver = random.choice(["10.0", "11.0"])
            chrome_ver = f"{random.randint(120, 131)}.0.{random.randint(4000, 6000)}.{random.randint(100, 200)}"
            return f"Mozilla/5.0 (Windows NT {ver}; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36"
        elif os_type == "mac":
            ver = f"10_{random.randint(12, 15)}_{random.randint(0, 7)}"
            chrome_ver = f"{random.randint(120, 131)}.0.{random.randint(4000, 6000)}.{random.randint(100, 200)}"
            return f"Mozilla/5.0 (Macintosh; Intel Mac OS X {ver}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36"
        else:
            chrome_ver = f"{random.randint(120, 131)}.0.{random.randint(4000, 6000)}.{random.randint(100, 200)}"
            return f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36"

ua_generator = UserAgentGenerator()

def get_random_ua():
    return ua_generator.generate()
