"""
XLIFF Batch Translator dengan DeepL atau Google Cloud Translation API
=======================================================================
Enhanced version implementing WPML XLIFF Translation Playbook rules.

FEATURES:
- DUAL API SUPPORT: DeepL dan Google Cloud Translation
- Smart Title Case with position/city/punctuation detection
- XLIFF Integrity Protection (prevents double-encoding, preserves placeholders)
- WP Admin-Only Settings Protection (JetEngine, Bricks, WPML fields)
- WordPress Block Detection (Accordion, List, Repeater, etc.)
- Legal content optimization

Cara penggunaan:
1. Pilih API provider di variabel TRANSLATION_API ("deepl" atau "google")
2. Masukkan API Key yang sesuai
3. Letakkan file-file XLIFF di folder 'input'
4. Jalankan script: python translate_xliff.py
5. Hasil terjemahan akan tersimpan di folder 'output'
"""

import os
import sys
import re
import time
import html
import json
from pathlib import Path
from datetime import datetime

# Fix encoding untuk Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Import translation libraries (conditional)
DEEPL_AVAILABLE = False
GOOGLE_AVAILABLE = False

try:
    import deepl
    DEEPL_AVAILABLE = True
except ImportError:
    pass

try:
    import requests
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

# ==================== KONFIGURASI ====================
# Pilih API provider: "deepl" atau "google"
TRANSLATION_API = "google"  # <-- GANTI INI UNTUK SWITCH API

# DeepL API Settings
DEEPL_API_KEY = "7d310721-db7e-45b2-9c1f-11071e317678"

# Google Cloud Translation Settings
# Gunakan API Key (dapatkan di Google Cloud Console > APIs & Services > Credentials)
GOOGLE_API_KEY = "AIzaSyB0BMJArddW_3MtVPAzOZSDy9KgHbkXPbc"

# General Settings
DEFAULT_TARGET_LANG = None  # None = wajib baca dari XLIFF
INPUT_FOLDER = "input"
OUTPUT_FOLDER = "output"
DELAY_BETWEEN_REQUESTS = 0.5
DELAY_BETWEEN_FILES = 2
BATCH_SIZE = 10
# =====================================================

# ==================== LANGUAGE CODE MAPPING ====================
# DeepL uses uppercase codes like 'EN-US', Google uses lowercase like 'en'
DEEPL_TO_GOOGLE_LANG = {
    'DE': 'de', 'EN': 'en', 'EN-US': 'en', 'EN-GB': 'en',
    'ES': 'es', 'FR': 'fr', 'IT': 'it', 'PT': 'pt', 'PT-BR': 'pt',
    'NL': 'nl', 'PL': 'pl', 'RU': 'ru', 'JA': 'ja', 'ZH': 'zh',
}

def convert_lang_for_google(lang_code):
    """Convert DeepL language code to Google format."""
    if not lang_code:
        return 'en'
    return DEEPL_TO_GOOGLE_LANG.get(lang_code.upper(), lang_code.lower())
# ==================== END LANGUAGE MAPPING ====================



# ==================== GLOSSARY & CONSTANTS ====================
# Legal terminology glossary (DE -> EN)
LEGAL_GLOSSARY = {
    'Erbrecht': 'Inheritance Law',
    'kanzlei': 'Law Firm',
    'kanzleien': 'Law Firms',
    'kanzleiinhaber': 'Firm Owner',
    'rechtsanwalt': 'Lawyer',
    'rechtsanwälte': 'Lawyers',
    'fachanwalt': 'Specialist Lawyer',
    'fachanwälte': 'Specialist Lawyers',
    'urteil': 'Judgment',
    'urteile': 'Judgments',
    'verhandlung': 'Hearing',
    'verhandlungen': 'Hearings',
    'rückzahlung': 'Refund',
    'rückzahlungen': 'Refunds',
    'verbraucherrecht': 'Consumer Law',
    'notar': 'Notary',
    'richter': 'Judge',
    'staatsanwalt': 'Prosecutor',
    'geschäftsführer': 'Managing Director',
    'kanzleiinhaber': 'Firm Owner',
    'einstellungen': 'Settings',
    'Cookie-einstellungen': 'Cookie Settings',
}

# Spanish-specific legal translations (DE -> ES)
SPANISH_LEGAL_GLOSSARY = {
    'impressum': 'Aviso Legal',
    'datenschutzerklärung': 'Política de Privacidad',
    'cookie-einstellungen': 'Configuración de Cookies',
    'rechtliches': 'Legal',
    'kontaktinformationen': 'Información de Contacto',
}

# Terms that should NEVER be translated
DO_NOT_TRANSLATE = {
    'ZVG', 'BGB', 'StGB', 'GmbH', 'AG', 'UG', 'WPML', 'JetEngine',
    'WordPress', 'Bricks', 'Gutenberg', 'XLIFF', 'HTML', 'CSS',
}

# Job positions - always capitalize
JOB_POSITIONS = {
    'attorney', 'lawyer', 'judge', 'notary', 'prosecutor', 'partner',
    'senior partner', 'managing director', 'firm owner', 'counsel',
    'associate', 'specialist attorney', 'attorney at law', 'founder',
    'co-founder', 'managing partner',
}

# German cities (should always be capitalized)
GERMAN_CITIES = {
    'berlin', 'münchen', 'munich', 'frankfurt', 'hamburg', 'düsseldorf',
    'cologne', 'köln', 'stuttgart', 'dortmund', 'essen', 'bremen',
    'dresden', 'leipzig', 'hannover', 'nürnberg', 'nuremberg',
}

# German states
GERMAN_STATES = {
    'bayern', 'bavaria', 'nordrhein-westfalen', 'hessen', 'sachsen',
    'baden-württemberg', 'niedersachsen', 'rheinland-pfalz',
}

# ==================== CITY & COUNTRY TRANSLATIONS ====================
# Nama kota dan negara diterjemahkan sesuai EYD target language
CITY_TRANSLATIONS = {
    'EN': {  # German -> English
        'münchen': 'Munich',
        'köln': 'Cologne',
        'nürnberg': 'Nuremberg',
        'hannover': 'Hanover',
        'braunschweig': 'Brunswick',
        'mainz': 'Mayence',
        'aachen': 'Aix-la-Chapelle',
        'regensburg': 'Ratisbon',
        'wien': 'Vienna',
        'zürich': 'Zurich',
        'genf': 'Geneva',
        'luzern': 'Lucerne',
        'basel': 'Basle',
        'bern': 'Bern',
        'prag': 'Prague',
        'warschau': 'Warsaw',
        'mailand': 'Milan',
        'venedig': 'Venice',
        'florenz': 'Florence',
        'rom': 'Rome',
        'neapel': 'Naples',
        'lissabon': 'Lisbon',
        'brüssel': 'Brussels',
        'antwerpen': 'Antwerp',
        'kopenhagen': 'Copenhagen',
        'den haag': 'The Hague',
        'peking': 'Beijing',
        'moskau': 'Moscow',
        'athen': 'Athens',
        'kairo': 'Cairo',
    },
    'ES': {  # German -> Spanish
        'münchen': 'Múnich',
        'köln': 'Colonia',
        'nürnberg': 'Núremberg',
        'hannover': 'Hanóver',
        'wien': 'Viena',
        'zürich': 'Zúrich',
        'genf': 'Ginebra',
        'luzern': 'Lucerna',
        'basel': 'Basilea',
        'bern': 'Berna',
        'prag': 'Praga',
        'warschau': 'Varsovia',
        'mailand': 'Milán',
        'venedig': 'Venecia',
        'florenz': 'Florencia',
        'rom': 'Roma',
        'neapel': 'Nápoles',
        'lissabon': 'Lisboa',
        'brüssel': 'Bruselas',
        'antwerpen': 'Amberes',
        'kopenhagen': 'Copenhague',
        'den haag': 'La Haya',
        'peking': 'Pekín',
        'moskau': 'Moscú',
        'athen': 'Atenas',
        'kairo': 'El Cairo',
    },
}

