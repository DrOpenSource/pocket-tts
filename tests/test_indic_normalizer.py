import pytest

from pocket_tts.indic_normalizer import normalize_numbers, normalize_text


def test_normalize_numbers_hindi():
    assert normalize_numbers("10", mode="hindi") == "दस"
    assert normalize_numbers("₹500", mode="hindi") == "पाँच सौ रुपये"
    assert normalize_numbers("3:30", mode="hindi") == "साढ़े तीन बजे"
    assert normalize_numbers("50%", mode="hindi") == "पचास प्रतिशत"
    assert normalize_numbers("1st", mode="hindi") == "पहला"

    norm, changes = normalize_text("10 लोग और ₹50", mode="hindi")
    assert norm == "दस लोग और पचास रुपये"
    assert len(changes) == 2


def test_normalize_numbers_english():
    assert normalize_numbers("10", mode="english") == "ten"
    assert normalize_numbers("$50", mode="english") == "fifty dollars"
    assert normalize_numbers("50%", mode="english") == "fifty percent"
    assert normalize_numbers("1st", mode="english") == "first"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("3.14 प्रतिशत", "तीन दशमलव एक चार प्रतिशत"),
        ("3.14%", "तीन दशमलव एक चार प्रतिशत"),
        ("₹1,25,000 मिले", "एक लाख पच्चीस हज़ार रुपये मिले"),
        ("₹125,000", "एक लाख पच्चीस हज़ार रुपये"),
        ("₹5 करोड़", "पाँच करोड़ रुपये"),
        ("₹99.50", "निन्यानवे दशमलव पाँच शून्य रुपये"),
        ("1:30 बजे", "डेढ़ बजे"),
        ("2:30", "ढाई बजे"),
        ("3:30", "साढ़े तीन बजे"),
        ("1:30 baje", "डेढ़ बजे"),
        ("3:30 Baje", "साढ़े तीन बजे"),
        ("3:30   BAJE", "साढ़े तीन बजे"),
        ("14:30 बजे", "ढाई बजे"),
        ("13:45", "पौने दो बजे"),
        ("25:99", "पच्चीस:निन्यानवे"),
        ("16:9 स्क्रीन", "सोलह:नौ स्क्रीन"),
        ("50%की", "पचास प्रतिशतकी"),
        ("1,2,3", "एक,दो,तीन"),
    ],
)
def test_normalize_numbers_hindi_whole_tokens(text: str, expected: str):
    assert normalize_numbers(text, mode="hindi") == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("12th floor", "twelfth floor"),
        ("20th", "twentieth"),
        ("21st century", "twenty-first century"),
        ("$1 only", "one dollar only"),
        ("$5 million", "five million dollars"),
        ("$1,250", "one thousand two hundred fifty dollars"),
        ("Meet at 3:30", "Meet at three thirty"),
        ("At 7:05", "At seven oh five"),
        ("At 9:00", "At nine o'clock"),
        ("It costs 1,250 rupees", "It costs one thousand two hundred fifty rupees"),
        ("Pi is 3.14.", "Pi is three point one four."),
        ("2,500,000 people", "2,500,000 people"),
        ("16:9 screen", "sixteen:nine screen"),
    ],
)
def test_normalize_numbers_english_whole_tokens(text: str, expected: str):
    assert normalize_numbers(text, mode="english") == expected


def test_romanized_baje_is_not_doubled_in_hinglish():
    norm, changes = normalize_text("meeting 3:30 baje hai", mode="auto")
    assert norm == "मीटिंग साढ़े तीन बजे है"
    assert {"from": "3:30 baje", "to": "साढ़े तीन बजे", "type": "time"} in changes
    assert not any(c["from"] == "baje" for c in changes)


def test_baje_is_only_consumed_as_a_whole_word():
    norm, _ = normalize_text("3:30 bajega", mode="hindi")
    assert norm.startswith("साढ़े तीन बजे ")
    assert len(norm.split()) == 4

    # A bare hour has no time reading, so its baje stays a word of its own.
    norm, _ = normalize_text("meeting 5 baje hai", mode="auto")
    assert norm == "मीटिंग पाँच बजे है"


def test_number_fixes_keep_abbreviations_transliteration_and_changes():
    norm, changes = normalize_text("KYC meeting 1:30 बजे, ₹1,25,000 और 3.14 प्रतिशत", mode="auto")
    assert norm == "केवाईसी मीटिंग डेढ़ बजे, एक लाख पच्चीस हज़ार रुपये और तीन दशमलव एक चार प्रतिशत"
    kinds = {c["type"] for c in changes}
    assert {"abbreviation", "loanword", "time", "currency", "number"} <= kinds


def test_normalize_hinglish_loanwords():
    text = "कल की meeting 10 बजे reschedule कर देना और updated link मुझे भेज देना।"
    norm, changes = normalize_text(text, mode="auto")
    assert norm == "कल की मीटिंग दस बजे रीशेड्यूल कर देना और अपडेटेड लिंक मुझे भेज देना।"
    assert any(c["from"].lower() == "reschedule" and c["to"] == "रीशेड्यूल" for c in changes)
    assert any(c["from"].lower() == "meeting" and c["to"] == "मीटिंग" for c in changes)
    assert any(c["from"] == "10" and c["to"] == "दस" for c in changes)


def test_normalize_g2p_unlisted_words():
    text = "डॉक्टर ने नया prescription दिया है और distribution शुरू हो गया है।"
    norm, changes = normalize_text(text, mode="auto")
    assert "प्रिस्क्रिप्शन" in norm
    assert "डिस्ट्रिब्यूशन" in norm or "डिसट्रिब्यूशन" in norm
    assert any(c["from"] == "prescription" and c["type"] == "g2p" for c in changes)


def test_normalize_romanized_hinglish():
    text = "kal ki meeting 10 baje reschedule kar dena aur updated link mujhe bhej dena."
    norm, changes = normalize_text(text, mode="auto")
    assert "कल" in norm
    assert "मीटिंग" in norm
    assert "दस बजे" in norm
    assert "रीशेड्यूल" in norm
    assert "अपडेटेड" in norm
    assert "लिंक" in norm
    assert any(c["type"] == "roman_hindi" for c in changes)


def test_english_mode_unaffected():
    text = "This prescription is for the distribution of 50 dollars."
    norm, changes = normalize_text(text, mode="english")
    assert norm == "This prescription is for the distribution of fifty dollars."
    assert not any(c.get("type") in ("g2p", "loanword", "roman_hindi") for c in changes)
