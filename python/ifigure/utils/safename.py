import re
import unicodedata

def safename(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = value.decode('utf-8', 'surrogateescape')
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    valee = re.sub(r'[-\s]+', '-', value)
    return value