STATE_TRANSLATIONS = {
    'EN': {  # German -> English
        'bayern': 'Bavaria',
        'nordrhein-westfalen': 'North Rhine-Westphalia',
        'niedersachsen': 'Lower Saxony',
        'baden-württemberg': 'Baden-Württemberg',
        'rheinland-pfalz': 'Rhineland-Palatinate',
        'sachsen': 'Saxony',
        'sachsen-anhalt': 'Saxony-Anhalt',
        'schleswig-holstein': 'Schleswig-Holstein',
        'mecklenburg-vorpommern': 'Mecklenburg-Western Pomerania',
        'thüringen': 'Thuringia',
        'brandenburg': 'Brandenburg',
        'saarland': 'Saarland',
        'hessen': 'Hesse',
    },
    'ES': {  # German -> Spanish
        'bayern': 'Baviera',
        'nordrhein-westfalen': 'Renania del Norte-Westfalia',
        'niedersachsen': 'Baja Sajonia',
        'baden-württemberg': 'Baden-Wurtemberg',
        'rheinland-pfalz': 'Renania-Palatinado',
        'sachsen': 'Sajonia',
        'sachsen-anhalt': 'Sajonia-Anhalt',
        'thüringen': 'Turingia',
        'hessen': 'Hesse',
    },
}

COUNTRY_TRANSLATIONS = {
    'EN': {  # German -> English
        'deutschland': 'Germany',
        'österreich': 'Austria',
        'schweiz': 'Switzerland',
        'frankreich': 'France',
        'spanien': 'Spain',
        'italien': 'Italy',
        'niederlande': 'Netherlands',
        'belgien': 'Belgium',
        'polen': 'Poland',
        'tschechien': 'Czech Republic',
        'ungarn': 'Hungary',
        'griechenland': 'Greece',
        'türkei': 'Turkey',
        'russland': 'Russia',
        'china': 'China',
        'japan': 'Japan',
        'vereinigte staaten': 'United States',
        'usa': 'USA',
        'grossbritannien': 'Great Britain',
        'vereinigtes königreich': 'United Kingdom',
    },
    'ES': {  # German -> Spanish
        'deutschland': 'Alemania',
        'österreich': 'Austria',
        'schweiz': 'Suiza',
        'frankreich': 'Francia',
        'spanien': 'España',
        'italien': 'Italia',
        'niederlande': 'Países Bajos',
        'belgien': 'Bélgica',
        'polen': 'Polonia',
        'tschechien': 'República Checa',
        'ungarn': 'Hungría',
        'griechenland': 'Grecia',
        'türkei': 'Turquía',
        'russland': 'Rusia',
        'china': 'China',
        'japan': 'Japón',
        'vereinigte staaten': 'Estados Unidos',
        'usa': 'EE.UU.',
        'grossbritannien': 'Gran Bretaña',
        'vereinigtes königreich': 'Reino Unido',
    },
}
# ==================== END CITY & COUNTRY TRANSLATIONS ====================

# Title case exceptions (lowercase unless first/last word)
TITLE_CASE_MINOR_WORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'via',
}

# Technical patterns to skip
SKIP_TECHNICAL_PATTERNS = [
    r'^\{[a-z_]+\}$',           # Field tokens like {je_field}
    r'^[a-z0-9]{5,8}$',          # Internal IDs
    r'^[a-z]+-[a-z-]+$',         # CSS class patterns
    r'^_[a-z_]+$',               # Meta key patterns
    r'^\d+$',                    # Numeric IDs
    r'^(true|false|none|auto|flex|block|inherit|visible|hidden)$',
    r'^[a-z0-9_/-]+\.(php|css|js|png|jpg|svg|webp)$',  # File paths
]

# WP Admin-only field patterns (NEVER translate)
WP_ADMIN_PROTECTED_PATTERNS = [
    # JetEngine
    r'\{je_[^}]+\}',
    r'^jet-engine/',
    r'^jet_engine_',
    r'^_jet_',
    # Bricks Builder
    r'^bricks_',
    r'^_bricks_',
    r'^brx-',
    r'^brxe-',
    # WPML Internal
    r'^wpml_',
    r'^_icl_',
    r'^icl_translations',
    r'^translation_id',
    r'^trid$',
    r'^element_type$',
    # WordPress Core
    r'^_edit_lock$',
    r'^_edit_last$',
    r'^_wp_trash_',
    r'^_wp_old_slug$',
    r'^_wp_attached_file$',
    r'^_wp_attachment_metadata$',
    # Parent-Child relationships
    r'.*\bParent$',
    r'.*\bChildren$',
    r'^parent$',
    r'^post_parent$',
    r'^menu_order$',
]
# ==================== END CONSTANTS ====================


def setup_folders():
    """Membuat folder input dan output jika belum ada."""
    Path(INPUT_FOLDER).mkdir(exist_ok=True)
    Path(OUTPUT_FOLDER).mkdir(exist_ok=True)
    print(f"[OK] Folder '{INPUT_FOLDER}' dan '{OUTPUT_FOLDER}' siap digunakan")


def get_xliff_files():
    """Mendapatkan semua file XLIFF dari folder input."""
    xliff_extensions = ['.xliff', '.xlf']
    files = []
    for ext in xliff_extensions:
        files.extend(Path(INPUT_FOLDER).glob(f"*{ext}"))
    return sorted(files)


def translate_batch(translator, texts, target_lang):
    """
    Menerjemahkan batch teks menggunakan API yang dipilih.
    Mendukung DeepL dan Google Cloud Translation.
    """
    if not texts:
        return []
    
    non_empty_indices = []
    non_empty_texts = []
    for i, text in enumerate(texts):
        if text and text.strip():
            non_empty_indices.append(i)
            non_empty_texts.append(text)
    
    if not non_empty_texts:
        return texts
    
    try:
        time.sleep(DELAY_BETWEEN_REQUESTS)
        
        if TRANSLATION_API == "google" and GOOGLE_AVAILABLE:
            # Google Cloud Translation REST API
            google_target = convert_lang_for_google(target_lang)
            translated_texts = []
            
            for text in non_empty_texts:
                # Use REST API endpoint
                url = f"https://translation.googleapis.com/language/translate/v2?key={GOOGLE_API_KEY}"
                payload = {
                    "q": text,
                    "target": google_target,
                    "format": "html"  # Use "html" to preserve HTML tags like <strong>, <em>, etc.
                }
                response = requests.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                translated_texts.append(result['data']['translations'][0]['translatedText'])
            
            translated = list(texts)
            for idx, trans_text in zip(non_empty_indices, translated_texts):
                # Decode HTML entities from Google
                translated[idx] = html.unescape(trans_text)
            
            return translated
            
        else:
            # DeepL API (default)
            # Use tag_handling='html' to preserve HTML tags like <strong>, <em>, etc.
            results = translator.translate_text(non_empty_texts, target_lang=target_lang, tag_handling='html')
            
            translated = list(texts)
            for idx, result in zip(non_empty_indices, results):
                translated[idx] = result.text
            
            return translated
        
    except Exception as e:
        error_msg = str(e).lower()
        
        # Handle DeepL specific errors
        if DEEPL_AVAILABLE and TRANSLATION_API == "deepl":
            if 'quota' in error_msg:
                print("\n[ERROR] Kuota DeepL habis!")
                raise
            if 'too many requests' in error_msg:
                print("\n[WAIT] Too many requests, waiting 10 seconds...")
                time.sleep(10)
                return translate_batch(translator, texts, target_lang)
        
        # Handle Google specific errors
        if 'quota' in error_msg or 'limit' in error_msg:
            print(f"\n[ERROR] API quota/limit reached!")
            raise
        
        print(f"\n[!] Error translating batch: {str(e)[:100]}")
        return texts


