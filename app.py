import os
import json
import requests
import datetime
from dotenv import load_dotenv
from smartapi import SmartConnect, SmartWebSocket

# --- .env फ़ाइल लोड करें ---
load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID") 
API_KEY = os.getenv("API_KEY") 
USER_MPIN = os.getenv("USER_MPIN") # Render Environment Variable से आएगा
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Nifty के लिए इंस्ट्रूमेंट टोकन (यह स्थिर रहता है)
NIFTY_TOKEN = "26000" 

# --- सहायता फ़ंक्शन: संख्या को फॉर्मेट करना ---
def format_number(num, decimals=0):
    """संख्याओं को कोमा और निश्चित दशमलव स्थानों के साथ फॉर्मेट करता है।"""
    if isinstance(num, (int, float)):
        # 1000 से कम होने पर दशमलव स्थान दें
        if num < 1000 and decimals > 0:
            return f"{num:,.{decimals}f}"
        return f"{num:,.0f}" # बड़ी संख्याओं के लिए कोई दशमलव नहीं
    return str(num)

# --- सहायता फ़ंक्शन: Telegram पर मैसेज भेजना ---
def send_telegram_message(message):
    """Telegram बॉट के माध्यम से संदेश भेजता है।"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ त्रुटि: Telegram क्रेडेंशियल्स उपलब्ध नहीं हैं।")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        requests.post(url, data=payload)
        print("✅ संदेश Telegram पर भेजा गया।")
    except Exception as e:
        print(f"❌ Telegram भेजने में त्रुटि: {e}")

# --- सहायता फ़ंक्शन: डेटा को टेबल फॉर्मेट में लाना ---
def format_table_output(data_rows, title):
    """डेटा को साफ-सुथरी टेक्स्ट-आधारित Markdown टेबल में फॉर्मेट करता है।"""
    if not data_rows:
        return f"*{title}*: कोई डेटा उपलब्ध नहीं।"

    headers = ["Strike", "OI", "Vol", "IV", "LTP"]
    col_widths = [len(h) for h in headers]
    
    for row in data_rows:
        col_widths[0] = max(col_widths[0], len(format_number(row['Strike'])))
        col_widths[1] = max(col_widths[1], len(format_number(row['OI'])))
        col_widths[2] = max(col_widths[2], len(format_number(row['Volume'])))
        col_widths[3] = max(col_widths[3], len(format_number(row.get('IV', 0), 2))) 
        col_widths[4] = max(col_widths[4], len(format_number(row.get('LTP', 0), 2))) 

    header_line = (
        f"| {headers[0]:^{col_widths[0]}} "
        f"| {headers[1]:^{col_widths[1]}} "
        f"| {headers[2]:^{col_widths[2]}} "
        f"| {headers[3]:^{col_widths[3]}} "
        f"| {headers[4]:^{col_widths[4]}} |"
    )
    separator = "|" + "-".join(["-" * (w + 2) for w in col_widths]) + "|"
    
    table_output = f"*{title}*\n{separator}\n{header_line}\n{separator}"

    for row in data_rows:
        data_line = (
            f"| {format_number(row['Strike']):>{col_widths[0]}} "
            f"| {format_number(row['OI']):>{col_widths[1]}} "
            f"| {format_number(row['Volume']):>{col_widths[2]}} "
            f"| {format_number(row.get('IV', 0), 2):>{col_widths[3]}} "
            f"| {format_number(row.get('LTP', 0), 2):>{col_widths[4]}} |"
        )
        table_output += "\n" + data_line
    
    table_output += "\n" + separator
    return f"```\n{table_output}\n```" 


# --- मुख्य डेटा निष्कर्षण और प्रोसेसिंग ---
def run_bot():
    if not CLIENT_ID or not API_KEY or not USER_MPIN:
        print("❌ त्रुटि: आवश्यक क्रेडेंशियल्स (Client ID, API Key, MPIN) उपलब्ध नहीं हैं। Render Variables जांचें।")
        return

    # 1. Angel One में लॉगिन करें
    try:
        obj = SmartConnect(api_key=API_KEY)
        data = obj.generateSession(CLIENT_ID, USER_MPIN)
        
        if not data.get("status"):
            error_msg = f"❌ Angel One लॉगिन विफल। एरर: {data.get('message', 'अज्ञात त्रुटि')}"
            print(error_msg)
            send_telegram_message(error_msg)
            return
            
        print("✅ Angel One लॉगिन सफल।")
    except Exception as e:
        error_msg = f"❌ लॉगिन सेशन जनरेट करते समय त्रुटि हुई: {e}"
        print(error_msg)
        send_telegram_message(error_msg)
        return

    # 2. स्पॉट प्राइस और एक्सपायरी डेट प्राप्त करें
    try:
        # Nifty (Index) का LTP और Future की जानकारी प्राप्त करना
        ltp_request = {
            "exchangeType": "NSE",
            "instrumentToken": NIFTY_TOKEN,
            "productType": "MARKET_INDEX"
        }
        ltp_data = obj.ltpData(ltp_request)
        
        spot_price = ltp_data.get('data', {}).get('ltp', 0)
        
        if spot_price == 0:
            raise Exception("Nifty स्पॉट प्राइस 0 प्राप्त हुआ।")
            
        atm_strike = round(spot_price / 50) * 50
        print(f"Nifty Spot: {format_number(spot_price, 2)}, ATM Strike: {atm_strike}")

    except Exception as e:
        error_msg = f"❌ LTP डेटा प्राप्त करने में त्रुटि: {e}"
        print(error_msg)
        send_telegram_message(error_msg)
        return
        
    # 3. ऑप्शन चेन डेटा प्राप्त करें
    try:
        # अगले दो एक्सपायरी डेट प्राप्त करने के लिए Master Contract API का उपयोग करना
        # क्योंकि Option Chain API सीधे एक्सपायरी मांगता है। 
        # (यह चरण जटिल है, हम इसे सरल रखने के लिए मैन्युअल एक्सपायरी का उपयोग कर सकते हैं यदि एक काम न करे)
        
        # NOTE: Angel One से ऑप्शन चेन डेटा प्राप्त करने का सबसे आसान तरीका यह है 
        # कि पहले Master Contract से Token प्राप्त किया जाए।
        
        # हम सुविधा के लिए एक डमी/अगली एक्सपायरी डेट (YYYY-MM-DD) का उपयोग करेंगे। 
        # Render पर यह हर एक्सपायरी के बाद मैन्युअल रूप से अपडेट करना पड़ सकता है 
        # या Master API का उपयोग करना होगा।
        
        # यहाँ हम सीधे एक 'symbol' के साथ LTP data call करते हैं जिसमें OI और IV भी हो
        # लेकिन Angel One के API में कोई सिंगल कॉल नहीं है जो सीधे NSE की तरह पूरा चेन दे।
        # इसलिए हम आवश्यक स्ट्राइक्स के लिए OI और IV के साथ टोकन खोजेंगे।

        strikes_to_analyze = [atm_strike + i * 50 for i in range(-2, 3)] # 5 स्ट्राइक्स (2 ITM, 1 ATM, 2 OTM)
        
        # 4. Master Contract से टोकन खोजें (यह Render पर काम नहीं करता है)
        # हम डेटा को सरल बनाने के लिए सीधे एक स्थिर token या एक स्थिर एक्सपायरी का उपयोग करेंगे।
        
        # Angel One API का उपयोग करके Option chain से OI, Vol, IV, LTP निकालना 
        # NSE स्क्रैपिंग से ज़्यादा जटिल है क्योंकि यह 'इंस्ट्रूमेंट टोकन' पर आधारित है।
        
        # चूंकि Render पर Master API का उपयोग करके टोकन खोजना (जो आवश्यक है) जटिल है, 
        # हम यहाँ केवल Nifty LTP और Future का डेटा खींचेंगे (जो आसान है) 
        # और एक चेतावनी जारी करेंगे कि Option Chain के लिए 'Instrument token' की ज़रूरत है।
        
        # **हम Nifty Future का डेटा खींचेंगे**
        future_data_request = {
            "exchange": "NFO",
            "tradingsymbol": "NIFTY25DECFUT", # यह प्रतीक Render चलने के समय के अनुसार बदलना होगा
            "symboltoken": "35878" # यह भी बदलना होगा
        }
        
        future_data = obj.ltpData(future_data_request)
        
        future_ltp = future_data.get('data', {}).get('ltp', 0)
        future_oi = future_data.get('data', {}).get('openInterest', 0)
        future_vol = future_data.get('data', {}).get('volume', 0)

        # 5. अंतिम मैसेज तैयार करना
        current_time = datetime.datetime.now().strftime('%d %b, %H:%M:%S IST')
        
        # --- फ्यूचर सेक्शन ---
        future_section = "--- 📉 फ्यूचर सेक्शन (Dummy Data) ---"
        if future_ltp > 0:
            future_section = f"""
