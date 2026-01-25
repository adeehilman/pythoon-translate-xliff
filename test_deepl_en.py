
import deepl
import os
import sys

# Hardcoded key from user's file
DEEPL_API_KEY = "3be77fea-610e-4d7d-ab4b-df5f09eb2c60:fx"

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
    test_en_target()
