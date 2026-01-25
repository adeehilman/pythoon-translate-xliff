"""
XLIFF Batch Translator menggunakan Google Cloud Translation API
================================================================
Script untuk menerjemahkan file XLIFF dalam jumlah banyak secara otomatis.
Kompatibel dengan WPML XLIFF export/import.

Cara penggunaan:
1. Masukkan API Key Google Cloud Anda di variabel GOOGLE_API_KEY
2. Letakkan file-file XLIFF di folder 'input'
3. Jalankan script: python translate_xliff_google.py
4. Hasil terjemahan akan tersimpan di folder 'output'
"""

import os
import sys
import re
import time
import html
import zipfile
import requests
from pathlib import Path
from datetime import datetime

# Fix encoding untuk Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ==================== KONFIGURASI ====================
# Masukkan API Key Google Cloud Anda di sini
GOOGLE_API_KEY = "AIzaSyB0BMJArddW_3MtVPAzOZSDy9KgHbkXPbc"

# Bahasa target default akan dibaca dari file XLIFF
# Jika tidak ada di file XLIFF, gunakan command line override: python translate_xliff_google.py ES
DEFAULT_TARGET_LANG = None  # None = wajib baca dari XLIFF

# Folder input dan output
INPUT_FOLDER = "input"
OUTPUT_FOLDER = "output"

# Rate limiting - delay dalam detik antar request ke Google
DELAY_BETWEEN_REQUESTS = 0.1  # Google API lebih cepat
DELAY_BETWEEN_FILES = 1  # 1 detik antar file

# Batch size - jumlah segment per batch untuk translasi
BATCH_SIZE = 50  # Google Cloud mendukung batch lebih besar

# Output batch - jumlah file per folder batch
FILES_PER_BATCH = 5  # Maksimal 5 file per folder batch
# =====================================================


def setup_folders():
    """Membuat folder input dan output jika belum ada."""
    Path(INPUT_FOLDER).mkdir(exist_ok=True)
    Path(OUTPUT_FOLDER).mkdir(exist_ok=True)
    print(f"[OK] Folder '{INPUT_FOLDER}' dan '{OUTPUT_FOLDER}' siap digunakan")


def get_current_batch_folder():
    """
    Mendapatkan folder batch yang aktif untuk menyimpan output.
    Akan membuat batch baru jika batch saat ini sudah penuh (>= FILES_PER_BATCH).
    
    Output structure:
    - output/batch_1/ (max 5 files)
    - output/batch_2/ (max 5 files)
    - ...
    """
    output_path = Path(OUTPUT_FOLDER)
    
    # Cari semua folder batch yang ada
    batch_folders = sorted([
        d for d in output_path.iterdir() 
        if d.is_dir() and d.name.startswith('batch_')
    ], key=lambda x: int(x.name.split('_')[1]) if x.name.split('_')[1].isdigit() else 0)
    
    if not batch_folders:
        # Belum ada batch folder, buat batch_1
        new_batch = output_path / 'batch_1'
        new_batch.mkdir(exist_ok=True)
        print(f"  [BATCH] Membuat folder baru: {new_batch}")
        return new_batch
    
    # Cek batch terakhir
    last_batch = batch_folders[-1]
    xliff_files = list(last_batch.glob('*.xliff')) + list(last_batch.glob('*.xlf'))
    
    if len(xliff_files) >= FILES_PER_BATCH:
        # Batch penuh, buat batch baru
        batch_num = int(last_batch.name.split('_')[1]) + 1
        new_batch = output_path / f'batch_{batch_num}'
        new_batch.mkdir(exist_ok=True)
        print(f"  [BATCH] Folder {last_batch.name} penuh ({len(xliff_files)} files), membuat: {new_batch}")
        return new_batch
    
    return last_batch


def get_xliff_files():
    """Mendapatkan semua file XLIFF dari folder input."""
    xliff_extensions = ['.xliff', '.xlf']
    files = []
    
    for ext in xliff_extensions:
        files.extend(Path(INPUT_FOLDER).glob(f"*{ext}"))
    
    return sorted(files)


