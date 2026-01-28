
import deepl
import os
import sys

# Hardcoded key from user's file
DEEPL_API_KEY = "7d310721-db7e-45b2-9c1f-11071e317678"

def check_quota():
    """Check DeepL API usage and quota."""
    print("=" * 60)
    print("    DeepL API Usage Check")
    print("=" * 60)
    
    try:
        translator = deepl.Translator(DEEPL_API_KEY)
        usage = translator.get_usage()
        
        if usage.character.valid:
            used = usage.character.count
            limit = usage.character.limit
            remaining = limit - used
            percent_used = (used / limit) * 100
            
            print(f"\n  Character Usage:")
            print(f"     Used      : {used:,} characters")
            print(f"     Limit     : {limit:,} characters")
            print(f"     Remaining : {remaining:,} characters")
            print(f"     Percent   : {percent_used:.2f}% used")
            
            # Progress bar
            bar_length = 40
            filled = int(bar_length * used / limit)
            bar = "#" * filled + "-" * (bar_length - filled)
            print(f"\n     [{bar}]")
            
            if percent_used > 90:
                print("\n  WARNING: Quota almost exhausted!")
            elif percent_used > 75:
                print("\n  NOTE: Quota usage is high")
            else:
                print("\n  OK: Quota is healthy")
        else:
            print("  ERROR: Unable to retrieve usage information")
            
    except deepl.AuthorizationException:
        print("  ERROR: Invalid API Key!")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    print("\n" + "=" * 60)

def test_en_target():
    translator = deepl.Translator(DEEPL_API_KEY)
    text = "Halo dunia"
    
    print("Testing target_lang='EN'...")
    try:
        result = translator.translate_text(text, target_lang="EN")
        print(f"SUCCESS: {result.text}")
    except Exception as e:
        print(f"FAILED: {e}")

    print("\nTesting target_lang='EN-US'...")
    try:
        result = translator.translate_text(text, target_lang="EN-US")
        print(f"SUCCESS: {result.text}")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    # Check quota first
    check_quota()
    
    # Uncomment to test translation
    # test_en_target()
