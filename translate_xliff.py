"""
XLIFF Batch Translator menggunakan DeepL API
=============================================
Script untuk menerjemahkan file XLIFF dalam jumlah banyak secara otomatis.
Kompatibel dengan WPML XLIFF export/import.

Cara penggunaan:
1. Masukkan API Key DeepL Anda di variabel DEEPL_API_KEY
2. Letakkan file-file XLIFF di folder 'input'
3. Jalankan script: python translate_xliff.py
4. Hasil terjemahan akan tersimpan di folder 'output'
"""

import deepl
import os
import sys
import re
import time
import html
from pathlib import Path
from datetime import datetime

# Fix encoding untuk Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ==================== KONFIGURASI ====================
# Masukkan API Key DeepL Anda di sini
DEEPL_API_KEY = "7d310721-db7e-45b2-9c1f-11071e317678"

# Bahasa target default akan dibaca dari file XLIFF
# Jika tidak ada di file XLIFF, gunakan command line override: python translate_xliff.py ES
# Lihat daftar lengkap: https://www.deepl.com/docs-api/translate-text
DEFAULT_TARGET_LANG = None  # None = wajib baca dari XLIFF

# Folder input dan output
INPUT_FOLDER = "input"
OUTPUT_FOLDER = "output"

# Rate limiting - delay dalam detik antar request ke DeepL
# Untuk menghindari "too many requests" error
DELAY_BETWEEN_REQUESTS = 0.5  # 0.5 detik = 2 request per detik
DELAY_BETWEEN_FILES = 2  # 2 detik antar file

# Batch size - jumlah segment per batch untuk translasi
BATCH_SIZE = 10  # Translate 10 segment sekaligus untuk efisiensi
# =====================================================


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
    """Menerjemahkan batch teks menggunakan DeepL dengan rate limiting."""
    if not texts:
        return []
    
    # Filter teks kosong tapi simpan indexnya
    non_empty_indices = []
    non_empty_texts = []
    for i, text in enumerate(texts):
        if text and text.strip():
            non_empty_indices.append(i)
            non_empty_texts.append(text)
    
    if not non_empty_texts:
        return texts  # Return original jika semua kosong
    
    try:
        # Rate limiting
        time.sleep(DELAY_BETWEEN_REQUESTS)
        
        # Translate batch
        results = translator.translate_text(non_empty_texts, target_lang=target_lang)
        
        # Rebuild hasil dengan posisi yang benar
        translated = list(texts)  # Copy original
        for idx, result in zip(non_empty_indices, results):
            translated[idx] = result.text
        
        return translated
        
    except deepl.QuotaExceededException:
        print("\n[ERROR] Kuota DeepL habis!")
        raise
    except deepl.TooManyRequestsException:
        print("\n[WAIT] Too many requests, waiting 10 seconds...")
        time.sleep(10)
        return translate_batch(translator, texts, target_lang)  # Retry
    except Exception as e:
        print(f"\n[!] Error translating batch: {str(e)[:50]}")
        return texts  # Return original on error


def extract_cdata_content(text):
    """Mengekstrak konten dari CDATA section."""
    if text is None:
        return None, False
    
    # Check if it's CDATA
    cdata_match = re.match(r'^\s*<!\[CDATA\[(.*?)\]\]>\s*$', text, re.DOTALL)
    if cdata_match:
        return cdata_match.group(1), True
    return text, False


def wrap_in_cdata(text, was_cdata):
    """Membungkus text dalam CDATA jika sebelumnya CDATA."""
    if was_cdata and text:
        return f"<![CDATA[{text}]]>"
    return text