def extract_cdata_content(text):
    """Mengekstrak konten dari CDATA section."""
    if text is None:
        return None, False
    
    cdata_match = re.match(r'^\s*<!\[CDATA\[(.*?)\]\]>\s*$', text, re.DOTALL)
    if cdata_match:
        return cdata_match.group(1), True
    return text, False


def wrap_in_cdata(text, was_cdata):
    """Membungkus text dalam CDATA jika sebelumnya CDATA."""
    if was_cdata and text:
        return f"<![CDATA[{text}]]>"
    return text


# ==================== SMART TITLE CASE ====================
def is_job_position(word):
    """Check if word is a job position."""
    return word.lower() in JOB_POSITIONS


def is_city_or_location(word):
    """Check if word is a city or location name."""
    word_lower = word.lower()
    return word_lower in GERMAN_CITIES or word_lower in GERMAN_STATES


def is_abbreviation(word):
    """Check if word is an abbreviation that should preserve case."""
    # All caps words with 2+ characters
    if len(word) >= 2 and word.isupper():
        return True
    # Known abbreviations
    if word.upper() in DO_NOT_TRANSLATE:
        return True
    # Legal reference patterns
    if re.match(r'^§\s*\d+', word):
        return True
    if re.match(r'^Az\.\s*', word, re.IGNORECASE):
        return True
    if re.match(r'^Art\.\s*\d+', word, re.IGNORECASE):
        return True
    return False


def smart_title_case(text):
    """
    Apply intelligent title case following the workflow rules:
    - Capitalize nouns, verbs, adjectives, adverbs
    - Don't capitalize articles, conjunctions, prepositions (unless first/last)
    - Always capitalize job positions and city names
    - Preserve abbreviations and technical terms
    - Handle punctuation correctly
    """
    if not text:
        return text
    
    # Skip if text contains technical patterns
    technical_skip_patterns = [
        r'\{[^}]+\}',           # Bricks/CSS variables
        r'#[a-zA-Z0-9-_]+',     # CSS IDs
        r'\.[a-zA-Z0-9-_]+\s',  # CSS classes
        r':\s*\d+',             # CSS values
        r'transform:',
        r'margin:',
        r'padding:',
        r'position:',
        r'display:',
    ]
    
    for pattern in technical_skip_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return text
    
    # Skip if text is a technical identifier
    if re.match(r'^[a-z][a-z0-9]*[-_][a-z0-9_-]+$', text):
        return text
    
    # Skip CSS class selectors
    if re.match(r'^(brx|brxe|cr)[-_]', text.lower()):
        return text
    
    # Skip single technical words
    skip_words = {
        'toggle', 'visible', 'hidden', 'internal', 'external', 'click', 'hover',
        'flex', 'none', 'block', 'inline', 'absolute', 'relative', 'static',
        'left', 'right', 'center', 'top', 'bottom', 'span', 'div', 'ul', 'li',
        'svg', 'wpmenu', 'themify', 'queryloopextras'
    }
    if text.lower() in skip_words:
        return text
    
    words = text.split()
    result_words = []
    prev_ends_sentence = False
    
    for i, word in enumerate(words):
        is_first = (i == 0)
        is_last = (i == len(words) - 1)
        
        # Check for sentence-ending punctuation from previous word
        after_sentence_end = prev_ends_sentence
        prev_ends_sentence = bool(re.search(r'[.!?:]\s*$', word))
        
        # Skip technical words with underscore or multiple hyphens
        if '_' in word or word.count('-') > 1:
            result_words.append(word)
            continue
        
        # Preserve abbreviations
        if is_abbreviation(word):
            result_words.append(word)
            continue
        
        # Always capitalize job positions
        word_lower = word.lower().rstrip('.,;:!?')
        if word_lower in JOB_POSITIONS:
            # Capitalize and preserve trailing punctuation
            punctuation = ''
            if word[-1] in '.,;:!?':
                punctuation = word[-1]
                word = word[:-1]
            result_words.append(word.title() + punctuation)
            continue
        
        # Always capitalize cities and locations
        if is_city_or_location(word_lower):
            punctuation = ''
            if word[-1] in '.,;:!?':
                punctuation = word[-1]
                word = word[:-1]
            result_words.append(word.title() + punctuation)
            continue
        
        # Skip CSS ID patterns
        if word.startswith('#') or word.startswith('.'):
            result_words.append(word)
            continue
        
        # Title case rules
        clean_word = word.lower().rstrip('.,;:!?')
        
        # First word, last word, or after sentence-ending punctuation: always capitalize
        if is_first or is_last or after_sentence_end:
            result_words.append(word.capitalize())
        # Minor words: don't capitalize
        elif clean_word in TITLE_CASE_MINOR_WORDS:
            result_words.append(word.lower())
        # All other words: capitalize
        else:
            result_words.append(word.capitalize())
    
    return ' '.join(result_words)


def is_title_case(text):
    """Detect if source text is using title case."""
    if not text or len(text.strip()) < 2:
        return False
    
    # Skip technical patterns
    for pattern in SKIP_TECHNICAL_PATTERNS:
        if re.search(pattern, text):
            return False
    
    words = text.strip().split()
    if not words:
        return False
    
    title_case_words = 0
    total_meaningful_words = 0
    
    for i, word in enumerate(words):
        if not any(c.isalpha() for c in word):
            continue
        
        first_alpha = None
        for c in word:
            if c.isalpha():
                first_alpha = c
                break
        
        if not first_alpha:
            continue
            
        total_meaningful_words += 1
        
        if i == 0:
            if first_alpha.isupper():
                title_case_words += 1
        elif word.lower() in TITLE_CASE_MINOR_WORDS:
            title_case_words += 1
        elif first_alpha.isupper():
            title_case_words += 1
    
    if total_meaningful_words < 2:
        if total_meaningful_words == 1 and words[0][0].isupper():
            return True
        return False
    
    return (title_case_words / total_meaningful_words) >= 0.7
# ==================== END SMART TITLE CASE ====================


# ==================== XLIFF INTEGRITY PROTECTION ====================
def validate_xliff_structure(content):
    """
    Validate XLIFF structure to prevent corruption.
    Returns (is_valid, error_message)
    """
    errors = []
    
    # Check for double-encoded entities
    if re.search(r'&amp;(amp|lt|gt|quot|#)', content):
        errors.append("Double-encoded HTML entities detected")
    
    # Check for broken CDATA
    cdata_opens = content.count('<![CDATA[')
    cdata_closes = content.count(']]>')
    if cdata_opens != cdata_closes:
        errors.append(f"Mismatched CDATA sections: {cdata_opens} opens, {cdata_closes} closes")
    
    # Check for XML declaration
    if not content.strip().startswith('<?xml'):
        errors.append("Missing XML declaration")
    
    return (len(errors) == 0, errors)


def fix_entity_encoding(text, is_cdata=False):
    """
    Fix HTML entity encoding to prevent WPML import failures.
    
    For CDATA: bare & is valid, no encoding needed
    For non-CDATA: single encode to &amp;
    """
    if not text:
        return text
    
    # First, decode any double-encoded entities
    # &amp;amp; -> &amp; -> &
    decoded = text
    max_iterations = 3  # Prevent infinite loop
    for _ in range(max_iterations):
        new_decoded = html.unescape(decoded)
        if new_decoded == decoded:
            break
        decoded = new_decoded
    
    if is_cdata:
        # CDATA content doesn't need encoding
        return decoded
    else:
        # Non-CDATA needs proper XML encoding
        # Encode & but don't double-encode existing entities
        result = decoded.replace('&', '&amp;')
        # Fix common entities that got double-encoded
        result = result.replace('&amp;lt;', '&lt;')
        result = result.replace('&amp;gt;', '&gt;')
        result = result.replace('&amp;quot;', '&quot;')
        result = result.replace('&amp;apos;', '&apos;')
        return result