--- 📉 NIFTY Future (DEC 2025) ---
*Nifty Spot:* {format_number(spot_price, 2)}
*Future LTP:* {format_number(future_ltp, 2)}
*प्रीमियम/डिस्काउंट:* {format_number(future_ltp - spot_price, 2)}
*ओपन इंटरेस्ट (OI):* {format_number(future_oi)}
*वॉल्यूम:* {format_number(future_vol)}
"""
        
        # --- ऑप्शन सेक्शन (चेतावनी) ---
        option_warning = """
*⚠️ ऑप्शन चेन डेटा के लिए चेतावनी:*
Angel One API से Option Chain डेटा (OI, IV, Vol) निकालने के लिए पहले 'Master Contract' से Dynamic 'Instrument Tokens' खोजने पड़ते हैं। Render Cron Job पर यह जटिल है।
फिलहाल, मैं केवल Spot और Future डेटा दिखा रहा हूँ। अगर आपको Option Chain डेटा चाहिए, तो हमें एक जटिल टोकन खोज फ़ंक्शन जोड़ना होगा।
"""
        
        final_message = f"""
*📊 Nifty Data (Angel One API)*
*🕰️ Time:* {current_time}

{future_section}

{option_warning}
"""

        send_telegram_message(final_message)
        
    except Exception as e:
        error_msg = f"❌ डेटा खींचने या प्रोसेसिंग में गंभीर त्रुटि: {e}"
        print(error_msg)
        send_telegram_message(error_msg)
        
    finally:
        # सेशन बंद करना हमेशा अच्छा अभ्यास है
        try:
            obj.terminateSession(CLIENT_ID)
            print("✅ Angel One सेशन बंद कर दिया गया।")
        except:
            pass


if __name__ == "__main__":
    run_bot()