def smart_title_case(text):
    """
    Apply title case hanya ke kata-kata yang bermakna.
    Melewatkan HTML entities, CSS code, technical identifiers, dan strings dengan underscore/hyphen.
    """
    if not text:
        return text
    
    # Skip jika text mengandung technical patterns (CSS, identifiers, dll)
    technical_patterns = [
        r'\{[^}]+\}',           # CSS properties like { margin: 0; }
        r'#[a-zA-Z0-9-_]+\s',   # CSS IDs like #brxe-omexvs
        r'\.[a-zA-Z0-9-_]+\s',  # CSS classes like .cr-header
        r':\s*\d+',             # CSS values like : 100%
        r'transform:',
        r'margin:',
        r'padding:',
        r'position:',
        r'content:',
        r'height:',
        r'width:',
        r'display:',
        r'flex',
        r'absolute',
    ]
    
    for pattern in technical_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return text  # Return as-is, no title case
    
    # Skip jika text adalah technical identifier (mengandung underscore atau lowercase hyphenated)
    # Contoh: tablet_portrait, brx-submenu-toggle, nav-nested
    if re.match(r'^[a-z][a-z0-9]*[-_][a-z0-9_-]+$', text):
        return text  # Return as-is, this is a technical identifier
    
    # Skip jika text terlihat seperti CSS class atau selector (starts with brx-, cr-, dll)
    if re.match(r'^(brx|brxe|cr)[-_]', text.lower()):
        return text  # Return as-is
    
    # Jika text adalah single word dengan huruf kecil semua dan panjang < 15, skip
    # (kemungkinan technical term seperti: toggle, visible, hidden, internal, external)
    skip_lowercase_words = [
        'toggle', 'visible', 'hidden', 'internal', 'external', 'click', 'hover',
        'flex', 'none', 'block', 'inline', 'absolute', 'relative', 'static',
        'left', 'right', 'center', 'top', 'bottom', 'span', 'div', 'ul', 'li', 'a',
        'svg', 'wpmenu', 'themify', 'queryloopextras'
    ]
    if text.lower() in skip_lowercase_words:
        return text  # Return as-is
    
    # Apply title case hanya untuk meaningful text
    # Preserve & as-is (jangan convert ke &amp;)
    words = text.split()
    result_words = []
    
    for word in words:
        # Skip words yang terlihat technical (dengan underscore atau banyak hyphen)
        if '_' in word or word.count('-') > 1:
            result_words.append(word)
        # Skip kata-kata yang semuanya huruf besar (kemungkinan acronym/ID)
        elif word.isupper() and len(word) > 2:
            result_words.append(word)
        # Skip kata dengan pattern ID seperti #brxe-xxx
        elif word.startswith('#') or word.startswith('.'):
            result_words.append(word)
        else:
            # Title case untuk kata normal
            result_words.append(word.capitalize())
    
    return ' '.join(result_words)


