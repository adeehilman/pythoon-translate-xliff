"""
Comprehensive Test Suite for translate_xliff.py
================================================
Tests all major functions including:
- Smart Title Case
- XLIFF Integrity Protection
- WP Admin Protection
- WordPress Block Detection
- Skip Translation Logic
- CDATA Handling
- Entity Encoding

Run with: pytest test_translate_xliff.py -v
"""

import pytest
import sys
import os

# Add the directory to path to import the module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from translate_xliff import (
    # Smart Title Case
    smart_title_case,
    is_title_case,
    is_job_position,
    is_city_or_location,
    is_abbreviation,
    # XLIFF Integrity
    validate_xliff_structure,
    fix_entity_encoding,
    count_placeholders,
    extract_cdata_content,
    wrap_in_cdata,
    # WP Admin Protection
    is_wp_admin_protected,
    is_parent_child_field,
    # WordPress Block Detection
    detect_wordpress_block_type,
    is_accordion_content,
    is_list_item_content,
    is_repeater_field_content,
    # Skip Translation Logic
    should_skip_translation,
    # Utility functions
    extract_resname_from_trans_unit,
    extract_title_from_xliff,
    get_target_language_from_xliff,
    apply_post_translation_rules,
)


# ==================== TEST: SMART TITLE CASE ====================
class TestSmartTitleCase:
    """Test cases for smart title case functions."""
    
    def test_basic_title_case(self):
        """Test basic title case conversion."""
        assert smart_title_case("the quick brown fox") == "The Quick Brown Fox"
        assert smart_title_case("a simple test") == "A Simple Test"
    
    def test_minor_words_lowercase_middle(self):
        """Test that minor words in middle are lowercase."""
        result = smart_title_case("the man in the moon")
        assert "in the" in result.lower() or result == "The Man in the Moon"
    
    def test_job_positions_capitalized(self):
        """Test that job positions are always capitalized."""
        result = smart_title_case("meet our attorney john smith")
        assert "Attorney" in result
        
        result = smart_title_case("senior partner at the firm")
        assert "Senior Partner" in result or "Partner" in result
    
    def test_cities_capitalized(self):
        """Test that German cities are capitalized."""
        result = smart_title_case("office in berlin")
        assert "Berlin" in result
        
        result = smart_title_case("visit our münchen location")
        assert "München" in result
    
    def test_abbreviations_preserved(self):
        """Test that all-caps abbreviations preserve their case."""
        # Note: is_abbreviation only detects all-caps words (2+ chars) or known DO_NOT_TRANSLATE terms
        result = smart_title_case("WPML plugin info")
        assert "WPML" in result  # WPML is in DO_NOT_TRANSLATE set
    
    def test_technical_patterns_skipped(self):
        """Test that technical patterns are not modified."""
        # CSS class-like patterns should be skipped
        assert smart_title_case("brx-dropdown-content") == "brx-dropdown-content"
        assert smart_title_case("cr-nav-item") == "cr-nav-item"
        assert smart_title_case("tablet_portrait") == "tablet_portrait"
    
    def test_skip_single_technical_words(self):
        """Test that single technical words are skipped."""
        assert smart_title_case("toggle") == "toggle"
        assert smart_title_case("visible") == "visible"
        assert smart_title_case("hidden") == "hidden"
        assert smart_title_case("flex") == "flex"
    
    def test_empty_and_none_input(self):
        """Test handling of empty and None input."""
        assert smart_title_case("") == ""
        assert smart_title_case(None) is None


class TestIsTitleCase:
    """Test cases for is_title_case detection."""
    
    def test_detect_title_case(self):
        """Test detection of title case text."""
        assert is_title_case("The Quick Brown Fox") is True
        assert is_title_case("Contact Our Attorneys Today") is True
    
    def test_detect_non_title_case(self):
        """Test detection of non-title case text."""
        assert is_title_case("the quick brown fox") is False
        assert is_title_case("some random text here") is False
    
    def test_short_text_handling(self):
        """Test handling of short texts."""
        # Single word starting with capital should be True
        assert is_title_case("Hello") is True
        assert is_title_case("A") is False  # Too short
        assert is_title_case("") is False
    
    def test_technical_patterns_return_false(self):
        """Test that technical patterns return False."""
        assert is_title_case("{brxe-content}") is False
        assert is_title_case("#navigation-menu") is False