def count_placeholders(text):
    """Count XLIFF placeholders in text for validation."""
    if not text:
        return {}
    
    counts = {
        'ph': len(re.findall(r'<ph[^>]*/?>', text)),
        'g': len(re.findall(r'<g[^>]*>', text)),
        'x': len(re.findall(r'<x[^>]*/?>', text)),
        'bx': len(re.findall(r'<bx[^>]*/?>', text)),
        'ex': len(re.findall(r'<ex[^>]*/?>', text)),
        'bpt': len(re.findall(r'<bpt[^>]*>', text)),
        'ept': len(re.findall(r'<ept[^>]*>', text)),
    }
    return counts
# ==================== END XLIFF INTEGRITY ====================


# ==================== WP ADMIN PROTECTION ====================
def is_wp_admin_protected(resname, source_text):
    """
    Check if this field is a WP Admin-only setting that should NEVER be translated.
    These include JetEngine fields, Bricks settings, WPML internal fields, etc.
    """
    if not resname and not source_text:
        return False
    
    # Check resname patterns
    if resname:
        for pattern in WP_ADMIN_PROTECTED_PATTERNS:
            if re.search(pattern, resname, re.IGNORECASE):
                return True
    
    # Check source text patterns
    if source_text:
        # JetEngine field tokens
        if re.match(r'^\{je_[^}]+\}$', source_text):
            return True
        
        # Check technical patterns
        for pattern in SKIP_TECHNICAL_PATTERNS:
            if re.match(pattern, source_text, re.IGNORECASE):
                return True
    
    return False


def is_parent_child_field(resname):
    """Check if this is a parent-child relationship field."""
    if not resname:
        return False
    
    parent_child_patterns = [
        r'.*\bParent\b',
        r'.*\bChildren\b',
        r'.*\bparent\b',
        r'.*\bchildren\b',
        r'.*post_parent\b',
        r'.*menu_order\b',
        r'.*_thumbnail_id\b',
        r'.*_wp_page_template\b',
    ]
    
    for pattern in parent_child_patterns:
        if re.match(pattern, resname, re.IGNORECASE):
            return True
    
    return False
# ==================== END WP ADMIN PROTECTION ====================


# ==================== WORDPRESS BLOCK DETECTION ====================
def detect_wordpress_block_type(resname, source_text):
    """
    Detect WordPress block type from resname and content.
    Returns: (block_type, is_translatable)
    """
    if not resname:
        return ('unknown', True)
    
    resname_lower = resname.lower()
    
    wp_block_patterns = {
        'accordion': (
            ['accordion', 'accordion-item', 'accordion:::ueberschrift', 'accordion:::überschrift', 
             'accordion:::title', 'accordion:::content', 'accordion:::text'],
            True
        ),
        'list': (
            ['item:::text', 'item:::bullet', 'item:::punkte', ':::points', ':::items',
             'schwerpunkte:::bullet', 'tipps:::bullet', 'ueberblick:::punkte', 'überblick:::punkte'],
            True
        ),
        'repeater': (
            ['0 item:::', '1 item:::', '2 item:::', '3 item:::', '4 item:::', 
             '5 item:::', '6 item:::', '7 item:::', '8 item:::', '9 item:::',
             'mitgliedschaften:::tooltip:::text', 'werdegang:::text', 'werdegang:::jahr',
             'in den medien:::text', 'in:::den:::medien:::text', 'in:::den:::medien:::datum'],
            True
        ),
        'table': (
            ['table:::cell', 'table:::header', 'tabelle:::zelle', 'tabelle:::kopf'],
            True
        ),
        'gallery': (
            ['gallery:::caption', 'galerie:::beschriftung', 'image:::alt', 'image:::caption',
             'bild:::alt', 'bild:::beschriftung'],
            True
        ),
        'quote': (
            ['quote:::text', 'quote:::citation', 'zitat:::text', 'zitat:::quelle',
             'pullquote', 'blockquote'],
            True
        ),
        'button': (
            ['button:::text', 'button:::label', 'schaltfläche:::text', 'link:::text'],
            True
        ),
        'media_text': (
            ['media-text:::content', 'medien-text:::inhalt'],
            True
        ),
        'columns': (
            ['column:::content', 'spalte:::inhalt'],
            True
        ),
        'cover': (
            ['cover:::text', 'cover:::heading', 'abdeckung:::text'],
            True
        ),
        'heading': (
            ['heading', 'überschrift', 'ueberschrift', 'titel', 'title'],
            True
        ),
        'paragraph': (
            ['beschreibungstext', 'beschreibung', 'text:::content', 'paragraph',
             'absatz', 'inhalt', 'content'],
            True
        ),
        'tooltip': (
            ['tooltip:::text', 'popup:::text', 'hinweis:::text'],
            True
        ),
        'section_visibility': (
            ['sektionen ein ausblenden', 'ein ausblenden', 'sektion:::', 'sichtbarkeit'],
            False
        ),
        'technical': (
            [':::id', ':::name', ':::class', ':::slug', ':::key', ':::type',
             'field-id', 'element-id', 'block-id'],
            False
        ),
    }
    
    for block_type, (patterns, is_translatable) in wp_block_patterns.items():
        for pattern in patterns:
            if pattern in resname_lower:
                return (block_type, is_translatable)
    
    return ('unknown', True)


def is_accordion_content(resname):
    """Detect if resname is accordion content."""
    if not resname:
        return (False, None, None)
    
    resname_lower = resname.lower()
    accordion_indicators = ['accordion', 'akkordeon', 'toggle', 'collapsible', 'expandable']
    
    for indicator in accordion_indicators:
        if indicator in resname_lower:
            if any(x in resname_lower for x in ['ueberschrift', 'überschrift', 'title', 'header', 'label']):
                return (True, 'title', None)
            elif any(x in resname_lower for x in ['text', 'content', 'inhalt', 'body']):
                return (True, 'content', None)
            else:
                return (True, 'unknown', None)
    
    return (False, None, None)


def is_list_item_content(resname):
    """Detect if resname is a list item."""
    if not resname:
        return (False, None, None)
    
    resname_lower = resname.lower()
    list_indicators = [
        ':::bullet', ':::punkte', ':::item', ':::element', 
        'schwerpunkte', 'aufgaben', 'leistungen', 'vorteile'
    ]
    
    for indicator in list_indicators:
        if indicator in resname_lower:
            match = re.search(r'(\d+)\s*(?:item|element|punkt)', resname_lower)
            item_index = int(match.group(1)) if match else None
            return (True, 'bullet', item_index)
    
    return (False, None, None)


def is_repeater_field_content(resname):
    """Detect if resname is a repeater field."""
    if not resname:
        return (False, None, None)
    
    repeater_pattern = re.match(
        r'.*?(\d+)\s*Item:::(\d+)\s*([^:]+):::(.+)$',
        resname,
        re.IGNORECASE
    )
    
    if repeater_pattern:
        return (True, int(repeater_pattern.group(2)), repeater_pattern.group(4))
    
    simple_pattern = re.match(r'.*?\s+(\d+)\s+Item:::', resname, re.IGNORECASE)
    if simple_pattern:
        return (True, int(simple_pattern.group(1)), None)
    
    return (False, None, None)
# ==================== END WORDPRESS BLOCK DETECTION ====================


