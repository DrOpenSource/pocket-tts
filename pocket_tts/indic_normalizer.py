"""Hindi, Hinglish and English text normalization for the app.

Reads digits, times, currencies and ordinals as words, expands abbreviations, and spells English
loanwords and Romanized Hindi in Devanagari, with a grapheme-to-phoneme fallback for unlisted words.

This is `personal-dev` code. It lives apart from `text_chunking.py`, which upstream edits often, and
from upstream's per-model `pocket_tts/text_normalization/`.
"""

import re
from collections.abc import Callable

_HINDI_NUMBERS_0_99 = {
    0: "शून्य",
    1: "एक",
    2: "दो",
    3: "तीन",
    4: "चार",
    5: "पाँच",
    6: "छह",
    7: "सात",
    8: "आठ",
    9: "नौ",
    10: "दस",
    11: "ग्यारह",
    12: "बारह",
    13: "तेरह",
    14: "चौदह",
    15: "पंद्रह",
    16: "सोलह",
    17: "सत्रह",
    18: "अठारह",
    19: "उन्नीस",
    20: "बीस",
    21: "इक्कीस",
    22: "बाईस",
    23: "तेईस",
    24: "चौबीस",
    25: "पच्चीस",
    26: "छब्बीस",
    27: "सत्ताईस",
    28: "अट्ठाईस",
    29: "उनतीस",
    30: "तीस",
    31: "इकतीस",
    32: "बत्तीस",
    33: "तैंतीस",
    34: "चौंतीस",
    35: "पैंतीस",
    36: "छत्तीस",
    37: "सैंतीस",
    38: "अड़तीस",
    39: "उनतालीस",
    40: "चालीस",
    41: "इकतालीस",
    42: "बयालीस",
    43: "तैंतालीस",
    44: "चौवालीस",
    45: "पैंतालीस",
    46: "छियालीस",
    47: "सैंतालीस",
    48: "अड़तालीस",
    49: "उनचास",
    50: "पचास",
    51: "इक्यावन",
    52: "बावन",
    53: "तिरेपन",
    54: "चौवन",
    55: "पचपन",
    56: "छप्पन",
    57: "सत्तावन",
    58: "अट्ठावन",
    59: "उनसठ",
    60: "साठ",
    61: "इकसठ",
    62: "बासठ",
    63: "तिरेसठ",
    64: "चौंसठ",
    65: "पैंसठ",
    66: "छियासठ",
    67: "सरसठ",
    68: "अड़सठ",
    69: "उनहत्तर",
    70: "सत्तर",
    71: "इकहत्तर",
    72: "बहत्तर",
    73: "तिहत्तर",
    74: "चौहत्तर",
    75: "पचहत्तर",
    76: "छिहत्तर",
    77: "सतहत्तर",
    78: "अठहत्तर",
    79: "उन्नासी",
    80: "अस्सी",
    81: "इक्यासी",
    82: "बयासी",
    83: "तिरासी",
    84: "चौरासी",
    85: "पचासी",
    86: "छियासी",
    87: "सत्तासी",
    88: "अठासी",
    89: "नवासी",
    90: "नब्बे",
    91: "इक्यानवे",
    92: "बानवे",
    93: "तिरानवे",
    94: "चौरानवे",
    95: "पंचानवे",
    96: "छियानवे",
    97: "सत्तानवे",
    98: "अट्ठानवे",
    99: "निन्यानवे",
    100: "सौ",
}

_ENGLISH_NUMBERS_0_19 = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
]
_ENGLISH_TENS = [
    "",
    "",
    "twenty",
    "thirty",
    "forty",
    "fifty",
    "sixty",
    "seventy",
    "eighty",
    "ninety",
]

_DEVANAGARI_DIGITS_TRANS = str.maketrans("०१२३४५६७८९", "0123456789")


def _number_to_hindi(num: int) -> str:
    if num in _HINDI_NUMBERS_0_99:
        return _HINDI_NUMBERS_0_99[num]
    if num < 1000:
        h, rem = divmod(num, 100)
        res = f"{_HINDI_NUMBERS_0_99.get(h, str(h))} सौ"
        return f"{res} {_number_to_hindi(rem)}" if rem else res
    if num < 100000:
        th, rem = divmod(num, 1000)
        res = f"{_number_to_hindi(th)} हज़ार"
        return f"{res} {_number_to_hindi(rem)}" if rem else res
    if num < 10000000:
        lakh, rem = divmod(num, 100000)
        res = f"{_number_to_hindi(lakh)} लाख"
        return f"{res} {_number_to_hindi(rem)}" if rem else res
    cr, rem = divmod(num, 10000000)
    res = f"{_number_to_hindi(cr)} करोड़"
    return f"{res} {_number_to_hindi(rem)}" if rem else res


