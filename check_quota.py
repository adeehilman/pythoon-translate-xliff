
import deepl
import sys

# API Key from translate_xliff.py
DEEPL_API_KEY = "3be77fea-610e-4d7d-ab4b-df5f09eb2c60:fx"

def check_quota():
    try:
        translator = deepl.Translator(DEEPL_API_KEY)
        usage = translator.get_usage()
        
        if usage.character.valid:
            print(f"=" * 40)
            print(f"DEEPL API QUOTA STATUS")
            print(f"=" * 40)
            print(f"Used      : {usage.character.count:,} chars")
            print(f"Limit     : {usage.character.limit:,} chars")
            print(f"Remaining : {usage.character.limit - usage.character.count:,} chars")
            print(f"=" * 40)
        else:
            print("Usage data is not valid/available.")
            
    except Exception as e:
        print(f"Error checking quota: {e}")

if __name__ == "__main__":
    check_quota()