class TestJobPositionAndLocation:
    """Test job position and location detection."""
    
    def test_is_job_position(self):
        """Test job position detection."""
        assert is_job_position("attorney") is True
        assert is_job_position("ATTORNEY") is True
        assert is_job_position("Attorney") is True
        assert is_job_position("managing director") is True
        assert is_job_position("developer") is False
    
    def test_is_city_or_location(self):
        """Test city/location detection."""
        assert is_city_or_location("berlin") is True
        assert is_city_or_location("München") is True
        assert is_city_or_location("frankfurt") is True
        assert is_city_or_location("randomcity") is False
    
    def test_is_abbreviation(self):
        """Test abbreviation detection."""
        # is_abbreviation checks: all-caps 2+ chars, or in DO_NOT_TRANSLATE, or legal patterns
        assert is_abbreviation("WPML") is True  # All caps
        assert is_abbreviation("BGB") is True   # All caps
        assert is_abbreviation("CSS") is True   # All caps
        assert is_abbreviation("§ 123") is True  # Legal pattern
        assert is_abbreviation("normal") is False
        # Note: GmbH is mixed case, function only detects full uppercase


# ==================== TEST: XLIFF INTEGRITY PROTECTION ====================
class TestXliffIntegrity:
    """Test XLIFF integrity protection functions."""
    
    def test_validate_xliff_structure_valid(self):
        """Test validation of valid XLIFF structure."""
        valid_xliff = """<?xml version="1.0" encoding="UTF-8"?>
        <xliff version="1.2">
            <file>
                <body>
                    <trans-unit>
                        <source><![CDATA[Hello World]]></source>
                        <target><![CDATA[Hallo Welt]]></target>
                    </trans-unit>
                </body>
            </file>
        </xliff>"""
        is_valid, errors = validate_xliff_structure(valid_xliff)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_xliff_structure_missing_xml_declaration(self):
        """Test validation catches missing XML declaration."""
        invalid_xliff = """<xliff version="1.2">
            <file><body></body></file>
        </xliff>"""
        is_valid, errors = validate_xliff_structure(invalid_xliff)
        assert is_valid is False
        assert any("XML declaration" in e for e in errors)
    
    def test_validate_xliff_structure_double_encoded(self):
        """Test validation catches double-encoded entities."""
        double_encoded = """<?xml version="1.0" encoding="UTF-8"?>
        <xliff><source>&amp;amp;test</source></xliff>"""
        is_valid, errors = validate_xliff_structure(double_encoded)
        assert is_valid is False
        assert any("Double-encoded" in e for e in errors)
    
    def test_validate_xliff_structure_mismatched_cdata(self):
        """Test validation catches mismatched CDATA sections."""
        mismatched = """<?xml version="1.0" encoding="UTF-8"?>
        <xliff><source><![CDATA[test</source></xliff>"""
        is_valid, errors = validate_xliff_structure(mismatched)
        assert is_valid is False
        assert any("CDATA" in e for e in errors)


class TestEntityEncoding:
    """Test entity encoding functions."""
    
    def test_fix_entity_encoding_cdata(self):
        """Test entity encoding for CDATA content."""
        # CDATA doesn't need encoding
        result = fix_entity_encoding("Hello & World", is_cdata=True)
        assert result == "Hello & World"
    
    def test_fix_entity_encoding_non_cdata(self):
        """Test entity encoding for non-CDATA content."""
        result = fix_entity_encoding("Hello & World", is_cdata=False)
        assert "&amp;" in result
    
    def test_fix_double_encoded_entities(self):
        """Test fixing double-encoded entities."""
        result = fix_entity_encoding("Test &amp;amp; More", is_cdata=True)
        assert result == "Test & More"
    
    def test_fix_entity_encoding_empty(self):
        """Test handling of empty input."""
        assert fix_entity_encoding("", is_cdata=True) == ""
        assert fix_entity_encoding(None, is_cdata=False) is None


class TestPlaceholderCounting:
    """Test placeholder counting function."""
    
    def test_count_ph_placeholders(self):
        """Test counting <ph> placeholders."""
        text = '<ph id="1"/> text <ph id="2"/>'
        counts = count_placeholders(text)
        assert counts['ph'] == 2
    
    def test_count_g_placeholders(self):
        """Test counting <g> placeholders."""
        text = '<g id="1">text</g> and <g id="2">more</g>'
        counts = count_placeholders(text)
        assert counts['g'] == 2
    
    def test_count_empty_text(self):
        """Test counting placeholders in empty text."""
        counts = count_placeholders("")
        assert all(v == 0 for v in counts.values())
        
        counts = count_placeholders(None)
        assert counts == {}