def _number_to_english(num: int) -> str:
    if 0 <= num < 20:
        return _ENGLISH_NUMBERS_0_19[num]
    if 20 <= num < 100:
        tens, rem = divmod(num, 10)
        return f"{_ENGLISH_TENS[tens]}-{_ENGLISH_NUMBERS_0_19[rem]}" if rem else _ENGLISH_TENS[tens]
    if 100 <= num < 1000:
        h, rem = divmod(num, 100)
        res = f"{_ENGLISH_NUMBERS_0_19[h]} hundred"
        return f"{res} {_number_to_english(rem)}" if rem else res
    if 1000 <= num < 1000000:
        th, rem = divmod(num, 1000)
        res = f"{_number_to_english(th)} thousand"
        return f"{res} {_number_to_english(rem)}" if rem else res
    return str(num)


_HINDI_ORDINALS = {
    1: "पहला",
    2: "दूसरा",
    3: "तीसरा",
    4: "चौथा",
    5: "पाँचवाँ",
    6: "छठा",
    7: "सातवाँ",
    8: "आठवाँ",
    9: "नौवाँ",
    10: "दसवाँ",
}

_HINDI_COMMON_ABBR = {
    "AI": "एआई",
    "ML": "एमएल",
    "CEO": "सीईओ",
    "CTO": "सीटीओ",
    "HR": "एचआर",
    "Dr.": "डॉक्टर",
    "Mr.": "मिस्टर",
    "Mrs.": "मिसेज",
    "PM": "पीएम",
    "AM": "एएम",
    "OTP": "ओटीपी",
    "KYC": "केवाईसी",
    "OK": "ओके",
    "vs": "बनाम",
    "vs.": "बनाम",
    "API": "एपीआई",
    "UI": "यूआई",
    "UX": "यूएक्स",
    "ID": "आईडी",
    "PIN": "पिन",
    "URL": "यूआरएल",
    "PDF": "पीडीएफ",
    "PPT": "पीपीटी",
    "SIM": "सिम",
    "GPS": "जीपीएस",
    "VPN": "वीपीएन",
    "WiFi": "वाईफाई",
    "wifi": "वाईफाई",
}

_ROMAN_HINDI_WORDS: dict[str, str] = {
    "kal": "कल",
    "aaj": "आज",
    "kar": "कर",
    "karna": "करना",
    "karo": "करो",
    "karein": "करें",
    "dena": "देना",
    "do": "दो",
    "de": "दे",
    "lena": "लेना",
    "lo": "लो",
    "le": "ले",
    "hai": "है",
    "hain": "हैं",
    "ho": "हो",
    "hoga": "होगा",
    "hogi": "होगी",
    "nahi": "नहीं",
    "nahin": "नहीं",
    "mat": "मत",
    "mera": "मेरा",
    "meri": "मेरी",
    "mere": "मेरे",
    "aap": "आप",
    "tum": "तुम",
    "hum": "हम",
    "tera": "तेरा",
    "teri": "तेरी",
    "tere": "तेरे",
    "yeh": "यह",
    "woh": "वह",
    "ka": "का",
    "ke": "के",
    "ki": "की",
    "ko": "को",
    "se": "से",
    "me": "में",
    "mein": "में",
    "par": "पर",
    "aur": "और",
    "bhi": "भी",
    "kya": "क्या",
    "kyon": "क्यों",
    "kab": "कब",
    "kahan": "कहाँ",
    "kaise": "कैसे",
    "kuch": "कुछ",
    "bahut": "बहुत",
    "sab": "सब",
    "saath": "साथ",
    "liye": "लिए",
    "pehle": "पहले",
    "baad": "बाद",
    "sirf": "सिर्फ",
    "thora": "थोड़ा",
    "thoda": "थोड़ा",
    "bhej": "भेज",
    "bhejo": "भेजो",
    "bhejna": "भेजना",
    "batao": "बताओ",
    "bolo": "बोलो",
    "dekho": "देखो",
    "sun": "सुन",
    "suno": "सुनो",
    "accha": "अच्छा",
    "achha": "अच्छा",
    "theek": "ठीक",
    "thik": "ठीक",
    "baje": "बजे",
    "mujhe": "मुझे",
    "kripya": "कृपया",
    "zaroor": "ज़रूर",
    "namaste": "नमस्ते",
    "dhanyawad": "धन्यवाद",
}

