"""
Test untuk kalimat campuran German-Spanish
"""
from translate_xliff import should_skip_translation, smart_title_case, is_title_case, apply_post_translation_rules

test_text = 'Abogada & Kooperationspartnerin in Spanien'
resname = 'Settings Text'

print('='*60)
print('TEST: Mixed Language Sentence')
print('='*60)
print(f'Text: {test_text}')
print(f'Resname: {resname}')
print()
print(f'Should Skip Translation: {should_skip_translation(resname, test_text)}')
print(f'Is Title Case: {is_title_case(test_text)}')
print(f'After Smart Title Case: {smart_title_case(test_text)}')
print()

# Simulasi apa yang akan terjadi
print('='*60)
print('ANALISIS:')
print('='*60)
print('1. Teks TIDAK akan di-skip (bukan technical)')
print('2. DeepL AKAN menerjemahkan seluruh teks')
print()
print('Target EN-US -> "Lawyer & Cooperation Partner in Spain"')
print('Target ES    -> "Abogada y socia de cooperacion en Espana"')
print()
print('NOTE: DeepL cukup pintar mengenali bahwa "Abogada" adalah')
print('      Spanish dan akan menjaga atau translate sesuai konteks.')