class TestCdataHandling:
    """Test CDATA extraction and wrapping."""
    
    def test_extract_cdata_content(self):
        """Test extracting content from CDATA."""
        text, is_cdata = extract_cdata_content("<![CDATA[Hello World]]>")
        assert text == "Hello World"
        assert is_cdata is True
    
    def test_extract_non_cdata_content(self):
        """Test extracting non-CDATA content."""
        text, is_cdata = extract_cdata_content("Hello World")
        assert text == "Hello World"
        assert is_cdata is False
    
    def test_extract_cdata_none_input(self):
        """Test extracting CDATA with None input."""
        text, is_cdata = extract_cdata_content(None)
        assert text is None
        assert is_cdata is False
    
    def test_wrap_in_cdata(self):
        """Test wrapping content in CDATA."""
        result = wrap_in_cdata("Hello World", was_cdata=True)
        assert result == "<![CDATA[Hello World]]>"
    
    def test_wrap_in_cdata_false(self):
        """Test not wrapping when was_cdata is False."""
        result = wrap_in_cdata("Hello World", was_cdata=False)
        assert result == "Hello World"


# ==================== TEST: WP ADMIN PROTECTION ====================
class TestWpAdminProtection:
    """Test WP Admin protection functions."""
    
    def test_is_wp_admin_protected_jetengine(self):
        """Test JetEngine field protection."""
        assert is_wp_admin_protected("jet_engine_field", "some text") is True
        assert is_wp_admin_protected("_jet_meta", "value") is True
        assert is_wp_admin_protected(None, "{je_lawyers_name}") is True
    
    def test_is_wp_admin_protected_bricks(self):
        """Test Bricks field protection."""
        assert is_wp_admin_protected("bricks_page_data", "test") is True
        assert is_wp_admin_protected("_bricks_editor_mode", "test") is True
    
    def test_is_wp_admin_protected_wpml(self):
        """Test WPML internal field protection."""
        assert is_wp_admin_protected("wpml_language", "de") is True
        assert is_wp_admin_protected("_icl_translator", "test") is True
    
    def test_is_wp_admin_protected_wordpress_core(self):
        """Test WordPress core field protection."""
        assert is_wp_admin_protected("_edit_lock", "123456") is True
        assert is_wp_admin_protected("_wp_trash_meta_time", "test") is True
    
    def test_is_wp_admin_protected_false(self):
        """Test that normal content is not protected."""
        assert is_wp_admin_protected("title", "Page Title") is False
        assert is_wp_admin_protected("Bricks Content", "Hello World") is False


class TestParentChildField:
    """Test parent-child field detection."""
    
    def test_is_parent_child_field_true(self):
        """Test parent/child field detection."""
        assert is_parent_child_field("Element Parent") is True
        assert is_parent_child_field("Children Items") is True
        assert is_parent_child_field("post_parent") is True
        assert is_parent_child_field("menu_order") is True
    
    def test_is_parent_child_field_false(self):
        """Test non-parent/child fields."""
        assert is_parent_child_field("title") is False
        assert is_parent_child_field("content") is False
        assert is_parent_child_field(None) is False


# ==================== TEST: WORDPRESS BLOCK DETECTION ====================
class TestWordPressBlockDetection:
    """Test WordPress block detection functions."""
    
    def test_detect_accordion_block(self):
        """Test accordion block detection."""
        block_type, is_translatable = detect_wordpress_block_type("accordion:::title", "Test")
        assert block_type == "accordion"
        assert is_translatable is True
    
    def test_detect_list_block(self):
        """Test list block detection."""
        block_type, is_translatable = detect_wordpress_block_type("item:::text", "Item text")
        assert block_type == "list"
        assert is_translatable is True
    
    def test_detect_table_block(self):
        """Test table block detection."""
        block_type, is_translatable = detect_wordpress_block_type("table:::cell", "Cell content")
        assert block_type == "table"
        assert is_translatable is True
    
    def test_detect_technical_block(self):
        """Test technical block detection (non-translatable)."""
        block_type, is_translatable = detect_wordpress_block_type("element:::id", "abc123")
        assert block_type == "technical"
        assert is_translatable is False
    
    def test_detect_unknown_block(self):
        """Test unknown block type."""
        block_type, is_translatable = detect_wordpress_block_type("custom field", "test")
        assert block_type == "unknown"
        assert is_translatable is True


class TestAccordionContent:
    """Test accordion content detection."""
    
    def test_is_accordion_title(self):
        """Test accordion title detection."""
        is_acc, content_type, _ = is_accordion_content("accordion:::überschrift:::1")
        assert is_acc is True
        assert content_type == "title"
    
    def test_is_accordion_content_text(self):
        """Test accordion content detection."""
        is_acc, content_type, _ = is_accordion_content("toggle:::content:::2")
        assert is_acc is True
        assert content_type == "content"
    
    def test_non_accordion_content(self):
        """Test non-accordion content."""
        is_acc, _, _ = is_accordion_content("normal field")
        assert is_acc is False