_ROMAN_HINDI_STOPWORDS = set(_ROMAN_HINDI_WORDS.keys())

_HINGLISH_LOANWORDS: dict[str, str] = {
    # Meetings & Scheduling
    "reschedule": "रीशेड्यूल",
    "rescheduled": "रीशेड्यूल्ड",
    "rescheduling": "रीशेड्यूलिंग",
    "schedule": "शेड्यूल",
    "scheduled": "शेड्यूल्ड",
    "scheduling": "शेड्यूलिंग",
    "meeting": "मीटिंग",
    "meetings": "मीटिंग्स",
    "appointment": "अपॉइंटमेंट",
    "appointments": "अपॉइंटमेंट्स",
    "deadline": "डेडलाइन",
    "deadlines": "डेडलाइन्स",
    "cancel": "कैंसिल",
    "cancelled": "कैंसिल्ड",
    "canceling": "कैंसलिंग",
    "cancellation": "कैंसिलेशन",
    "confirm": "कन्फर्म",
    "confirmed": "कन्फर्मड",
    "confirmation": "कन्फर्मेशन",
    "postpone": "पोस्टपोन",
    "postponed": "पोस्टपोंड",
    # Communication & Tech
    "link": "लिंक",
    "links": "लिंक्स",
    "updated": "अपडेटेड",
    "update": "अपडेट",
    "updates": "अपडेट्स",
    "message": "मैसेज",
    "messages": "मैसेजेस",
    "call": "कॉल",
    "calls": "कॉल्स",
    "calling": "कॉलिंग",
    "email": "ईमेल",
    "emails": "ईमेल्स",
    "chat": "चैट",
    "chats": "चैट्स",
    "video": "वीडियो",
    "videos": "वीडियोज",
    "audio": "ऑडियो",
    "audios": "ऑडियोज",
    "share": "शेयर",
    "shared": "शेयर्ड",
    "sharing": "शेयरिंग",
    "send": "सेंड",
    "sent": "सेंट",
    "sending": "सेंडिंग",
    "check": "चेक",
    "checked": "चेक्ड",
    "checking": "चेकिंग",
    "online": "ऑनलाइन",
    "offline": "ऑफलाइन",
    "download": "डाउनलोड",
    "downloaded": "डाउनलोडेड",
    "upload": "अपलोड",
    "uploaded": "अपलोडेड",
    "login": "लॉगिन",
    "logout": "लॉगआउट",
    "password": "पासवर्ड",
    "account": "अकाउंट",
    "accounts": "अकाउंट्स",
    "profile": "प्रोफाइल",
    "notification": "नोटिफिकेशन",
    "notifications": "नोटिफिकेशन्स",
    "status": "स्टेटस",
    "report": "रिपोर्ट",
    "reports": "रिपोर्ट्स",
    "feedback": "फीडबैक",
    "review": "रिव्यू",
    "reviews": "रिव्यूज",
    # Work & Business
    "office": "ऑफिस",
    "project": "प्रोजेक्ट",
    "projects": "प्रोजेक्ट्स",
    "client": "क्लाइंट",
    "clients": "क्लाइंट्स",
    "team": "टीम",
    "teams": "टीम्स",
    "presentation": "प्रेजेंटेशन",
    "presentations": "प्रेजेंटेशन्स",
    "problem": "प्रॉब्लम",
    "problems": "प्रॉब्लम्स",
    "issue": "इश्यू",
    "issues": "इश्यूज",
    "urgent": "अर्जेंट",
    "urgently": "अर्जेंटली",
    "important": "इम्पॉर्टेंट",
    "approved": "अप्रूव्ड",
    "approve": "अप्रूव",
    "approval": "अप्रूवल",
    "pending": "पेंडिंग",
    "reject": "रिजेक्ट",
    "rejected": "रिजेक्टेड",
    "interview": "इंटरव्यू",
    "manager": "मैनेजर",
    "developer": "डेवलपर",
    "design": "डिजाइन",
    "system": "सिस्टम",
    "service": "सर्विस",
    "setup": "सेटअप",
    "test": "टेस्ट",
    "testing": "टेस्टिंग",
    "verified": "वेरीफाइड",
    "verify": "वेरीफाई",
    "connect": "कनेक्ट",
    "connected": "कनेक्टेड",
    "network": "नेटवर्क",
    "server": "सर्वर",
    "website": "वेबसाइट",
    "app": "ऐप",
    "apps": "ऐप्स",
    "document": "डॉक्यूमेंट",
    "documents": "डॉक्यूमेंट्स",
    "file": "फाइल",
    "files": "फाइल्स",
    "folder": "फ़ोल्डर",
    # Common Conversational
    "plan": "प्लान",
    "plans": "प्लान्स",
    "simple": "सिंपल",
    "busy": "बिजी",
    "free": "फ्री",
    "fast": "फास्ट",
    "slow": "स्लो",
    "please": "प्लीज",
    "thanks": "थैंक्स",
    "thank you": "थैंक यू",
    "welcome": "वेलकम",
    "sorry": "सॉरी",
    "hello": "हेलो",
    "ready": "रेडी",
    "done": "डन",
    "start": "स्टार्ट",
    "stop": "स्टॉप",
    # Irregular / Everyday Borrowed Words (High-Frequency Overrides)
    "receipt": "रिसीट",
    "receipts": "रिसीट्स",
    "assignment": "असाइनमेंट",
    "assignments": "असाइनमेंट्स",
    "budget": "बजट",
    "budgets": "बजट्स",
    "hospital": "हॉस्पिटल",
    "hospitals": "हॉस्पिटल्स",
    "doctor": "डॉक्टर",
    "doctors": "डॉक्टर्स",
    "computer": "कंप्यूटर",
    "computers": "कंप्यूटर्स",
    "laptop": "लैपटॉप",
    "laptops": "लैपटॉप्स",
    "flight": "फ्लाइट",
    "flights": "फ्लाइट्स",
    "ticket": "टिकट",
    "tickets": "टिकट्स",
    "station": "स्टेशन",
    "stations": "स्टेशन्स",
    "train": "ट्रेन",
    "trains": "ट्रेन्स",
    "bus": "बस",
    "buses": "बसें",
    "metro": "मेट्रो",
    "car": "कार",
    "cars": "कार्स",
    "police": "पुलिस",
    "ambulance": "एंबुलेंस",
    "medicine": "मेडिसिन",
    "medicines": "मेडिसिन्स",
    "clinic": "क्लीनिक",
    "bank": "बैंक",
    "banks": "बैंक्स",
    "discount": "डिस्काउंट",
    "discounts": "डिस्काउंट्स",
    "payment": "पेमेंट",
    "payments": "पेमेंट्स",
    "invoice": "इनवॉयस",
    "invoices": "इनवॉयसेस",
    "salary": "सैलरी",
    "bonus": "बोनस",
    "queue": "कतार",
    "colleague": "कलीग",
    "colleagues": "कलीग्स",
    "submit": "सबमिट",
    "submitted": "सबमिटेड",
    "submitting": "सबमिटिंग",
    "compulsory": "कंपलसरी",
    "mandatory": "मेंडेटरी",
}