def decode_google_translation(text, is_cdata=False):
    """
    Decode HTML entities from Google Translate API response.
    Google API returns HTML-encoded text (e.g., &amp; becomes &amp;amp;, ' becomes &#39;).
    We need to decode these back to proper characters for XLIFF compatibility.
    
    For CDATA sections: bare & is valid and preferred
    For non-CDATA: &amp; is required for valid XML
    """
    if not text:
        return text
    
    # Google API returns text with HTML entities double-encoded
    # First decode the HTML entities (this converts &amp; to &, &#39; to ', etc.)
    decoded = html.unescape(text)
    
    # For CDATA content, bare & is valid - just return decoded
    # For non-CDATA content, we need to re-encode & as &amp; for valid XML
    if not is_cdata:
        # Re-encode ampersands for non-CDATA XML content
        # But be careful not to double-encode existing entities
        # Since we already unescaped, all & are now bare
        # We need to encode them back for XML compatibility
        decoded = decoded.replace('&', '&amp;')
    
    return decoded


def translate_batch_google(texts, target_lang, source_lang='de'):
    """Menerjemahkan batch teks menggunakan Google Cloud Translation API."""
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
        
        # Google Cloud Translation API v2
        url = f"https://translation.googleapis.com/language/translate/v2"
        
        # Convert target language format (EN-US -> en, ES -> es)
        google_target = target_lang.split('-')[0].lower()
        
        payload = {
            'key': GOOGLE_API_KEY,
            'q': non_empty_texts,
            'target': google_target,
            'source': source_lang.lower(),
            'format': 'html'  # Preserve HTML tags
        }
        
        response = requests.post(url, data=payload)
        
        if response.status_code == 200:
            result = response.json()
            translations = result['data']['translations']
            
            # Rebuild hasil dengan posisi yang benar
            translated = list(texts)  # Copy original
            for idx, trans in zip(non_empty_indices, translations):
                # Return raw text - decoding will be done later when we know CDATA status
                translated[idx] = trans['translatedText']
            
            return translated
        else:
            error_msg = response.json().get('error', {}).get('message', 'Unknown error')
            print(f"\n[!] Google API Error: {error_msg}")
            return texts  # Return original on error
        
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
    
    # 1. Skip jika source text terlalu pendek dan terlihat seperti ID (huruf random saja)
    if len(source_text) == 6 and re.match(r'^[a-z]{6}$', source_text):
        return True
    
    # 2. Skip berdasarkan resname (field name) yang PASTI tidak perlu ditranslate
    skip_resname_patterns = [
        # Bricks Builder internal IDs
        r'.*\bId$',                    # Ends with "Id" (element IDs)
        r'.*\bParent$',                # Parent references
        r'.*\bChildren$',              # Children references
        r'.*\b_CssGlobalClasses$',     # CSS class references
        r'.*\bCssGlobalClasses$',      # CSS class references
        
        # Technical fields
        r'.*-id$',
        r'.*-id-\d+$',
        r'.*-children-\d+$',
        r'.*-parent$',
        
        # File/media references
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
        
        # Dynamic data placeholders
        r'.*\bUseDynamicData$',
        
        # Internal Bricks references
        r'.*\bFill Id$',
        r'.*\bIcon Fill Id$',
        
        # Technical Settings fields
        r'.*\bSettings Tag$',
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
        
        # File extensions
        r'^[^/\\]+\.(webp|png|jpg|jpeg|gif|svg|pdf|mp4|mp3|ico|woff|woff2|ttf|eot)$',
        
        # Dynamic placeholders
        r'^\{[^}]+\}$',
        
        # HTML tags only
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
    
    # 4. Skip element/component names
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
    """Mengekstrak title dari konten XLIFF."""
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
    """Membaca target-language dari konten XLIFF."""
    match = re.search(r'target-language=["\']([^"\']+)["\']', content)
    if match:
        return match.group(1).upper()
    
    match = re.search(r'trgLang=["\']([^"\']+)["\']', content)
    if match:
        return match.group(1).upper()
    
    return None


def process_xliff_file_google(file_path, target_lang_override=None):
    """
    Memproses file XLIFF menggunakan Google Cloud Translation API.
    """
    print(f"\n[FILE] Memproses: {file_path.name}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        xliff_target_lang = get_target_language_from_xliff(content)
        target_lang = target_lang_override or xliff_target_lang
        
        if not target_lang:
            print(f"  [ERROR] Target language tidak ditemukan di file XLIFF!")
            print(f"          Gunakan command line override: python translate_xliff_google.py ES")
            return 0
            
        # Normalize EN to EN-US for Google API compatibility
        if target_lang == 'EN':
            target_lang = 'EN-US'
        
        source_info = 'override' if target_lang_override else 'XLIFF file'
        print(f"       Bahasa target: {target_lang} (dari {source_info})")
        
        # Cek apakah output sudah ada (di semua batch folders)
        xliff_title = extract_title_from_xliff(content)
        
        # Check if this is a CR Header file (apply title case to translations)
        is_cr_header_file = xliff_title and xliff_title.startswith('CR ')
        if is_cr_header_file:
            print(f"       [TITLE CASE] File CR Header terdeteksi, hasil translasi akan di-title case")
        
        if xliff_title:
            expected_output = f"{xliff_title}_{file_path.stem}_{target_lang}{file_path.suffix}"
        else:
            expected_output = f"{file_path.stem}_{target_lang}{file_path.suffix}"
        
        fallback_output = f"{file_path.stem}_{target_lang}{file_path.suffix}"
        
        # Cari di semua batch folders
        output_base = Path(OUTPUT_FOLDER)
        for batch_dir in output_base.iterdir():
            if batch_dir.is_dir() and batch_dir.name.startswith('batch_'):
                if (batch_dir / expected_output).exists():
                    print(f"  [SKIP] Output sudah ada: {batch_dir.name}/{expected_output}")
                    return -1
                if expected_output != fallback_output and (batch_dir / fallback_output).exists():
                    print(f"  [SKIP] Output sudah ada: {batch_dir.name}/{fallback_output}")
                    return -1
        
        # Juga cek di root output folder (untuk file lama)
        if (output_base / expected_output).exists():
            print(f"  [SKIP] Output sudah ada: {expected_output}")
            return -1
        if expected_output != fallback_output and (output_base / fallback_output).exists():
            print(f"  [SKIP] Output sudah ada: {fallback_output}")
            return -1
        
        # Pattern untuk menemukan trans-unit
        trans_unit_pattern = re.compile(
            r'(<trans-unit[^>]*>.*?<source[^>]*>)(.*?)(</source>)(.*?)(<target[^>]*>)(.*?)(</target>)',
            re.DOTALL
        )
        
        matches = list(trans_unit_pattern.finditer(content))
        
        if not matches:
            print("  [!] Tidak ada trans-unit dengan target ditemukan")
            return 0
        
        print(f"       Ditemukan {len(matches)} segment total")
        
        # Extract source texts
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
        
        # Prepare texts untuk ditranslate
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
                
                translated_batch = translate_batch_google(batch, target_lang)
                translated_results.extend(translated_batch)
        
        # Map translated results back with proper entity decoding
        translated_texts = list(source_texts)
        for i, (idx, translated) in enumerate(zip(translation_indices, translated_results)):
            # Get the CDATA status for this segment to decode properly
            is_cdata = cdata_flags[idx]
            # Decode HTML entities with proper handling based on CDATA status
            translated = decode_google_translation(translated, is_cdata=is_cdata)
            # Apply smart title case for CR Header files
            if is_cr_header_file and translated:
                translated = smart_title_case(translated)
            translated_texts[idx] = translated
        
        # Replace dalam content
        new_content = content
        translated_count = 0
        for i in range(len(matches) - 1, -1, -1):
            match = matches[i]
            translated = translated_texts[i]
            was_cdata = cdata_flags[i]
            was_skipped = skip_flags[i]
            
            if was_cdata:
                new_target_content = f"<![CDATA[{translated}]]>"
            else:
                new_target_content = translated
            
            target_tag = match.group(5)
            new_target_tag = re.sub(
                r'state="[^"]*"',
                'state="translated"',
                target_tag
            )
            if 'state=' not in new_target_tag:
                new_target_tag = target_tag.replace('>', ' state="translated">', 1)
            
            new_trans_unit = (
                match.group(1) +
                match.group(2) +
                match.group(3) +
                match.group(4) +
                new_target_tag +
                new_target_content +
                match.group(7)
            )
            
            new_content = new_content[:match.start()] + new_trans_unit + new_content[match.end():]
            
            if not was_skipped:
                translated_count += 1
        
        # Simpan hasil ke batch folder
        xliff_title = extract_title_from_xliff(content)
        if xliff_title:
            output_filename = f"{xliff_title}_{file_path.stem}_{target_lang}{file_path.suffix}"
        else:
            output_filename = f"{file_path.stem}_{target_lang}{file_path.suffix}"
        
        # Dapatkan folder batch yang aktif
        batch_folder = get_current_batch_folder()
        output_path = batch_folder / output_filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
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
    print("    XLIFF Batch Translator dengan Google Cloud Translation")
    print("    (WPML Compatible)")
    print("=" * 60)
    
    # Cek API Key
    if GOOGLE_API_KEY == "YOUR_GOOGLE_API_KEY_HERE":
        print("\n[ERROR] Silakan masukkan API Key Google Cloud Anda!")
        print("        Buka file ini dan edit variabel GOOGLE_API_KEY")
        sys.exit(1)
    
    # Setup
    setup_folders()
    
    # Test API Key
    print("\n[INFO] Testing Google Cloud Translation API...")
    try:
        test_result = translate_batch_google(["Hello"], "EN-US", "en")
        if test_result:
            print("[OK] Google Cloud Translation API siap digunakan!")
    except Exception as e:
        print(f"[ERROR] Gagal terhubung ke Google API: {e}")
        sys.exit(1)
    
    # Cek command line override
    target_lang_override = None
    if len(sys.argv) > 1:
        target_lang_override = sys.argv[1].upper()
        print(f"\n[TARGET] Override bahasa target: {target_lang_override}")
    else:
        print(f"\n[TARGET] Bahasa target: Otomatis dari file XLIFF")
    
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
        segments = process_xliff_file_google(xliff_file, target_lang_override)
        
        if segments == -1:
            skipped_files += 1
            # [CLEANUP] If skipped because output exists, delete input
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


def zip_batch_folders():
    """
    Membuat file ZIP untuk setiap batch folder yang penuh.
    File zip akan disimpan di folder output dengan nama batch_X.zip
    """
    output_path = Path(OUTPUT_FOLDER)
    
    # Cari semua batch folders
    batch_folders = sorted([
        d for d in output_path.iterdir() 
        if d.is_dir() and d.name.startswith('batch_')
    ], key=lambda x: int(x.name.split('_')[1]) if x.name.split('_')[1].isdigit() else 0)
    
    if not batch_folders:
        print("\n[ZIP] Tidak ada batch folder untuk di-zip")
        return
    
    print("\n" + "=" * 60)
    print("    MEMBUAT ZIP FILES")
    print("=" * 60)
    
    for batch_folder in batch_folders:
        xliff_files = list(batch_folder.glob('*.xliff')) + list(batch_folder.glob('*.xlf'))
        
        if not xliff_files:
            print(f"[ZIP] {batch_folder.name}: Folder kosong, skip")
            continue
        
        zip_filename = f"{batch_folder.name}.zip"
        zip_path = output_path / zip_filename
        
        # Cek jika zip sudah ada dan up-to-date
        if zip_path.exists():
            # Cek apakah ada file baru sejak zip dibuat
            zip_mtime = zip_path.stat().st_mtime
            newest_file_mtime = max(f.stat().st_mtime for f in xliff_files)
            
            if zip_mtime > newest_file_mtime:
                print(f"[ZIP] {zip_filename}: Sudah up-to-date ({len(xliff_files)} files)")
                continue
        
        # Buat zip file
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for xliff_file in xliff_files:
                    # Simpan dengan nama file saja (tanpa path)
                    zf.write(xliff_file, xliff_file.name)
            
            zip_size_kb = zip_path.stat().st_size / 1024
            print(f"[ZIP] {zip_filename}: {len(xliff_files)} files, {zip_size_kb:.1f} KB")
        except Exception as e:
            print(f"[ZIP] {zip_filename}: Error - {e}")


if __name__ == "__main__":
    main()
    # Buat zip files setelah translasi selesai
    zip_batch_folders()
