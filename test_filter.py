"""
Test script untuk memverifikasi filter skip translation bekerja dengan benar.
"""
import re

def should_skip_translation(resname, source_text):
    """
    Menentukan apakah trans-unit ini harus dilewati dari translasi.
    """
    if not source_text:
        return True
    
    source_text = source_text.strip()
    
    if not source_text:
        return True
    
    # 1. Skip ID random 6 karakter
    if len(source_text) == 6 and re.match(r'^[a-z]{6}$', source_text):
        return True
    
    # 2. Skip berdasarkan resname
    skip_resname_patterns = [
        r'.*\bId$',
        r'.*\bParent$',
        r'.*\bChildren$',
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
    
    # 3. Skip content patterns
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
    ]
    
    for pattern in skip_content_patterns:
        if re.match(pattern, source_text, re.IGNORECASE):
            return True
    
    # 4. Skip element names
    element_names = [
        'section', 'container', 'block', 'button', 'text', 'text-basic',
        'heading', 'image', 'template', 'icon', 'nav', 'header', 'footer',
        'sidebar', 'wrapper', 'grid', 'row', 'column', 'col', 'post-content'
    ]
    if source_text.lower() in element_names:
        if resname and ('Name' in resname or 'Tag' in resname):
            return True
    
    return False


# Test cases
test_cases = [
    # Format: (resname, source_text, expected_skip, description)
    
    # HARUS DITERJEMAHKAN (expected_skip = False)
    ("title", "Kanzlei Cocron Rechtsanwälte", False, "Page title - HARUS translate"),
    ("Rank Math Description", "Über 20 Jahre Erfahrung in der Rechtsvertretung.", False, "SEO description - HARUS translate"),
    (" Bricks Page Content 2 0 6 Settings Text", "Unsere Anwälte & Kooperationspartner", False, "Heading text - HARUS translate"),
    (" Bricks Page Content 2 0 19 Settings Text", "<p>Seit mehr als 20 Jahren vertritt Rechtsanwalt Cocron...</p>", False, "Rich text - HARUS translate"),
    ("Bricks (Überschrift)", "Unsere Erfolge", False, "Bricks heading - HARUS translate"),
    ("Bricks (Rich Text)", "<p>Hier finden Sie eine beispielhafte Aufzählung...</p>", False, "Bricks rich text - HARUS translate"),
    (" Bricks Page Content 2 0 16 Settings Text", "Zum Profil", False, "Button text - HARUS translate"),
    (" Bricks Page Content 2 0 18 Settings Text", "Rechtserfahrung seit über 20 Jahren", False, "Heading - HARUS translate"),
    ("Heading (H2)", "Erbrecht", False, "H2 heading - HARUS translate"),
    (" Bricks Page Content 2 0 0 Label", "Hero Small", False, "Label - HARUS translate"),
    (" Bricks Page Content 2 0 4 Label", "Content", False, "Label - HARUS translate"),
    
    # HARUS DI-SKIP (expected_skip = True)
    (" Bricks Page Content 2 0 0 Id", "ivleto", True, "Element ID - skip"),
    (" Bricks Page Content 2 0 0 Name", "section", True, "Element name - skip"),
    (" Bricks Page Content 2 0 1 Parent", "ivleto", True, "Parent reference - skip"),
    (" Bricks Page Content 2 0 0 Children", "hzgxpp", True, "Children reference - skip"),
    (" Bricks Page Content 2 0 0 Settings  CssGlobalClasses", "vjknoy", True, "CSS class - skip"),
    (" Bricks Page Content 2 0 9 Settings Tag", "h1", True, "HTML tag setting - skip"),
    (" Bricks Page Content 2 0 49 Settings Image Url", "https://ra-cocron.de/wp-content/uploads/image.png", True, "Image URL - skip"),
    (" Bricks Page Content 2 0 49 Settings Image Filename", "img-logo.png", True, "Filename - skip"),
    (" Bricks Page Content 2 0 12 Settings Image UseDynamicData", "{featured_image}", True, "Dynamic data - skip"),
    (" Bricks Page Content 2 0 12 Settings Image Size", "full", True, "Image size - skip"),
    (" Bricks Page Content 2 0 14 Settings Link Type", "meta", True, "Link type - skip"),
]

print("=" * 80)
print("TESTING TRANSLATION FILTER LOGIC")
print("=" * 80)

passed = 0
failed = 0

for resname, source_text, expected_skip, description in test_cases:
    result = should_skip_translation(resname, source_text)
    status = "[PASS]" if result == expected_skip else "[FAIL]"
    
    if result == expected_skip:
        passed += 1
    else:
        failed += 1
    
    action = "SKIP" if result else "TRANSLATE"
    expected_action = "SKIP" if expected_skip else "TRANSLATE"
    
    print(f"\n{status}: {description}")
    print(f"  resname: {resname[:50]}...")
    print(f"  source: {source_text[:50]}...")
    print(f"  Result: {action} (Expected: {expected_action})")

print("\n" + "=" * 80)
print(f"RESULTS: {passed} passed, {failed} failed")
print("=" * 80)

if failed == 0:
    print("\n[OK] ALL TESTS PASSED! Kode siap digunakan.")
else:
    print(f"\n[ERROR] {failed} TESTS FAILED! Perlu perbaikan.")