_LOANWORD_SORTED_KEYS = sorted(_HINGLISH_LOANWORDS.keys(), key=len, reverse=True)
_LOANWORD_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _LOANWORD_SORTED_KEYS) + r")\b", re.IGNORECASE
)

# Algorithmic G2P (Grapheme-to-Phoneme) fallback rules for arbitrary English words
_G2P_PREFIXES = [
    (r"^com", "कंप"),
    (r"^con", "कन"),
    (r"^sub", "सब"),
    (r"^sus", "सस"),
    (r"^dis", "डिस"),
    (r"^mis", "मिस"),
    (r"^pre", "प्रि"),
    (r"^per", "पर"),
    (r"^dep", "डिप"),
    (r"^rep", "रिप"),
    (r"^ex", "एक्स"),
    (r"^in", "इन"),
    (r"^un", "अन"),
]

_G2P_SILENT_INITIALS = [
    (r"^ps", "s"),
    (r"^pn", "n"),
    (r"^kn", "n"),
    (r"^wr", "r"),
    (r"^gn", "n"),
    (r"^wh", "w"),
]

_G2P_SUFFIXES = [
    (r"isation\b", "ाइजेशन"),
    (r"ization\b", "ाइजेशन"),
    (r"ational\b", "ेशनल"),
    (r"ation\b", "ेशन"),
    (r"ition\b", "िशन"),
    (r"ution\b", "्यूशन"),
    (r"ction\b", "क्शन"),
    (r"ption\b", "प्शन"),
    (r"sion\b", "शन"),
    (r"tion\b", "शन"),
    (r"izing\b", "ाइजिंग"),
    (r"ising\b", "ाइजिंग"),
    (r"ized\b", "ाइज्ड"),
    (r"ised\b", "ाइज्ड"),
    (r"ize\b", "ाइज"),
    (r"ise\b", "ाइज"),
    (r"ture\b", "चर"),
    (r"ment\b", "मेंट"),
    (r"able\b", "एबल"),
    (r"ible\b", "इबल"),
    (r"ology\b", "ऑलॉजी"),
    (r"graphy\b", "ग्राफी"),
    (r"fully\b", "फुली"),
    (r"ful\b", "फुल"),
    (r"less\b", "लेस"),
    (r"ness\b", "नेस"),
    (r"ship\b", "शिप"),
    (r"ward\b", "वर्ड"),
    (r"wise\b", "वाइज"),
    (r"ical\b", "िकल"),
    (r"ing\b", "िंग"),
    (r"ight\b", "ाइट"),
    (r"ound\b", "ाउंड"),
    (r"ould\b", "ुड"),
    (r"ance\b", "ांस"),
    (r"ence\b", "ेंस"),
    (r"ency\b", "ेंसी"),
    (r"ancy\b", "ांसी"),
    (r"ity\b", "िटी"),
    (r"tive\b", "टिव"),
    (r"sive\b", "सिव"),
    (r"ory\b", "री"),
    (r"ary\b", "री"),
    (r"ous\b", "अस"),
    (r"ious\b", "ियस"),
    (r"ive\b", "िव"),
]

