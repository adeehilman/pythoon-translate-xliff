"""
Fix XLIFF Files - HTML Entity Decoder
======================================
Script untuk memperbaiki file XLIFF yang memiliki masalah double-encoding
pada HTML entities seperti &amp;amp; (seharusnya &amp;) dan &#39; (seharusnya ')

Cara penggunaan:
1. Letakkan file XLIFF yang bermasalah di folder yang ingin diperbaiki
2. Jalankan: python fix_xliff_entities.py <folder_path>
3. File akan di-overwrite dengan versi yang sudah diperbaiki
"""

import os
import sys
import re
import html
from pathlib import Path


def fix_html_entities_in_target(content):
    """
    Perbaiki HTML entities dalam tag <target> XLIFF.
    
    WPML requires for CDATA sections:
    - Bare & is valid inside CDATA (no need for &amp;)
    - &amp; inside CDATA should be converted to bare &
    - &#39; can be ' (apostrophe)
    - &quot; can be " (quote)
    
    This function fixes:
    1. &amp; inside CDATA -> bare &
    2. &#39; inside CDATA -> ' (apostrophe)
    3. &quot; inside CDATA -> " (quote)
    """
    
    def fix_cdata_content(match):
        prefix = match.group(1)  # <target...>
        cdata_start = match.group(2)  # <![CDATA[
        content_text = match.group(3)  # actual content
        cdata_end = match.group(4)  # ]]>
        suffix = match.group(5)  # </target>
        
        fixed_content = content_text
        
        # Inside CDATA, we want bare characters, not entities
        # Convert HTML entities back to bare characters
        
        # Step 1: First fix any double-encoded entities
        fixed_content = fixed_content.replace('&amp;amp;', '&')
        fixed_content = fixed_content.replace('&amp;#39;', "'")
        fixed_content = fixed_content.replace('&amp;quot;', '"')
        
        # Step 2: Convert single-encoded entities to bare characters
        # &amp; -> & (bare ampersand is valid in CDATA)
        fixed_content = fixed_content.replace('&amp;', '&')
        # &#39; -> ' (apostrophe)
        fixed_content = fixed_content.replace('&#39;', "'")
        # &quot; -> " (quote)
        fixed_content = fixed_content.replace('&quot;', '"')
        
        return f"{prefix}{cdata_start}{fixed_content}{cdata_end}{suffix}"
    
    # Pattern untuk mencari <target...><![CDATA[...]]></target>
    pattern = r'(<target[^>]*>)(<!\[CDATA\[)(.*?)(\]\]>)(</target>)'
    
    fixed = re.sub(pattern, fix_cdata_content, content, flags=re.DOTALL)
    
    return fixed


def fix_xliff_file(file_path):
    """Perbaiki satu file XLIFF."""
    print(f"[FIX] Processing: {file_path.name}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if file has issues in target CDATA sections
        has_issues = False
        
        # Extract all target CDATA contents and check for issues
        target_pattern = r'<target[^>]*><!\[CDATA\[(.*?)\]\]></target>'
        targets = re.findall(target_pattern, content, re.DOTALL)
        
        for target_content in targets:
            # Check for double-encoded entities (always an issue)
            if '&amp;amp;' in target_content:
                has_issues = True
                print(f"       Found: &amp;amp; (double-encoded)")
            if '&amp;#39;' in target_content:
                has_issues = True
                print(f"       Found: &amp;#39; (double-encoded)")
            if '&amp;quot;' in target_content:
                has_issues = True
                print(f"       Found: &amp;quot; (double-encoded)")
            
            # Check for &amp; inside CDATA - this should be bare & for WPML
            if '&amp;' in target_content:
                has_issues = True
                print(f"       Found: &amp; in CDATA (should be bare &)")
            
            # Check for &#39; - should be ' (apostrophe)
            if '&#39;' in target_content:
                has_issues = True
                print(f"       Found: &#39; in CDATA (should be ')")
            
            # Check for &quot; - should be " (quote)
            if '&quot;' in target_content:
                has_issues = True
                print(f"       Found: &quot; in CDATA (should be \")")
        
        if not has_issues:
            print(f"       [SKIP] No issues found")
            return False
        
        # Fix the content
        fixed_content = fix_html_entities_in_target(content)
        
        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        print(f"       [DONE] Fixed!")
        return True
        
    except Exception as e:
        print(f"       [ERROR] {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_xliff_entities.py <folder_path>")
        print("Example: python fix_xliff_entities.py output/batch_2")
        sys.exit(1)
    
    folder_path = Path(sys.argv[1])
    
    if not folder_path.exists():
        print(f"[ERROR] Folder not found: {folder_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("    XLIFF HTML Entity Fixer")
    print("=" * 60)
    print(f"\n[FOLDER] {folder_path}")
    
    # Find all XLIFF files
    xliff_files = list(folder_path.glob("*.xliff")) + list(folder_path.glob("*.xlf"))
    
    if not xliff_files:
        print(f"\n[!] No XLIFF files found in {folder_path}")
        sys.exit(0)
    
    print(f"\n[FILES] Found {len(xliff_files)} XLIFF files\n")
    
    fixed_count = 0
    for xliff_file in sorted(xliff_files):
        if fix_xliff_file(xliff_file):
            fixed_count += 1
    
    print("\n" + "=" * 60)
    print(f"    DONE: Fixed {fixed_count}/{len(xliff_files)} files")
    print("=" * 60)


if __name__ == "__main__":
    main()