def should_skip_translation(resname, source_text):
    """
    Menentukan apakah trans-unit ini harus dilewati dari translasi.
    Ini untuk menghindari mentranslate ID internal, nama elemen, CSS class, URL, dll.
    
    Returns True jika harus dilewati (tidak ditranslate).
    """
    if not source_text:
        return True
    
    source_text = source_text.strip()
    
    # Skip empty or whitespace only
    if not source_text:
        return True
    
    # 2. Skip jika text adalah URL, path, email, atau nomor telepon
    if source_text.startswith(('http:', 'https:', '/', 'file:', 'mailto:')):
        return True
    
    # Regex untuk Email
    if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', source_text.strip()):
        return True
        
    # Regex untuk Phone Number (format umum +49, 089, dll)
    # Minimal 7 digit, boleh ada spasi/dash/+
    if re.match(r'^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$', source_text.replace(" ", "")):
        return True
        
    # Skip jika text berisi keywords teknis Bricks/WP
    if '{' in source_text and '}' in source_text:
        # Cek jika ini Bricks variable
        if re.search(r'\{[a-z0-9_:-]+\}', source_text):
            return True
    
    # 1. Skip jika source text terlalu pendek dan terlihat seperti ID (huruf random saja)
    # HANYA skip jika terlihat seperti random ID (lowercase letters only, 6 chars)
    if len(source_text) == 6 and re.match(r'^[a-z]{6}$', source_text):
        return True
    
    
    # 1. Explicit Allowances (Prioritas Tinggi)
    # Izinkan Settings ... Value (biasanya untuk Attribute Value / Tooltip)
    if resname and 'settings' in resname.lower() and 'value' in resname.lower():
         # Tetap skip jika kontennya murni variable {..} (Dynamic Data)
         if re.match(r'^\{[^}]+\}$', source_text):
             return True
         # Skip jika kontennya URL
         if re.match(r'^https?://', source_text):
             return True
         # Selain itu, IZINKAN (jangan diproses logic skip di bawah)
         return False

    # 2. Skip berdasarkan resname (field name) yang PASTI tidak perlu ditranslate
    skip_resname_patterns = [
        # Bricks Builder internal IDs
        r'.*\bId$',                    # Ends with "Id" (element IDs)
        r'.*\bParent$',                # Parent references
        r'.*\bChildren$',              # Children references
        r'.*\b_CssGlobalClasses$',     # CSS class references
        r'.*\bCssGlobalClasses$',      # CSS class references
        
        # Technical fields yang biasanya berisi ID/reference
        r'.*-id$',
        r'.*-id-\d+$',
        r'.*-children-\d+$',
        r'.*-parent$',
        
        # File/media references - URL dan filename
        r'.*\bFilename$',              # Filename fields
        r'.*\bUrl$',                   # URL fields  
        r'.*\bFull$',                  # Full URL fields
        r'.*\bImage Url$',
        r'.*\bImage Full$',
        r'.*\bImage Filename$',
        r'.*\bSvg Url$',
        r'.*\bSvg Filename$',
        r'.*\bFile Url$',
        r'.*\bFile Filename$',
        
        # Dynamic data placeholders
        r'.*\bUseDynamicData$',
        
        # Internal Bricks references
        r'.*\bFill Id$',
        r'.*\bIcon Fill Id$',
        
        # Technical Settings fields (bukan konten)
        r'.*\bSettings Tag$',          # HTML tag setting (h1, h2, etc)
        r'.*\bSettings Size$',
        r'.*\bSettings Type$',
        r'.*\bSettings Order$',
        r'.*\bSettings Orderby$',
        r'.*\bLink Type$',
        r'.*\bIcon Library$',
    ]
    
    if resname:
        for pattern in skip_resname_patterns:
            if re.match(pattern, resname, re.IGNORECASE):
                return True
    
    # 3. Skip berdasarkan source text content yang jelas technical
    skip_content_patterns = [
        # URLs
        r'^https?://',
        r'^//',
        
        # File extensions (images, etc)
        r'^[^/\\]+\.(webp|png|jpg|jpeg|gif|svg|pdf|mp4|mp3|ico|woff|woff2|ttf|eot)$',
        
        # Dynamic placeholders
        r'^\{[^}]+\}$',                # {post_title}, {post_url}, etc.
        
        # HTML tags only (single word, lowercase)
        r'^(h[1-6]|ul|ol|li|div|span|img|svg)$',
        
        # Image sizes
        r'^(full|large|medium|small|thumbnail)$',
        
        # Link/query types
        r'^(internal|external|meta|asc|desc)$',
        
        # Technical snake_case values
        r'^meta_value_num$',
        r'^post_type$',
        r'^posts_per_page$',
    ]
    
    for pattern in skip_content_patterns:
        if re.match(pattern, source_text, re.IGNORECASE):
            return True
    
    # 4. Skip element/component names HANYA jika resname menunjukkan ini adalah Name atau Tag field
    element_names = [
        'section', 'container', 'block', 'button', 'text', 'text-basic',
        'heading', 'image', 'template', 'icon', 'nav', 'header', 'footer',
        'sidebar', 'wrapper', 'grid', 'row', 'column', 'col', 'post-content'
    ]
    if source_text.lower() in element_names:
        if resname and ('Name' in resname or 'Tag' in resname):
            return True
    
    # 5. Skip specific template/brand names that should not be translated
    skip_exact_texts = [
        'CR Header',
        'CR Footer',
        'true', 'false', 'True', 'False', 'TRUE', 'FALSE'
    ]
    if source_text in skip_exact_texts:
        return True
    
    # Also skip anything starting with "CR " (template names)
    if source_text.startswith('CR '):
        return True
    
    return False