_G2P_CHUNKS = [
    ("ign", ("ाइन", "ाइन")),
    ("eipt", ("ीट", "ीट")),
    ("dge", ("ज", "ज")),
    ("tch", ("च", "च")),
    ("sch", ("स्क", "स्क")),
    ("ck", ("क", "क")),
    ("ph", ("फ", "फ")),
    ("sh", ("श", "श")),
    ("ch", ("च", "च")),
    ("th", ("थ", "थ")),
    ("qu", ("क्व", "क्व")),
    ("wh", ("व", "व")),
    ("ng", ("ंग", "ंग")),
    ("nk", ("ंक", "ंक")),
    ("ee", ("ई", "ी")),
    ("ea", ("ई", "ी")),
    ("oo", ("ऊ", "ू")),
    ("ai", ("ए", "े")),
    ("ay", ("ए", "े")),
    ("ey", ("ए", "े")),
    ("oi", ("ऑय", "ॉय")),
    ("oy", ("ऑय", "ॉय")),
    ("ou", ("आउ", "ाउ")),
    ("ow", ("ओ", "ो")),
    ("oa", ("ओ", "ो")),
    ("au", ("ऑ", "ॉ")),
    ("aw", ("ऑ", "ॉ")),
    ("ia", ("िया", "िया")),
    ("io", ("ियो", "ियो")),
    ("b", ("ब", "ब")),
    ("c", ("क", "क")),
    ("d", ("ड", "ड")),
    ("f", ("फ", "फ")),
    ("g", ("ग", "ग")),
    ("h", ("ह", "ह")),
    ("j", ("ज", "ज")),
    ("k", ("क", "क")),
    ("l", ("ल", "ल")),
    ("m", ("म", "म")),
    ("n", ("न", "न")),
    ("p", ("प", "प")),
    ("q", ("क", "क")),
    ("r", ("र", "र")),
    ("s", ("स", "स")),
    ("t", ("ट", "ट")),
    ("v", ("व", "व")),
    ("w", ("व", "व")),
    ("x", ("क्स", "क्स")),
    ("y", ("य", "य")),
    ("z", ("ज़", "ज़")),
    ("a", ("अ", "ा")),
    ("e", ("ए", "े")),
    ("i", ("इ", "ि")),
    ("o", ("ओ", "ो")),
    ("u", ("उ", "ु")),
]

_G2P_VOWEL_CHUNKS = {
    "a",
    "e",
    "i",
    "o",
    "u",
    "ee",
    "ea",
    "oo",
    "ai",
    "ay",
    "ey",
    "oi",
    "oy",
    "ou",
    "ow",
    "oa",
    "au",
    "aw",
    "ia",
    "io",
    "ign",
    "eipt",
}