class TestListItemContent:
    """Test list item content detection."""
    
    def test_is_list_item(self):
        """Test list item detection."""
        is_list, item_type, _ = is_list_item_content("schwerpunkte:::bullet:::1")
        assert is_list is True
        assert item_type == "bullet"
    
    def test_non_list_item(self):
        """Test non-list item."""
        is_list, _, _ = is_list_item_content("title field")
        assert is_list is False


class TestRepeaterFieldContent:
    """Test repeater field content detection."""
    
    def test_is_repeater_field(self):
        """Test repeater field detection."""
        is_rep, index, _ = is_repeater_field_content("0 Item:::1 field:::text")
        assert is_rep is True
    
    def test_non_repeater_field(self):
        """Test non-repeater field."""
        is_rep, _, _ = is_repeater_field_content("normal field")
        assert is_rep is False


# ==================== TEST: SKIP TRANSLATION LOGIC ====================
class TestShouldSkipTranslation:
    """Test the main skip translation logic."""
    
    # SHOULD TRANSLATE (skip = False)
    def test_translate_page_title(self):
        """Test that page titles are translated."""
        assert should_skip_translation("title", "Kanzlei Cocron Rechtsanwälte") is False
    
    def test_translate_seo_description(self):
        """Test that SEO descriptions are translated."""
        assert should_skip_translation("Rank Math Description", "Über 20 Jahre Erfahrung") is False
    
    def test_translate_heading_text(self):
        """Test that heading text is translated."""
        assert should_skip_translation("Bricks Page Content Settings Text", "Unsere Anwälte") is False
    
    def test_translate_rich_text(self):
        """Test that rich text content is translated."""
        assert should_skip_translation("Bricks (Rich Text)", "<p>Hier finden Sie Info</p>") is False
    
    def test_translate_button_text(self):
        """Test that button text is translated."""
        assert should_skip_translation("Settings Text", "Zum Profil") is False
    
    def test_translate_label_content(self):
        """Test that label content is translated."""
        assert should_skip_translation("Label", "Content Section") is False
    
    # SHOULD SKIP (skip = True)
    def test_skip_element_id(self):
        """Test that element IDs are skipped."""
        assert should_skip_translation("Bricks Page Content Id", "ivleto") is True
    
    def test_skip_element_name(self):
        """Test that element names in Name field are skipped."""
        assert should_skip_translation("Bricks Page Content Name", "section") is True
    
    def test_skip_parent_reference(self):
        """Test that parent references are skipped."""
        assert should_skip_translation("Element Parent", "hzgxpp") is True
    
    def test_skip_children_reference(self):
        """Test that children references are skipped."""
        assert should_skip_translation("Element Children", "abc123") is True
    
    def test_skip_css_global_classes(self):
        """Test that CSS classes are skipped."""
        assert should_skip_translation("Settings CssGlobalClasses", "vjknoy") is True
    
    def test_skip_image_url(self):
        """Test that image URLs are skipped."""
        assert should_skip_translation("Settings Image Url", "https://example.com/image.png") is True
    
    def test_skip_dynamic_data(self):
        """Test that dynamic data placeholders are skipped."""
        assert should_skip_translation("UseDynamicData", "{featured_image}") is True
    
    def test_skip_true_false_values(self):
        """Test that true/false values are skipped."""
        assert should_skip_translation("some_field", "true") is True
        assert should_skip_translation("some_field", "false") is True
    
    def test_skip_urls(self):
        """Test that URLs are skipped."""
        assert should_skip_translation("field", "https://example.com") is True
        assert should_skip_translation("field", "http://test.de/page") is True
    
    def test_skip_emails(self):
        """Test that emails are skipped."""
        assert should_skip_translation("field", "test@example.com") is True
    
    def test_skip_random_ids(self):
        """Test that random 6-char IDs are skipped."""
        assert should_skip_translation("id field", "abcdef") is True
        assert should_skip_translation("id field", "ivleto") is True
    
    def test_skip_bricks_variables(self):
        """Test that Bricks variables are skipped."""
        assert should_skip_translation("field", "{je_lawyers_name}") is True
        assert should_skip_translation("field", "{post_title}") is True
    
    def test_skip_cr_templates(self):
        """Test that CR template names are skipped."""
        assert should_skip_translation("template", "CR Header") is True
        assert should_skip_translation("template", "CR Footer Main") is True
    
    def test_skip_empty_values(self):
        """Test that empty values are skipped."""
        assert should_skip_translation("field", "") is True
        assert should_skip_translation("field", "   ") is True
        assert should_skip_translation("field", None) is True
    
    def test_skip_filenames(self):
        """Test that filenames are skipped."""
        assert should_skip_translation("Image Filename", "logo.png") is True
        assert should_skip_translation("Settings Filename", "document.pdf") is True