def extract_resname_from_trans_unit(trans_unit_text):
    """Mengekstrak resname dari trans-unit element."""
    match = re.search(r'resname="([^"]*)"', trans_unit_text)
    if match:
        return match.group(1)
    return None


def extract_title_from_xliff(content):
    """
    Mengekstrak title dari konten XLIFF.
    Title biasanya ada di trans-unit dengan resname="title" atau id="title".
    """
    # Cari trans-unit dengan resname atau id = title
    title_pattern = re.compile(
        r'<trans-unit[^>]*(?:resname|id)="title"[^>]*>.*?<source[^>]*>\s*(?:<!\[CDATA\[)?([^\]<]+)(?:\]\]>)?\s*</source>',
        re.DOTALL | re.IGNORECASE
    )
    match = title_pattern.search(content)
    if match:
        title = match.group(1).strip()
        # Bersihkan karakter yang tidak valid untuk nama file
        # Hapus karakter: \ / : * ? " < > |
        title = re.sub(r'[\\/:*?"<>|]', '', title)
        # Batasi panjang title untuk nama file
        if len(title) > 50:
            title = title[:50].rsplit(' ', 1)[0]  # Potong di word boundary
        return title.strip()
    return None


def get_target_language_from_xliff(content):
    """Membaca target-language dari konten XLIFF."""
    # Cari target-language di atribut file
    match = re.search(r'target-language=["\']([^"\']+)["\']', content)
    if match:
        return match.group(1).upper()
    
    # Cari trgLang untuk XLIFF 2.0
    match = re.search(r'trgLang=["\']([^"\']+)["\']', content)
    if match:
        return match.group(1).upper()
    
    return None