def transliterate_english_to_devanagari(word: str) -> str:
    """
    Algorithmic G2P transliterator converting arbitrary English words into Devanagari phonetics.
    Handles prefixes, suffixes, silent letters, soft consonants, and syllable structure.
    """
    clean = word.lower().strip()
    if not clean:
        return ""

    if clean in _HINGLISH_LOANWORDS:
        return _HINGLISH_LOANWORDS[clean]

    w = clean
    for pat, rep in _G2P_SILENT_INITIALS:
        w = re.sub(pat, rep, w)

    prefix_deva = ""
    for pat, deva in _G2P_PREFIXES:
        m = re.search(pat, w)
        if m:
            prefix_deva = deva
            w = w[m.end() :]
            break

    suffix_deva = ""
    for pat, deva in _G2P_SUFFIXES:
        m = re.search(pat, w)
        if m:
            suffix_deva = deva
            w = w[: m.start()]
            break

    if not w:
        return prefix_deva + suffix_deva

    # Soft C (c -> s before e, i, y)
    chars = list(w)
    for i in range(len(chars)):
        if chars[i] == "c" and i + 1 < len(chars) and chars[i + 1] in ("e", "i", "y"):
            chars[i] = "s"
    w = "".join(chars)

    # Magic 'e' at end of stem (e.g. site, code, fine)
    magic_e = False
    v_deva_indep, v_deva_matra = "ए", "े"
    if len(w) >= 3 and w.endswith("e") and w[-2] not in "aeiou" and w[-3] in "aeiou":
        v = w[-3]
        magic_e = True
        if v == "a":
            v_deva_indep, v_deva_matra = "ए", "े"
        elif v == "i":
            v_deva_indep, v_deva_matra = "आइ", "ाइ"
        elif v == "o":
            v_deva_indep, v_deva_matra = "ओ", "ो"
        elif v == "u":
            v_deva_indep, v_deva_matra = "यू", "्यू"
        else:
            v_deva_indep, v_deva_matra = "ए", "े"

    res: list[str] = []
    if prefix_deva:
        res.append(prefix_deva)
        prev_was_consonant = False
    else:
        prev_was_consonant = False

    idx = 0
    while idx < len(w):
        if magic_e and idx == len(w) - 3:
            if not prev_was_consonant:
                res.append(v_deva_indep)
            else:
                res.append(v_deva_matra)
            c = w[idx + 1]
            c_deva = {
                "b": "ब",
                "d": "ड",
                "f": "फ",
                "g": "ग",
                "k": "क",
                "l": "ल",
                "m": "म",
                "n": "न",
                "p": "प",
                "r": "र",
                "s": "स",
                "t": "ट",
                "v": "व",
                "z": "ज़",
            }.get(c, "ट")
            res.append(c_deva)
            break

        matched = False
        for chunk, (indep, matra) in _G2P_CHUNKS:
            if w.startswith(chunk, idx):
                if chunk in _G2P_VOWEL_CHUNKS:
                    if prev_was_consonant:
                        res.append(matra)
                    else:
                        res.append(indep)
                    prev_was_consonant = False
                else:
                    if prev_was_consonant and not res[-1].endswith("्") and not res[-1].endswith("ं"):
                        res.append("्")
                    res.append(indep)
                    prev_was_consonant = True

                idx += len(chunk)
                matched = True
                break

        if not matched:
            idx += 1

    return "".join(res) + suffix_deva


# A time, not part of a longer number such as "1:30:05".
_TIME = r"(?<![\w.,:])(\d{1,2}):(\d\d)(?![\w:]|[.,]\d)"
_ENGLISH_TIME = re.compile(_TIME)
# The time reading says बजे itself, so a typed बजे or Romanized baje is consumed with the time.
_HINDI_TIME = re.compile(_TIME + r"(?:\s*(?:बजे|baje\b))?", re.IGNORECASE)
# A whole number token ("1,250", "822.95") with an optional currency sign, scale word, percent sign
# or ordinal suffix. Commas and periods belong to the token, so a number is never read in halves.
_NUMBER_START = r"(?<![\w.,:])({currency})?(\d[\d,.]*\d|\d)(\s(?:{scales})(?![\wऀ-ॿ]))?"
_NUMBER_END = r"(?:\s*(%)|(st|nd|rd|th)(?!\w)|(?!\w|:\d))"
_HINDI_NUMBER = re.compile(
    _NUMBER_START.format(currency=r"₹\s*|\$\s*", scales="हज़ार|हजार|लाख|करोड़") + _NUMBER_END,
    re.IGNORECASE,
)
_ENGLISH_NUMBER = re.compile(
    _NUMBER_START.format(currency=r"\$\s*", scales="thousand|million|billion|trillion")
    + _NUMBER_END,
    re.IGNORECASE,
)
# Colon-joined digits that are not a time, like "16:9": read digit run by digit run.
_COLON_NUMBERS = re.compile(r"(?<![\w.,:])\d+(?::\d+)+(?![\w:])")
# Indian "1,25,000" or Western "125,000" grouping.
_HINDI_GROUPING = re.compile(r"\d{1,3}(?:,\d\d)*,\d{3}")
_ENGLISH_GROUPING = re.compile(r"\d{1,3}(?:,\d{3})+")
_ENGLISH_IRREGULAR_ORDINALS = {
    "one": "first",
    "two": "second",
    "three": "third",
    "five": "fifth",
    "eight": "eighth",
    "nine": "ninth",
    "twelve": "twelfth",
}
_HINDI_CURRENCIES = {"₹": "रुपये", "$": "डॉलर"}