def should_skip_translation(resname, source_text):
    """
    Determine if trans-unit should be skipped from translation.
    Implements all protection rules from the workflow.
    """
    if not source_text:
        return True
    
    source_text = source_text.strip()
    
    if not source_text:
        return True
    
    # Priority 1: Check WP Admin protected fields
    if is_wp_admin_protected(resname, source_text):
        return True
    
    # Priority 2: Check parent-child relationship fields
    if is_parent_child_field(resname):
        return True
    
    # Priority 3: WordPress block detection
    if resname:
        block_type, is_translatable = detect_wordpress_block_type(resname, source_text)
        
        if block_type != 'unknown' and is_translatable:
            # Still skip if content is technical
            if source_text.lower() in ['true', 'false']:
                return True
            if source_text.isnumeric():
                return True
            if re.match(r'^https?://', source_text):
                return True
            if re.match(r'^\{[^}]+\}$', source_text):
                return True
            return False
        
        if block_type in ['section_visibility', 'technical']:
            return True
        
        # Accordion content
        is_accordion, _, _ = is_accordion_content(resname)
        if is_accordion:
            if source_text.lower() in ['true', 'false'] or source_text.isnumeric():
                return True
            return False
        
        # List content
        is_list, _, _ = is_list_item_content(resname)
        if is_list:
            if source_text.lower() in ['true', 'false'] or source_text.isnumeric():
                return True
            return False
        
        # Repeater content
        is_repeater, _, field_name = is_repeater_field_content(resname)
        if is_repeater:
            if field_name:
                field_lower = field_name.lower()
                skip_fields = ['id', 'url', 'filename', 'file', 'image', 'svg', 'icon', 'class']
                if any(skip in field_lower for skip in skip_fields):
                    return True
            if source_text.lower() in ['true', 'false'] or source_text.isnumeric():
                return True
            if re.match(r'^https?://', source_text):
                return True
            return False
    
    # Skip URLs, emails, phone numbers
    if source_text.startswith(('http:', 'https:', '/', 'file:', 'mailto:')):
        return True
    
    if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', source_text.strip()):
        return True
    
    if re.match(r'^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$', source_text.replace(" ", "")):
        return True
    
    # Skip Bricks variables
    if '{' in source_text and '}' in source_text:
        if re.search(r'\{[a-z0-9_:-]+\}', source_text):
            return True
    
    # Skip random IDs (exactly 6 lowercase letters)
    if len(source_text) == 6 and re.match(r'^[a-z]{6}$', source_text):
        return True
    
    # Allow Settings Value (Attribute Value / Tooltip)
    if resname and 'settings' in resname.lower() and 'value' in resname.lower():
        if re.match(r'^\{[^}]+\}$', source_text):
            return True
        if re.match(r'^https?://', source_text):
            return True
        return False
    
    # Skip based on resname patterns
    skip_resname_patterns = [
        r'.*\bId$',
        r'.*\b_CssGlobalClasses$',
        r'.*\bCssGlobalClasses$',
        r'.*-id$',
        r'.*-id-\d+$',
        r'.*-children-\d+$',
        r'.*-parent$',
        r'.*\bFilename$',
        r'.*\bUrl$',
        r'.*\bFull$',
        r'.*\bImage Url$',
        r'.*\bImage Full$',
        r'.*\bImage Filename$',
        r'.*\bSvg Url$',
        r'.*\bSvg Filename$',
        r'.*\bFile Url$',
        r'.*\bFile Filename$',
        r'.*\bUseDynamicData$',
        r'.*\bFill Id$',
        r'.*\bIcon Fill Id$',
        r'.*Children Anwälte.*',
        r'.*Connect Anwälte.*',
        r'.*\bSettings Tag$',
        r'.*\bSettings Size$',
        r'.*\bSettings Type$',
        r'.*\bSettings Order$',
        r'.*\bSettings Orderby$',
        r'.*\bLink Type$',
        r'.*\bIcon Library$',
        r'.*Sektionen Ein.*Ausblenden.*',
        r'.*Ein.*Ausblenden.*Sektion.*',
        # WPML IMPORT FIX: Skip Classic Block/Html with raw WordPress content
        # These contain Gutenberg block markup that conflicts with individual segment translations
        r'^Classic Block$',
        r'^Html$',
    ]

    
    if resname:
        for pattern in skip_resname_patterns:
            if re.match(pattern, resname, re.IGNORECASE):
                return True
    
    # Skip based on source content patterns
    skip_content_patterns = [
        r'^https?://',
        r'^//',
        r'^[^/\\]+\.(webp|png|jpg|jpeg|gif|svg|pdf|mp4|mp3|ico|woff|woff2|ttf|eot)$',
        r'^\{[^}]+\}$',
        r'^(h[1-6]|ul|ol|li|div|span|img|svg)$',
        r'^(full|large|medium|small|thumbnail)$',
        r'^(internal|external|meta|asc|desc)$',
        r'^meta_value_num$',
        r'^post_type$',
        r'^posts_per_page$',
        r'^\d{2}/\d{4}$',
        r'^\d{4}$',
        r'^\d{2}\.\d{2}\.\d{4}$',
    ]
    
    for pattern in skip_content_patterns:
        if re.match(pattern, source_text, re.IGNORECASE):
            return True
    
    # WPML IMPORT FIX: Skip content containing WordPress Gutenberg block markup
    # These are raw WordPress content blocks that should not be translated as a whole
    # Individual segments (Heading, Paragraph, etc.) are already translated separately
    if '<!-- wp:' in source_text or '<!-- /wp:' in source_text:
        return True

    
    # Skip element names only if in Name/Tag field
    element_names = [
        'section', 'container', 'block', 'button', 'text', 'text-basic',
        'heading', 'image', 'template', 'icon', 'nav', 'header', 'footer',
        'sidebar', 'wrapper', 'grid', 'row', 'column', 'col', 'post-content'
    ]
    if source_text.lower() in element_names:
        if resname and ('Name' in resname or 'Tag' in resname):
            return True
    
    # Skip specific template/brand names
    skip_exact_texts = [
        'CR Header', 'CR Footer',
        'true', 'false', 'True', 'False', 'TRUE', 'FALSE'
    ]
    if source_text in skip_exact_texts:
        return True
    
    if source_text.startswith('CR '):
        return True
    
    return False


def extract_resname_from_trans_unit(trans_unit_text):
    """Extract resname from trans-unit element."""
    match = re.search(r'resname="([^"]*)"', trans_unit_text)
    if match:
        return match.group(1)
    return None


def extract_title_from_xliff(content):
    """Extract title from XLIFF content."""
    title_pattern = re.compile(
        r'<trans-unit[^>]*(?:resname|id)="title"[^>]*>.*?<source[^>]*>\s*(?:<!\[CDATA\[)?([^\]<]+)(?:\]\]>)?\s*</source>',
        re.DOTALL | re.IGNORECASE
    )
    match = title_pattern.search(content)
    if match:
        title = match.group(1).strip()
        title = re.sub(r'[\\/:*?"<>|]', '', title)
        if len(title) > 50:
            title = title[:50].rsplit(' ', 1)[0]
        return title.strip()
    return None


def get_target_language_from_xliff(content):
    """Read target-language from XLIFF content."""
    match = re.search(r'target-language=["\']([^"\']+)["\']', content)
    if match:
        return match.group(1).upper()
    
    match = re.search(r'trgLang=["\']([^"\']+)["\']', content)
    if match:
        return match.group(1).upper()
    
    return None


def fix_html_attributes(text):
    """
    Fix HTML attributes that were incorrectly capitalized by translation API.
    Example: <a Href="..."> -> <a href="...">
    """
    if not text:
        return text
    
    # HTML attributes that must be lowercase
    html_attrs = ['href', 'src', 'alt', 'title', 'class', 'id', 'style', 
                  'type', 'name', 'value', 'action', 'method', 'target',
                  'async', 'defer', 'rel', 'data-[a-z-]+']
    
    for attr in html_attrs:
        # Fix patterns like Href= or HREF= or HRef=
        pattern = r'<([a-z][a-z0-9]*)\s+([^>]*)\b(' + attr + r')='
        text = re.sub(pattern, 
                      lambda m: f'<{m.group(1)} {m.group(2)}{m.group(3).lower()}=',
                      text, flags=re.IGNORECASE)
    
    # Fix standalone attribute capitalization after HTML tag
    text = re.sub(r'<([a-z]+)\s+([A-Z][a-z]+)=', 
                  lambda m: f'<{m.group(1)} {m.group(2).lower()}=', text)
    
    return text