def process_xliff_file_regex(translator, file_path, target_lang_override=None):
    """
    Memproses file XLIFF menggunakan regex untuk mempertahankan struktur asli.
    Ini memastikan XLIFF tetap valid untuk WPML import.
    """
    print(f"\n[FILE] Memproses: {file_path.name}")
    
    try:
        # Baca file sebagai text untuk mempertahankan struktur
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Dapatkan target language dari file atau override
        xliff_target_lang = get_target_language_from_xliff(content)
        target_lang = target_lang_override or xliff_target_lang
        
        if not target_lang:
            print(f"  [ERROR] Target language tidak ditemukan di file XLIFF!")
            print(f"          Gunakan command line override: python translate_xliff.py ES")
            return 0
            
        # [FIX] DeepL requires EN-US or EN-GB, not just EN
        if target_lang == 'EN':
            print("  [FIX] Mendeteksi target 'EN', mengubah otomatis ke 'EN-US'")
            target_lang = 'EN-US'

        # [MODIFIED] User request: Process ANY target language
        # Restriction removed: if target_lang != 'EN-US': ...

        
        source_info = 'override' if target_lang_override else 'XLIFF file'
        print(f"       Bahasa target: {target_lang} (dari {source_info})")
        
        # Cek apakah output sudah ada (skip jika sudah ditranslate sebelumnya)
        xliff_title = extract_title_from_xliff(content)
        if xliff_title:
            expected_output = f"{xliff_title}_{file_path.stem}_{target_lang}{file_path.suffix}"
        else:
            expected_output = f"{file_path.stem}_{target_lang}{file_path.suffix}"
        
        # Check if this is a CR Header file (apply title case to translations)
        is_cr_header_file = xliff_title and xliff_title.startswith('CR ')
        if is_cr_header_file:
            print(f"       [TITLE CASE] File CR Header terdeteksi, hasil translasi akan di-title case")

        expected_output_path = Path(OUTPUT_FOLDER) / expected_output
        
        # [MODIFIED] User request: Always re-translate, do not skip if output exists
        # Checks for existing output removed to allow re-translation
        
        # Juga cek format lama tanpa title (backward compatibility)
        fallback_output = f"{file_path.stem}_{target_lang}{file_path.suffix}"
        fallback_output_path = Path(OUTPUT_FOLDER) / fallback_output
        
        # if expected_output_path.exists():
        #     print(f"  [SKIP] Output sudah ada: {expected_output}")
        #     return -1  # Return -1 to indicate skipped
        
        # if fallback_output_path.exists() and expected_output != fallback_output:
        #     print(f"  [SKIP] Output sudah ada: {fallback_output}")
        #     return -1  # Return -1 to indicate skipped
        
        # Pattern untuk menemukan trans-unit dengan source dan target
        # Ini akan menangkap seluruh trans-unit element
        trans_unit_pattern = re.compile(
            r'(<trans-unit[^>]*>.*?<source[^>]*>)(.*?)(</source>)(.*?)(<target[^>]*>)(.*?)(</target>)',
            re.DOTALL
        )
        
        # Juga handle kasus di mana target belum ada
        trans_unit_no_target_pattern = re.compile(
            r'(<trans-unit[^>]*>.*?<source[^>]*>)(.*?)(</source>)((?:(?!</trans-unit>).)*?)(</trans-unit>)',
            re.DOTALL
        )
        
        # Kumpulkan semua source texts untuk batch translation
        matches = list(trans_unit_pattern.finditer(content))
        
        if not matches:
            print("  [!] Tidak ada trans-unit dengan target ditemukan")
            # Coba cari yang tanpa target
            matches_no_target = list(trans_unit_no_target_pattern.finditer(content))
            if matches_no_target:
                print(f"  [INFO] Ditemukan {len(matches_no_target)} trans-unit tanpa target")
            return 0
        
        print(f"       Ditemukan {len(matches)} segment total")
        
        # Extract source texts dan filter yang tidak perlu ditranslate
        source_texts = []
        cdata_flags = []
        resnames = []
        skip_flags = []  # Flag untuk menandai mana yang di-skip
        
        for match in matches:
            # Extract resname dari trans-unit
            trans_unit_start = match.group(1)
            resname = extract_resname_from_trans_unit(trans_unit_start)
            resnames.append(resname)
            
            source_raw = match.group(2)
            source_text, is_cdata = extract_cdata_content(source_raw)
            source_texts.append(source_text)
            cdata_flags.append(is_cdata)
            
            # Tentukan apakah harus di-skip
            should_skip = should_skip_translation(resname, source_text)
            skip_flags.append(should_skip)
        
        # Hitung segment yang akan ditranslate vs skip
        segments_to_translate = sum(1 for skip in skip_flags if not skip)
        segments_to_skip = sum(1 for skip in skip_flags if skip)
        
        print(f"       - Akan diterjemahkan: {segments_to_translate} segment")
        print(f"       - Dilewati (ID/technical): {segments_to_skip} segment")
        
        # Prepare texts untuk ditranslate (hanya yang tidak di-skip)
        texts_for_translation = []
        translation_indices = []  # Index asli dari texts yang ditranslate
        
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
        
        # Terapkan hasil translasi ke konten XML
        # Kita lakukan string replacement dari BELAKANG ke DEPAN agar offset tidak berantakan
        # Tapi karena XML string mutable di Python sulit, kita rebuild string atau pakai approach sequence replace
        
        # Pendekatan: Kita kumpulkan semua replacement (start, end, new_content)
        # Lalu kita apply sekaligus
        
        replacements_list = []
        translate_idx = 0
        
        all_matches = list(trans_unit_pattern.finditer(content))
        
        # Pre-calculate restoration checks
        def is_restore_required(text):
            if not text: return False
            # Email
            if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', text.strip()): return True
            # Phone
            if re.match(r'^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$', text.replace(" ", "")): return True
            # Bricks Variable
            if re.match(r'^\{[a-z0-9_:-]+\}$', text.strip()): return True
            # Boolean settings (prevent translation to verdadero/falso)
            if text.lower() in ['true', 'false']: return True
            return False

        translated_count = 0 # Reset translated_count for the new logic
        
        for i, match in enumerate(all_matches):
            # Extract resname from trans-unit
            trans_unit_start_tag = match.group(1)
            resname = extract_resname_from_trans_unit(trans_unit_start_tag)
            
            source_raw = match.group(2)
            source_text, is_cdata = extract_cdata_content(source_raw)
            
            # Determine if this segment should be skipped from translation
            should_skip = should_skip_translation(resname, source_text)
            should_restore = is_restore_required(source_text)
            
            final_translated_text = None
            
            if not should_skip:
                # This segment was meant to be translated
                if translate_idx < len(translated_results):
                    final_translated_text = translated_results[translate_idx]
                    translate_idx += 1
                else:
                    # Fallback if for some reason translation result is missing (shouldn't happen)
                    final_translated_text = source_text
            elif should_restore:
                # If skipped, BUT user requested restore (email/phone/variable)
                # Then we use the SOURCE as the TARGET
                final_translated_text = source_text
            else:
                # If skipped and not restored, keep the original target content (or source if no target)
                # For this regex, match.group(6) is the existing target content.
                # If there was no target, this match wouldn't have been found by trans_unit_pattern.
                # So we can safely use the existing target or source if target was empty.
                # If skipped and not restored, keep the original target content (or source if no target)
                # But FIRST, check if existing target is corrupted (e.g. lowercase cdata)
                existing_target = match.group(6)
                if existing_target and '<![cdata[' in existing_target.lower():
                     # Target rusak/malformed, revert ke source
                     final_translated_text = source_text
                else:
                     final_translated_text = existing_target if existing_target else source_text
            
            # If no actual translation or restoration happened, and it was skipped, we don't need to modify
            # the target content unless we need to update the state.
            
            # Decode & Format
            if final_translated_text:
                final_translated_text = html.unescape(final_translated_text)
                
            # Apply title case if needed (CR Header)
            if is_cr_header_file and not should_restore and final_translated_text: # Jangan title case email/phone/variables
                 final_translated_text = smart_title_case(final_translated_text)
            
            # --- RULE: Specific Replace for "on Google Maps" ---
            # User request: "on Google Maps jadi On Google Maps"
            if 'on google maps' in final_translated_text.lower():
                final_translated_text = re.sub(r'\bon google maps\b', 'On Google Maps', final_translated_text, flags=re.IGNORECASE)

            # --- RULE: Job Title Casing ---
            # User request: "Jabatan dibikin title case"
            # Apply to short text that looks like a title/position
            if len(final_translated_text) < 100:
                job_titles_map = {
                    'lawyer': 'Lawyer',
                    'attorney': 'Lawyer', # Normalize attorney to Lawyer as per previous rule, but Title Cased
                    'attorney at law': 'Attorney at Law',
                    'partner': 'Partner',
                    'associate': 'Associate',
                    'counsel': 'Counsel',
                    'specialist lawyer': 'Specialist Lawyer',
                    'managing partner': 'Managing Partner',
                    'founder': 'Founder',
                    'co-founder': 'Co-Founder'
                }
                lower_text = final_translated_text.lower()
                for key, value in job_titles_map.items():
                    # Regex for whole word match to avoid replacing substrings incorrectly
                    if re.search(r'\b' + re.escape(key) + r'\b', lower_text):
                        # Replace preserving other text (simple approach: replace the match)
                        # Note: This simple replace might lose original casing of surrounding words if we rely on lower_text
                        # So we use re.sub with IGNORECASE on the original text
                        final_translated_text = re.sub(r'\b' + re.escape(key) + r'\b', value, final_translated_text, flags=re.IGNORECASE)

            # --- RULE: Attorney -> Lawyer (LEGACY, kept but integrated above) ---
            # Pre-existing logic was: replace attorney with Lawyer. 
            # The job_titles_map handles 'attorney' -> 'Lawyer' already.
            
            # --- RULE: Smart Title Case (Only for Header Files) ---
            if is_cr_header_file and not should_restore:
                final_translated_text = smart_title_case(final_translated_text)

            # Bungkus CDATA jika perlu
            if is_cdata:
                # Ensure the content itself doesn't contain CDATA delimiters if we're wrapping it
                cleaned_trans = final_translated_text.replace('<![CDATA[', '').replace(']]>', '')
                replacement_text = f"<![CDATA[{cleaned_trans}]]>"
            else:
                replacement_text = final_translated_text
                
            # Construct new target element and update state
            target_tag = match.group(5) # <target...>
            
            # Update state attribute if it exists, otherwise add it
            new_target_tag = re.sub(
                r'state="[^"]*"',
                'state="translated"',
                target_tag
            )
            if 'state=' not in new_target_tag:
                new_target_tag = target_tag.replace('>', ' state="translated">', 1)
            
            # Full replacement string for the TARGET element (from <target> to </target>)
            # Use replacement_text which is either CDATA wrapped or plain text
            new_target_element = new_target_tag + replacement_text + match.group(7)
            
            # Position: Group 5 start to Group 7 end
            start_pos = match.start(5)
            end_pos = match.end(7)
            
            replacements_list.append((start_pos, end_pos, new_target_element))
            
            if not should_skip:
                translated_count += 1

        # Apply all replacements
        replacements_list.sort(key=lambda x: x[0], reverse=True)
        for start, end, text in replacements_list:
            content = content[:start] + text + content[end:]
        
        # Simpan hasil dengan nama yang sesuai title
        xliff_title = extract_title_from_xliff(content)
        if xliff_title:
            # Format: Title_OriginalName_LANG.xliff
            output_filename = f"{xliff_title}_{file_path.stem}_{target_lang}{file_path.suffix}"
        else:
            # Fallback ke format lama jika tidak ada title
            output_filename = f"{file_path.stem}_{target_lang}{file_path.suffix}"
        
        output_path = Path(OUTPUT_FOLDER) / output_filename
        
        
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
    """Fungsi utama untuk menjalankan batch translation."""
    print("=" * 60)
    print("    XLIFF Batch Translator dengan DeepL API")
    print("    (WPML Compatible)")
    print("=" * 60)
    
    # Cek API Key
    if DEEPL_API_KEY == "your-api-key-here":
        print("\n[ERROR] Silakan masukkan API Key DeepL Anda!")
        print("        Buka file ini dan edit variabel DEEPL_API_KEY")
        print("        Dapatkan API Key di: https://www.deepl.com/pro-api")
        sys.exit(1)
    
    # Setup
    setup_folders()
    
    # Inisialisasi translator
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
    
    # Cek apakah ada override target language dari command line
    target_lang_override = None
    if len(sys.argv) > 1:
        target_lang_override = sys.argv[1].upper()
        print(f"\n[TARGET] Override bahasa target: {target_lang_override}")
    else:
        print(f"\n[TARGET] Bahasa target: Otomatis dari file XLIFF (fallback: {DEFAULT_TARGET_LANG})")
    
    # Ambil file XLIFF
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
    
    # Proses semua file
    start_time = datetime.now()
    total_segments = 0
    successful_files = 0
    skipped_files = 0
    
    for i, xliff_file in enumerate(xliff_files):
        segments = process_xliff_file_regex(translator, xliff_file, target_lang_override)
        
        if segments == -1:
            # File was skipped (output already exists)
            skipped_files += 1
            # [CLEANUP] If skipped because output exists, we can delete input
            print(f"  [CLEANUP] Output sudah ada, menghapus input file: {xliff_file.name}")
            try:
                os.remove(xliff_file)
            except Exception as e:
                print(f"  [!] Gagal menghapus input: {e}")
                
        elif segments > 0:
            total_segments += segments
            successful_files += 1
            
            # [CLEANUP] Successfully translated, delete input
            print(f"  [CLEANUP] Translasi sukses, menghapus input file: {xliff_file.name}")
            try:
                os.remove(xliff_file)
            except Exception as e:
                print(f"  [!] Gagal menghapus input: {e}")
                
            # Only wait if we actually processed a file and there are more to come
            # Only wait if we actually processed a file and there are more to come
            if i < len(xliff_files) - 1:
                print(f"\n[WAIT] Waiting {DELAY_BETWEEN_FILES}s before next file...")
                time.sleep(DELAY_BETWEEN_FILES)
    
    # Summary
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
    
    # Cek usage setelah selesai
    try:
        usage = translator.get_usage()
        if usage.character.valid:
            print(f"\n[INFO] Sisa kuota DeepL: {usage.character.limit - usage.character.count:,} karakter")
    except:
        pass


if __name__ == "__main__":
    main()