def _record(changes: list[dict[str, str]], m: re.Match[str], spoken: str, kind: str) -> str:
    changes.append({"from": m.group(0).strip(), "to": spoken, "type": kind})
    return spoken


def _read_digits(
    digits: str, grouping: re.Pattern[str], cardinal: Callable[[int], str], point: str
) -> str:
    """Read a digit token whole, decimals digit by digit ("3.14" -> "three point one four").

    A token that is not a plain, grouped or decimal number ("1.2.3", "1,2,3") is read one digit run
    at a time rather than left as digits, which the tokenizer may drop.
    """
    whole, dot, decimals = digits.partition(".")
    valid_whole = whole.isdigit() or grouping.fullmatch(whole)
    if not valid_whole or (dot and not decimals.isdigit()):
        return re.sub(r"\d+", lambda run: cardinal(int(run.group(0))), digits)
    words = cardinal(int(whole.replace(",", "")))
    if dot:
        words += f" {point} " + " ".join(cardinal(int(d)) for d in decimals)
    return words


def _read_colon_numbers(m: re.Match[str], cardinal: Callable[[int], str]) -> str:
    return re.sub(r"\d+", lambda run: cardinal(int(run.group(0))), m.group(0))


def _hindi_time(m: re.Match[str], changes: list[dict[str, str]]) -> str:
    hours, minutes = int(m.group(1)), int(m.group(2))
    if hours > 23 or minutes > 59:
        return m.group(0)
    hour = hours % 12 or 12
    spoken_hour = _number_to_hindi(hour)
    if minutes == 0:
        spoken = f"{spoken_hour} बजे"
    elif minutes == 15:
        spoken = f"सवा {spoken_hour} बजे"
    elif minutes == 30:
        spoken = {1: "डेढ़ बजे", 2: "ढाई बजे"}.get(hour, f"साढ़े {spoken_hour} बजे")
    elif minutes == 45:
        spoken = f"पौने {_number_to_hindi(hour % 12 + 1)} बजे"
    else:
        spoken = f"{spoken_hour} बजकर {_number_to_hindi(minutes)} मिनट"
    return _record(changes, m, spoken, "time")


def _hindi_number(m: re.Match[str], changes: list[dict[str, str]]) -> str:
    currency, digits, scale, percent, ordinal_suffix = m.groups()
    scale = scale or ""
    if ordinal_suffix:
        plain = digits.replace(",", "")
        if not plain.isdigit():
            return m.group(0)
        n = int(plain)
        spoken = _HINDI_ORDINALS.get(n, f"{_number_to_hindi(n)}वाँ") + scale
        return _record(changes, m, spoken, "ordinal")
    spoken = _read_digits(digits, _HINDI_GROUPING, _number_to_hindi, "दशमलव") + scale
    if currency:
        return _record(changes, m, f"{spoken} {_HINDI_CURRENCIES[currency.strip()]}", "currency")
    if percent:
        return _record(changes, m, f"{spoken} प्रतिशत", "percentage")
    return _record(changes, m, spoken, "number")


def _english_ordinal(n: int) -> str:
    def last_word(m: re.Match[str]) -> str:
        word = m.group(0)
        if word in _ENGLISH_IRREGULAR_ORDINALS:
            return _ENGLISH_IRREGULAR_ORDINALS[word]
        return word[:-1] + "ieth" if word.endswith("y") else word + "th"

    return re.sub(r"[a-z]+$", last_word, _number_to_english(n))