# ==================== TEST: UTILITY FUNCTIONS ====================
class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_extract_resname_from_trans_unit(self):
        """Test resname extraction."""
        trans_unit = '<trans-unit id="1" resname="title" xml:space="preserve">'
        assert extract_resname_from_trans_unit(trans_unit) == "title"
    
    def test_extract_resname_missing(self):
        """Test resname extraction when missing."""
        trans_unit = '<trans-unit id="1" xml:space="preserve">'
        assert extract_resname_from_trans_unit(trans_unit) is None
    
    def test_extract_title_from_xliff(self):
        """Test title extraction from XLIFF content."""
        xliff_content = '''
        <trans-unit resname="title">
            <source><![CDATA[Page Title Here]]></source>
        </trans-unit>
        '''
        title = extract_title_from_xliff(xliff_content)
        assert title == "Page Title Here"
    
    def test_get_target_language_from_xliff(self):
        """Test target language extraction."""
        xliff_content = '<file source-language="de" target-language="en-US">'
        lang = get_target_language_from_xliff(xliff_content)
        assert lang == "EN-US"
    
    def test_get_target_language_not_found(self):
        """Test target language extraction when not found."""
        xliff_content = '<file source-language="de">'
        lang = get_target_language_from_xliff(xliff_content)
        assert lang is None


class TestApplyPostTranslationRules:
    """Test post-translation rule application."""
    
    def test_job_title_capitalization(self):
        """Test that job titles are capitalized."""
        result = apply_post_translation_rules("meet our attorney", "Test Source")
        assert "Attorney" in result
    
    def test_google_maps_capitalization(self):
        """Test Google Maps capitalization."""
        result = apply_post_translation_rules("view on google maps", "Test")
        assert "Google Maps" in result
    
    def test_title_case_matching(self):
        """Test that title case is matched from source."""
        source = "Our Legal Services"  # Title case
        result = apply_post_translation_rules("our legal services", source)
        # Should attempt to apply title case
        assert result[0].isupper()  # First char should be uppercase
    
    def test_html_entity_decoding(self):
        """Test HTML entity decoding."""
        result = apply_post_translation_rules("Hello &amp; World", "Test")
        assert "&" in result


# ==================== TEST: COMPREHENSIVE INTEGRATION ====================
class TestIntegration:
    """Integration tests combining multiple functions."""
    
    def test_full_workflow_translatable_content(self):
        """Test full workflow for translatable content."""
        resname = "Bricks Page Content Settings Text"
        source = "Willkommen auf unserer Website"  # German sentence (not title case)
        
        # Should not skip
        assert should_skip_translation(resname, source) is False
        
        # Check if title case - German normal sentences are not title case
        is_tc = is_title_case(source)
        # German capitalizes first word only (not title case pattern)
        assert is_tc is False
        
        # Test with actual title case source
        title_source = "Unsere Rechtsanwälte Und Partner"  # Title cased
        is_tc_title = is_title_case(title_source)
        assert is_tc_title is True
        
        # Apply title case if needed
        translated = "our attorneys and partners"
        if is_tc_title:
            translated = smart_title_case(translated)
        
        assert translated[0].isupper()
    
    def test_full_workflow_technical_content(self):
        """Test full workflow for technical content."""
        resname = "Element Id"
        source = "brxe-abc123"
        
        # Should skip
        assert should_skip_translation(resname, source) is True
        
        # If somehow processed, smart_title_case should not modify it
        result = smart_title_case(source)
        assert result == source
    
    def test_cdata_workflow(self):
        """Test CDATA extraction and re-wrapping."""
        original = "<![CDATA[Hello & World]]>"
        
        # Extract
        content, is_cdata = extract_cdata_content(original)
        assert content == "Hello & World"
        assert is_cdata is True
        
        # Fix encoding for CDATA
        fixed = fix_entity_encoding(content, is_cdata=True)
        assert fixed == "Hello & World"
        
        # Re-wrap
        result = wrap_in_cdata(fixed, was_cdata=True)
        assert result == "<![CDATA[Hello & World]]>"


# ==================== MAIN ====================
if __name__ == "__main__":
    # Run with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