def fix_protocol_schemes(text):
    """
    Fix protocol schemes that were incorrectly capitalized.
    Example: Mailto: -> mailto:, Tel: -> tel:
    """
    if not text:
        return text
    
    # Protocol schemes that must be lowercase
    schemes = ['mailto', 'tel', 'http', 'https', 'ftp', 'file', 'javascript']
    
    for scheme in schemes:
        # Fix capitalized schemes like Mailto: or MAILTO:
        pattern = r'\b' + scheme + r':'
        text = re.sub(pattern, f'{scheme}:', text, flags=re.IGNORECASE)
    
    return text


def fix_city_capitalization(text, target_lang=None):
    """
    Ensure city names are properly capitalized.
    Example: múnich -> Múnich, berlín -> Berlín
    """
    if not text:
        return text
    
    # City names that should always be capitalized (language-specific)
    city_caps = {
        'ES': {
            'múnich': 'Múnich',
            'berlín': 'Berlín',
            'colonia': 'Colonia',
            'viena': 'Viena',
            'ginebra': 'Ginebra',
            'praga': 'Praga',
            'varsovia': 'Varsovia',
            'milán': 'Milán',
            'venecia': 'Venecia',
            'florencia': 'Florencia',
            'roma': 'Roma',
            'nápoles': 'Nápoles',
            'bruselas': 'Bruselas',
            'copenhague': 'Copenhague',
            'moscú': 'Moscú',
            'atenas': 'Atenas',
        },
        'EN': {
            'munich': 'Munich',
            'München': 'Munich',
            'muenchen': 'Munich',
            'berlin': 'Berlin',
            'berlín': 'Berlin',
            'cologne': 'Cologne',
            'köln': 'Cologne',
            'koeln': 'Cologne',
            'vienna': 'Vienna',
            'wien': 'Vienna',
            'geneva': 'Geneva',
            'genf': 'Geneva',
            'prague': 'Prague',
            'prag': 'Prague',
            'warsaw': 'Warsaw',
            'warschau': 'Warsaw',
            'milan': 'Milan',
            'mailand': 'Milan',
            'venice': 'Venice',
            'venedig': 'Venice',
            'florence': 'Florence',
            'florenz': 'Florence',
            'rome': 'Rome',
            'rom': 'Rome',
            'naples': 'Naples',
            'neapel': 'Naples',
            'brussels': 'Brussels',
            'brüssel': 'Brussels',
            'bruessel': 'Brussels',
            'copenhagen': 'Copenhagen',
            'kopenhagen': 'Copenhagen',
            'moscow': 'Moscow',
            'moskau': 'Moscow',
            'athens': 'Athens',
            'athen': 'Athens',
            'frankfurt': 'Frankfurt',
            'hamburg': 'Hamburg',
            'düsseldorf': 'Düsseldorf',
            'duesseldorf': 'Düsseldorf',
            'stuttgart': 'Stuttgart',
            'nürnberg': 'Nuremberg',
            'nuernberg': 'Nuremberg',
            'nuremberg': 'Nuremberg',
        }
    }
    
    lang_key = None
    if target_lang:
        lang_key = target_lang.upper().split('-')[0]
    
    if lang_key and lang_key in city_caps:
        for lowercase, proper in city_caps[lang_key].items():
            # Match standalone city name or at start of text
            pattern = r'\b' + re.escape(lowercase) + r'\b'
            text = re.sub(pattern, proper, text, flags=re.IGNORECASE)
    
    return text


def apply_spanish_translations(text):
    """
    Fix specific German-to-Spanish translations that APIs get wrong.
    """
    if not text:
        return text
    
    # Specific fixes for Spanish
    fixes = {
        'Imprimir': 'Aviso Legal',  # Impressum should NOT be "Print"
        'Cookie-einstellungen': 'Configuración de Cookies',
        'Cookie-Einstellungen': 'Configuración de Cookies',
        'Información Del Contacto': 'Información de Contacto',
    }
    
    for wrong, correct in fixes.items():
        if wrong in text:
            text = text.replace(wrong, correct)
    
    return text


def apply_english_translations(text):
    """
    Fix specific German-to-English translations that APIs get wrong.
    """
    if not text:
        return text
    
    # Specific fixes for English
    fixes = {
        'Cookie-einstellungen': 'Cookie Settings',
        'Cookie-Einstellungen': 'Cookie Settings',
        'Einstellungen': 'Settings',
        'Kanzlei': 'Law Firm',
        'kanzlei': 'Law Firm',
        'Erbrecht': 'Inheritance Law',
        'erbrecht': 'Inheritance Law',
        'Rechtsanwalt': 'Lawyer',
        'rechtsanwalt': 'Lawyer',
        'Rechtsanwälte': 'Lawyers',
        'rechtsanwälte': 'Lawyers',
        'Fachanwalt': 'Specialist Lawyer',
        'fachanwalt': 'Specialist Lawyer',
        'Fachanwälte': 'Specialist Lawyers',
        'fachanwälte': 'Specialist Lawyers',
        'Notar': 'Notary',
        'notar': 'Notary',
        'Richter': 'Judge',
        'richter': 'Judge',
        'Impressum': 'Legal Notice',
        'impressum': 'Legal Notice',
        'Datenschutz': 'Privacy Policy',
        'datenschutz': 'Privacy Policy',
        'Datenschutzerklärung': 'Privacy Policy',
        'datenschutzerklärung': 'Privacy Policy',
    }
    
    for german, english in fixes.items():
        # Use word boundary to match whole words
        pattern = r'\b' + re.escape(german) + r'\b'
        text = re.sub(pattern, english, text)
    
    return text


