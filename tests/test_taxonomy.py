import unittest
import json
from dms.taxonomy import (
    get_vocabulary_list,
    load_taxonomy,
    get_terms,
    get_term_info,
    get_deprecated_terms,
    get_change_log,
    get_vocabulary_structure,
)

class TestTaxonomy(unittest.TestCase):
    def test_vocabulary_list(self):
        vocs = get_vocabulary_list()
        self.assertIn("types", vocs)
        self.assertIn("roles", vocs)
        self.assertIn("relation_types", vocs)

    def test_load_taxonomy(self):
        tax = load_taxonomy("types")
        self.assertEqual(tax["id"], "dms:HeritageTypes")
        self.assertEqual(tax["type"], "skos:ConceptScheme")
        self.assertTrue(len(tax["hasTopConcept"]) > 0)

    def test_get_term_info(self):
        term = get_term_info("types", "story")
        self.assertIsNotNone(term)
        self.assertEqual(term["label"], "Story")
        self.assertEqual(term["short_id"], "story")

        # Test non-existent term
        self.assertIsNone(get_term_info("types", "nonexistent"))

    def test_get_terms_subset(self):
        terms = get_terms("types", ids=["story", "photo"])
        self.assertEqual(len(terms), 2)
        self.assertEqual({term["label"] for term in terms}, {"Story", "Photograph"})

    def test_get_deprecated_terms(self):
        deprecated = get_deprecated_terms("types")
        self.assertEqual(len(deprecated), 1)
        self.assertEqual(deprecated[0]["id"], "dms:type/image")

    def test_get_change_log(self):
        history = get_change_log("types")
        self.assertTrue(any("Initial release" in entry["message"] for entry in history))

    def test_get_term_change_log(self):
        history = get_change_log("types", term_id="image")
        self.assertTrue(any("deprecated" in entry["message"].lower() for entry in history))

    def test_get_vocabulary_structure(self):
        structure = get_vocabulary_structure("types")
        self.assertEqual(structure["kind"], "flat")
        self.assertTrue(structure["supports_deprecations"])
        self.assertIn("jsonld", structure["available_formats"])

    def test_fallback_taxonomy(self):
        # 'roles' doesn't have a JSON file yet, should use fallback
        tax = load_taxonomy("roles")
        self.assertEqual(tax["id"], "dms:Roles")
        self.assertTrue(len(tax["hasTopConcept"]) > 0)
        
        # Verify a known role exists in fallback
        term = get_term_info("roles", "author")
        self.assertIsNotNone(term)

if __name__ == "__main__":
    unittest.main()
