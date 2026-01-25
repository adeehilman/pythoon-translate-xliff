
import re
from translate_xliff import should_skip_translation, extract_resname_from_trans_unit

def test_items():
    items = [
        # (resname, source_text, expected_skip: False)
        ("title", "Unsere Erfolge", False),
        (" Bricks Page Content 2 0 2 Settings Text", "Unsere Erfolge", False),
        (" Bricks Page Content 2 0 9 Settings Text", "<p>Hier finden Sie eine beispielhafte Aufzählung einiger Erfolge, die wir für unsere Mandanten erzielen konnten.</p>", False),
        ("Heading (H2)", "Online Casino", False),
        ("Heading (H2)", "Erbrecht", False),
        ("Heading (H2)", "Strafverfahren wegen Teilnahme am illegalen Online Glücksspiel", False),
        
        # Items that SHOULD be skipped
        (" Bricks Page Content 2 0 0 Id", "vsmuzk", True),
        (" Bricks Page Content 2 0 0 Name", "section", True),
        (" Bricks Page Content 2 0 0 Children", "degtyj", True),
        (" Bricks Page Content 2 0 0 Settings  CssGlobalClasses", "vjknoy", True),
    ]

    print("Testing should_skip_translation logic:\n")
    
    for resname, text, expected in items:
        skipped = should_skip_translation(resname, text)
        status = "SKIPPED" if skipped else "TRANSLATE"
        match = "OK" if skipped == expected else "FAIL"
        print(f"[{match}] {status:<10} | Resname: {resname[:30]:<30} | Text: {text[:30]}...")
        
        if skipped != expected:
            print(f"    >>> ERROR: Expected {expected} but got {skipped}")

if __name__ == "__main__":
    test_items()