def apply_post_translation_rules(text, source_text, is_cr_header_file=False, should_restore=False, target_lang=None):
    """
    Apply all post-translation rules:
    - Title case matching
    - Job title casing
    - Legal glossary
    - City/Country/State name translation (per target language EYD)
    - Specific text replacements
    - HTML attribute fixes
    - Protocol scheme fixes
    """
    if not text:
        return text
    
    # Don't modify if should_restore (emails, phones, variables)
    if should_restore:
        return text
    
    # CRITICAL: Fix HTML attributes BEFORE any other processing
    text = fix_html_attributes(text)
    
    # Fix protocol schemes (mailto:, tel:, etc.)
    text = fix_protocol_schemes(text)
    
    # Decode HTML entities
    text = html.unescape(text)
    
    # Normalize target language to base code (EN-US -> EN)
    lang_key = None
    if target_lang:
        lang_key = target_lang.upper().split('-')[0]
    
    # Apply city/country/state name translations based on target language
    if lang_key and lang_key in CITY_TRANSLATIONS:
        city_map = CITY_TRANSLATIONS[lang_key]
        for german_name, translated_name in city_map.items():
            # Match whole word, case insensitive
            pattern = r'\b' + re.escape(german_name) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                text = re.sub(pattern, translated_name, text, flags=re.IGNORECASE)
    
    if lang_key and lang_key in STATE_TRANSLATIONS:
        state_map = STATE_TRANSLATIONS[lang_key]
        for german_name, translated_name in state_map.items():
            pattern = r'\b' + re.escape(german_name) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                text = re.sub(pattern, translated_name, text, flags=re.IGNORECASE)
    
    if lang_key and lang_key in COUNTRY_TRANSLATIONS:
        country_map = COUNTRY_TRANSLATIONS[lang_key]
        for german_name, translated_name in country_map.items():
            pattern = r'\b' + re.escape(german_name) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                text = re.sub(pattern, translated_name, text, flags=re.IGNORECASE)
    
    # Fix city name capitalization
    text = fix_city_capitalization(text, target_lang)
    
    # Apply language-specific translation fixes
    if target_lang:
        lang_upper = target_lang.upper()
        if lang_upper.startswith('ES'):
            text = apply_spanish_translations(text)
        elif lang_upper.startswith('EN'):
            text = apply_english_translations(text)
    
    # Title case matching: if source was title case, apply to translation
    if source_text and is_title_case(source_text):
        text = smart_title_case(text)
    
    # CR Header files always get title case
    if is_cr_header_file:
        text = smart_title_case(text)
    
    # Job title casing
    if len(text) < 100:
        job_titles_map = {
            'lawyer': 'Lawyer',
            'attorney': 'Attorney',
            'attorney at law': 'Attorney at Law',
            'partner': 'Partner',
            'associate': 'Associate',
            'counsel': 'Counsel',
            'specialist lawyer': 'Specialist Lawyer',
            'specialist attorney': 'Specialist Attorney',
            'managing partner': 'Managing Partner',
            'managing director': 'Managing Director',
            'founder': 'Founder',
            'co-founder': 'Co-Founder',
            'judge': 'Judge',
            'notary': 'Notary',
            'prosecutor': 'Prosecutor',
        }
        
        for key, value in job_titles_map.items():
            if re.search(r'\b' + re.escape(key) + r'\b', text, re.IGNORECASE):
                text = re.sub(r'\b' + re.escape(key) + r'\b', value, text, flags=re.IGNORECASE)
    
    # Specific replacements
    if 'on google maps' in text.lower():
        text = re.sub(r'\bon google maps\b', 'On Google Maps', text, flags=re.IGNORECASE)
    
    return text


