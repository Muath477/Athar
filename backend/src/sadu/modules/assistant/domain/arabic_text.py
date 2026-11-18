import re

DIACRITICS = re.compile("[\u064b-\u0652\u0640]")
LETTER_FORMS = str.maketrans("أإآةى", "اااهي")


def normalize_ar(text: str) -> str:
    return DIACRITICS.sub("", text).translate(LETTER_FORMS).lower()


ARABIC_DIGITS = str.maketrans("0123456789.", "٠١٢٣٤٥٦٧٨٩٫")


def digits_ar(value: object) -> str:
    return str(value).translate(ARABIC_DIGITS)


def count_ar(count: int, *, one: str, two: str, few: str, many: str, zero: str) -> str:
    if count == 0:
        return zero
    if count == 1:
        return one
    if count == 2:
        return two
    if 3 <= count % 100 <= 10:
        return f"{digits_ar(count)} {few}"
    return f"{digits_ar(count)} {many}"


def elements_ar(count: int) -> str:
    return count_ar(count, zero="لا عناصر تلف", one="عنصر واحد", two="عنصران", few="عناصر", many="عنصرًا")
