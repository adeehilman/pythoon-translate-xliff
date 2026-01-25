import re
import os

# Copy paste logic dari translate_xliff.py
def should_skip_translation(resname, source_text):
    """
    Menentukan apakah trans-unit ini harus dilewati dari translasi.
    """
    if not source_text or not source_text.strip():
        return True
        
    # 1. Skip jika text adalah angka saja atau angka dengan simbol
    if re.match(r'^[\d\W]+$', source_text):
        return True

    # 2. Skip jika text adalah URL atau path
    if source_text.startswith(('http:', 'https:', '/', 'file:', 'mailto:')):
        return True
        
    # 3. Skip Bricks internal IDs dan references
    # Pattern: huruf kecil semua/mix angka, ada hyphen/underscore, tanpa spasi (biasanya ID)
    # Contoh: brxe-omexvs, b-473859, 23423-234, _section-entry, field_abc123
    if re.match(r'^[a-z0-9][a-z0-9-_]+$', source_text):
        # Kecuali kata-kata umum bahasa
        common_words = ['email', 'phone', 'address', 'copyright', 'date', 'author', 'search', 'menu', 'home', 
                       'about', 'contact', 'login', 'logout', 'register', 'submit', 'cancel', 'back', 'next']
        if source_text.lower() not in common_words:
            return True
            
    # Skip CSS selectors (starts with . or #)
    if source_text.startswith(('.', '#', '{', '}')):
        return True
        
    # Skip short technical-looking strings (like CSS props)
    if re.match(r'^[a-z-]+:\s*[^;]+;?$', source_text):  # margin: 0; display: non;
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
    ]
    if source_text in skip_exact_texts:
        return True
    
    # Also skip anything starting with "CR " (template names)
    if source_text.startswith('CR '):
        return True
    
    return False

# Load file 446
file_path = r"d:\Clean Folder\Personal\BIAR JAGO NGODING\python\deep-l translate\input\Cocron Rechtsanwalt-translation-job-446.xliff"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Extract trans-units regex (simplified from original script)
trans_unit_regex = re.compile(
    r'(<trans-unit\s+resname="([^"]+)"[^>]*>.*?<source><!\[CDATA\[(.*?)\]\]></source>.*?<target[^>]*>(.*?)</target>.*?</trans-unit>)',
    re.DOTALL
)

matches = trans_unit_regex.findall(content)

print(f"Found {len(matches)} segments in file.")
print("-" * 50)

for full_match, resname, source_text, target_content in matches:
    # Check skip logic
    should_skip = should_skip_translation(resname, source_text)
    status = "SKIP" if should_skip else "TRANSLATE"
    print(f"[{status}] Resname: {resname}")
    print(f"       Source: '{source_text[:50]}...'")
    print("-" * 30)