def _english_time(m: re.Match[str], changes: list[dict[str, str]]) -> str:
    hours, minutes = int(m.group(1)), int(m.group(2))
    if hours > 23 or minutes > 59:
        return m.group(0)
    spoken_hour = _number_to_english(hours)
    if minutes == 0:
        spoken = spoken_hour + (" o'clock" if hours <= 12 else " hundred")
    else:
        spoken = f"{spoken_hour} {'oh ' if minutes < 10 else ''}{_number_to_english(minutes)}"
    return _record(changes, m, spoken, "time")


def _english_number(m: re.Match[str], changes: list[dict[str, str]]) -> str:
    currency, digits, scale, percent, ordinal_suffix = m.groups()
    scale = scale or ""
    plain = digits.replace(",", "")
    # _number_to_english stops at a million: such values stay as they are, not half read.
    if plain.isdigit() and int(plain) >= 1_000_000:
        return m.group(0)
    if ordinal_suffix:
        if not plain.isdigit():
            return m.group(0)
        return _record(changes, m, _english_ordinal(int(plain)) + scale, "ordinal")
    spoken = _read_digits(digits, _ENGLISH_GROUPING, _number_to_english, "point") + scale
    if currency:
        unit = "dollar" if digits == "1" and not scale else "dollars"
        return _record(changes, m, f"{spoken} {unit}", "currency")
    if percent:
        return _record(changes, m, f"{spoken} percent", "percentage")
    return _record(changes, m, spoken, "number")


def normalize_text(text: str, mode: str = "auto") -> tuple[str, list[dict[str, str]]]:
    """Normalize numeric digits, ordinals, currencies, abbreviations, and Hinglish loanwords."""
    changes: list[dict[str, str]] = []
    text = text.translate(_DEVANAGARI_DIGITS_TRANS)

    has_devanagari = bool(re.search(r"[\u0900-\u097F]", text))
    if not has_devanagari and mode == "auto":
        words_in_text = set(re.findall(r"\b[a-zA-Z]+\b", text.lower()))
        is_roman_hinglish = len(words_in_text.intersection(_ROMAN_HINDI_STOPWORDS)) >= 2
    else:
        is_roman_hinglish = False

    is_hi = (mode in ("hindi", "hinglish")) or has_devanagari or is_roman_hinglish

    if is_hi:
        text = _HINDI_TIME.sub(lambda m: _hindi_time(m, changes), text)

        # Common abbreviations
        for abbr, word in _HINDI_COMMON_ABBR.items():
            pattern = r"\b" + re.escape(abbr) + r"\b"
            if re.search(pattern, text):
                text = re.sub(pattern, word, text)
                changes.append({"from": abbr, "to": word, "type": "abbreviation"})

        text = _HINDI_NUMBER.sub(lambda m: _hindi_number(m, changes), text)
        text = _COLON_NUMBERS.sub(lambda m: _read_colon_numbers(m, _number_to_hindi), text)

        # English loanwords in Hindi/Hinglish (e.g. 'reschedule' -> 'रीशेड्यूल', 'meeting' -> 'मीटिंग')
        def _repl_loanword(m: re.Match[str]) -> str:
            matched_key = m.group(1).lower()
            hi_word = _HINGLISH_LOANWORDS[matched_key]
            changes.append({"from": m.group(1), "to": hi_word, "type": "loanword"})
            return hi_word

        text = _LOANWORD_PATTERN.sub(_repl_loanword, text)

        # Fallback for remaining Latin words: check Roman Hindi words first, then algorithmic G2P
        def _repl_latin_word(m: re.Match[str]) -> str:
            raw = m.group(0)
            low = raw.lower()
            if low in _ROMAN_HINDI_WORDS:
                hi = _ROMAN_HINDI_WORDS[low]
                changes.append({"from": raw, "to": hi, "type": "roman_hindi"})
                return hi
            hi = transliterate_english_to_devanagari(raw)
            changes.append({"from": raw, "to": hi, "type": "g2p"})
            return hi

        text = re.sub(r"\b[a-zA-Z]+\b", _repl_latin_word, text)

    else:
        text = _ENGLISH_TIME.sub(lambda m: _english_time(m, changes), text)
        text = _ENGLISH_NUMBER.sub(lambda m: _english_number(m, changes), text)
        text = _COLON_NUMBERS.sub(lambda m: _read_colon_numbers(m, _number_to_english), text)

    return text, changes


def normalize_numbers(text: str, mode: str = "auto") -> str:
    """Normalize numeric digits into spoken words in Hindi or English."""
    normalized, _ = normalize_text(text, mode=mode)
    return normalized