def process_xliff_file_regex(translator, file_path, target_lang_override=None):
    """
    Process XLIFF file with all workflow rules applied.
    """
    print(f"\n[FILE] Memproses: {file_path.name}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Validate XLIFF structure
        is_valid, errors = validate_xliff_structure(content)
        if not is_valid:
            print(f"  [WARNING] XLIFF validation issues:")
            for error in errors:
                print(f"    - {error}")
        
        # Get target language
        xliff_target_lang = get_target_language_from_xliff(content)
        target_lang = target_lang_override or xliff_target_lang
        
        if not target_lang:
            print(f"  [ERROR] Target language tidak ditemukan di file XLIFF!")
            print(f"          Gunakan command line override: python translate_xliff.py ES")
            return 0
        
        # DeepL requires EN-US or EN-GB, not just EN
        if target_lang == 'EN':
            print("  [FIX] Mendeteksi target 'EN', mengubah otomatis ke 'EN-US'")
            target_lang = 'EN-US'
        
        source_info = 'override' if target_lang_override else 'XLIFF file'
        print(f"       Bahasa target: {target_lang} (dari {source_info})")
        
        # Extract title for output filename
        xliff_title = extract_title_from_xliff(content)
        
        # Check if this is a CR Header file (apply title case)
        is_cr_header_file = xliff_title and xliff_title.startswith('CR ')
        if is_cr_header_file:
            print(f"       [TITLE CASE] File CR Header terdeteksi")
        
        # Pattern for trans-unit with source and target
        trans_unit_pattern = re.compile(
            r'(<trans-unit[^>]*>.*?<source[^>]*>)(.*?)(</source>)(.*?)(<target[^>]*>)(.*?)(</target>)',
            re.DOTALL
        )
        
        matches = list(trans_unit_pattern.finditer(content))
        
        if not matches:
            print("  [!] Tidak ada trans-unit dengan target ditemukan")
            return 0
        
        print(f"       Ditemukan {len(matches)} segment total")
        
        # Extract source texts and flags
        source_texts = []
        cdata_flags = []
        resnames = []
        skip_flags = []
        
        for match in matches:
            trans_unit_start = match.group(1)
            resname = extract_resname_from_trans_unit(trans_unit_start)
            resnames.append(resname)
            
            source_raw = match.group(2)
            source_text, is_cdata = extract_cdata_content(source_raw)
            source_texts.append(source_text)
            cdata_flags.append(is_cdata)
            
            should_skip = should_skip_translation(resname, source_text)
            skip_flags.append(should_skip)
        
        segments_to_translate = sum(1 for skip in skip_flags if not skip)
        segments_to_skip = sum(1 for skip in skip_flags if skip)
        
        print(f"       - Akan diterjemahkan: {segments_to_translate} segment")
        print(f"       - Dilewati (ID/technical): {segments_to_skip} segment")
        
        # Prepare texts for translation
        texts_for_translation = []
        translation_indices = []
        
        for i, (text, skip) in enumerate(zip(source_texts, skip_flags)):
            if not skip:
                texts_for_translation.append(text)
                translation_indices.append(i)
        
        # Translate in batches
        translated_results = []
        if texts_for_translation:
            total_batches = (len(texts_for_translation) + BATCH_SIZE - 1) // BATCH_SIZE
            
            for i in range(0, len(texts_for_translation), BATCH_SIZE):
                batch = texts_for_translation[i:i+BATCH_SIZE]
                batch_num = (i // BATCH_SIZE) + 1
                print(f"  [+] Translating batch {batch_num}/{total_batches} ({len(batch)} segments)...")
                
                translated_batch = translate_batch(translator, batch, target_lang)
                translated_results.extend(translated_batch)
        
        # Helper function to check if restore is needed
        def is_restore_required(text):
            if not text:
                return False
            if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', text.strip()):
                return True
            if re.match(r'^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$', text.replace(" ", "")):
                return True
            if re.match(r'^\{[a-z0-9_:-]+\}$', text.strip()):
                return True
            if text.lower() in ['true', 'false']:
                return True
            return False
        
        # Apply translations
        replacements_list = []
        translate_idx = 0
        translated_count = 0
        
        for i, match in enumerate(matches):
            trans_unit_start_tag = match.group(1)
            resname = extract_resname_from_trans_unit(trans_unit_start_tag)
            
            source_raw = match.group(2)
            source_text, is_cdata = extract_cdata_content(source_raw)
            
            should_skip = should_skip_translation(resname, source_text)
            should_restore = is_restore_required(source_text)
            
            final_translated_text = None
            
            if not should_skip:
                if translate_idx < len(translated_results):
                    final_translated_text = translated_results[translate_idx]
                    translate_idx += 1
                else:
                    final_translated_text = source_text
            elif should_restore:
                final_translated_text = source_text
            else:
                existing_target = match.group(6)
                if existing_target and '<![cdata[' in existing_target.lower():
                    final_translated_text = source_text
                else:
                    final_translated_text = existing_target if existing_target else source_text
            
            # Apply post-translation rules
            if final_translated_text:
                final_translated_text = apply_post_translation_rules(
                    final_translated_text, 
                    source_text, 
                    is_cr_header_file, 
                    should_restore,
                    target_lang
                )
            
            # CRITICAL: Fallback to source_text if final_translated_text is None or empty
            if not final_translated_text or not final_translated_text.strip():
                final_translated_text = source_text if source_text else ""
            
            # Fix entity encoding
            if is_cdata:
                # Ensure we have a valid string before calling replace
                text_to_clean = final_translated_text if final_translated_text else ""
                # Clean CDATA wrappers and strip trailing brackets to prevent ]]]]>
                cleaned_trans = text_to_clean.replace('<![CDATA[', '').replace(']]>', '')
                # Remove any trailing ] that could cause ]]]]> malformation
                cleaned_trans = cleaned_trans.rstrip(']')
                replacement_text = f"<![CDATA[{cleaned_trans}]]>"
            else:
                replacement_text = fix_entity_encoding(final_translated_text, is_cdata=False)
                # Safety check
                if not replacement_text:
                    replacement_text = source_text if source_text else ""
            
            # Update target tag state
            target_tag = match.group(5)
            new_target_tag = re.sub(r'state="[^"]*"', 'state="translated"', target_tag)
            if 'state=' not in new_target_tag:
                new_target_tag = target_tag.replace('>', ' state="translated">', 1)
            
            new_target_element = new_target_tag + replacement_text + match.group(7)
            
            start_pos = match.start(5)
            end_pos = match.end(7)
            
            replacements_list.append((start_pos, end_pos, new_target_element))
            
            if not should_skip:
                translated_count += 1
        
        # Apply all replacements (from end to start)
        replacements_list.sort(key=lambda x: x[0], reverse=True)
        for start, end, text in replacements_list:
            content = content[:start] + text + content[end:]
        
        # Generate output filename
        if xliff_title:
            output_filename = f"{xliff_title}_{file_path.stem}_{target_lang}{file_path.suffix}"
        else:
            output_filename = f"{file_path.stem}_{target_lang}{file_path.suffix}"
        
        output_path = Path(OUTPUT_FOLDER) / output_filename
        
        # Validate XLIFF structure before writing
        is_valid, errors = validate_xliff_structure(content)
        if not is_valid:
            print(f"  [WARNING] XLIFF validation issues: {errors}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  [DONE] Selesai! {translated_count} segment diterjemahkan, {segments_to_skip} dilewati")
        print(f"  [SAVED] Tersimpan: {output_path}")
        
        return translated_count
        
    except Exception as e:
        print(f"  [ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return 0


def main():
    """Main function for batch translation."""
    print("=" * 60)
    print("    XLIFF Batch Translator")
    print(f"    API: {TRANSLATION_API.upper()}")
    print("    (Enhanced WPML Playbook Edition)")
    print("=" * 60)
    
    # Validate API availability and credentials
    translator = None
    
    if TRANSLATION_API == "google":
        if not GOOGLE_AVAILABLE:
            print("\n[ERROR] Google Cloud Translate tidak tersedia!")
            print("        Install dengan: pip install google-cloud-translate")
            sys.exit(1)
        
        if GOOGLE_API_KEY == "YOUR_GOOGLE_API_KEY":
            print("\n[ERROR] Silakan masukkan Google API Key Anda!")
            print("        Buka file ini dan edit variabel GOOGLE_API_KEY")
            print("        Dapatkan API Key di: https://console.cloud.google.com")
            sys.exit(1)
        
        try:
            # Test connection with REST API
            test_url = f"https://translation.googleapis.com/language/translate/v2?key={GOOGLE_API_KEY}"
            test_payload = {"q": "test", "target": "en", "format": "text"}
            test_response = requests.post(test_url, json=test_payload)
            test_response.raise_for_status()
            translator = "google_rest"  # Placeholder, actual translation in translate_batch
            print(f"\n[OK] Google Cloud Translation API tersambung")
            print(f"      API Key: {GOOGLE_API_KEY[:10]}...{GOOGLE_API_KEY[-4:]}")
        except requests.exceptions.HTTPError as e:
            print(f"\n[ERROR] Gagal terhubung ke Google API: {e}")
            if e.response is not None:
                print(f"        Response: {e.response.text[:200]}")
            sys.exit(1)
        except Exception as e:
            print(f"\n[ERROR] Gagal terhubung ke Google API: {e}")
            sys.exit(1)
    
    else:  # DeepL (default)
        if not DEEPL_AVAILABLE:
            print("\n[ERROR] DeepL tidak tersedia!")
            print("        Install dengan: pip install deepl")
            sys.exit(1)
        
        if DEEPL_API_KEY == "your-api-key-here":
            print("\n[ERROR] Silakan masukkan API Key DeepL Anda!")
            print("        Buka file ini dan edit variabel DEEPL_API_KEY")
            print("        Dapatkan API Key di: https://www.deepl.com/pro-api")
            sys.exit(1)
        
        try:
            translator = deepl.Translator(DEEPL_API_KEY)
            usage = translator.get_usage()
            print(f"\n[INFO] DeepL API Usage:")
            if usage.character.valid:
                remaining = usage.character.limit - usage.character.count
                print(f"        Terpakai : {usage.character.count:,} karakter")
                print(f"        Limit    : {usage.character.limit:,} karakter")
                print(f"        Sisa     : {remaining:,} karakter")
        except deepl.AuthorizationException:
            print("\n[ERROR] API Key tidak valid!")
            sys.exit(1)
        except Exception as e:
            print(f"\n[ERROR] Gagal terhubung ke DeepL: {e}")
            sys.exit(1)
    
    setup_folders()
    
    target_lang_override = None
    if len(sys.argv) > 1:
        target_lang_override = sys.argv[1].upper()
        print(f"\n[TARGET] Override bahasa target: {target_lang_override}")
    else:
        print(f"\n[TARGET] Bahasa target: Otomatis dari file XLIFF")
    
    xliff_files = get_xliff_files()
    
    if not xliff_files:
        print(f"\n[!] Tidak ada file XLIFF ditemukan di folder '{INPUT_FOLDER}'")
        print(f"    Letakkan file .xliff atau .xlf di folder tersebut")
        sys.exit(0)
    
    print(f"\n[FILES] Ditemukan {len(xliff_files)} file XLIFF:")
    for f in xliff_files:
        print(f"        - {f.name}")
    
    print(f"\n[CONFIG] Rate limiting: {DELAY_BETWEEN_REQUESTS}s antar request, {DELAY_BETWEEN_FILES}s antar file")
    print(f"[CONFIG] Batch size: {BATCH_SIZE} segment per request")
    
    print("\n[RULES] Enhanced protection enabled:")
    print("        - XLIFF Integrity Protection")
    print("        - WP Admin-Only Settings Protection")
    print("        - Smart Title Case (Position/City/Punctuation)")
    print("        - JetEngine/Bricks/WPML Field Protection")
    
    start_time = datetime.now()
    total_segments = 0
    successful_files = 0
    skipped_files = 0
    
    for i, xliff_file in enumerate(xliff_files):
        segments = process_xliff_file_regex(translator, xliff_file, target_lang_override)
        
        if segments == -1:
            skipped_files += 1
            print(f"  [CLEANUP] Output sudah ada, menghapus input file: {xliff_file.name}")
            try:
                os.remove(xliff_file)
            except Exception as e:
                print(f"  [!] Gagal menghapus input: {e}")
                
        elif segments > 0:
            total_segments += segments
            successful_files += 1
            
            print(f"  [CLEANUP] Translasi sukses, menghapus input file: {xliff_file.name}")
            try:
                os.remove(xliff_file)
            except Exception as e:
                print(f"  [!] Gagal menghapus input: {e}")
            
            if i < len(xliff_files) - 1:
                print(f"\n[WAIT] Waiting {DELAY_BETWEEN_FILES}s before next file...")
                time.sleep(DELAY_BETWEEN_FILES)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 60)
    print("    RINGKASAN")
    print("=" * 60)
    print(f"   File berhasil : {successful_files}/{len(xliff_files)}")
    print(f"   File di-skip  : {skipped_files} (sudah ada di output)")
    print(f"   Total segment : {total_segments:,}")
    print(f"   Waktu proses  : {duration:.1f} detik")
    print(f"   Output folder : {OUTPUT_FOLDER}/")
    print("=" * 60)
    
    try:
        usage = translator.get_usage()
        if usage.character.valid:
            print(f"\n[INFO] Sisa kuota DeepL: {usage.character.limit - usage.character.count:,} karakter")
    except:
        pass


if __name__ == "__main__":
    main()
