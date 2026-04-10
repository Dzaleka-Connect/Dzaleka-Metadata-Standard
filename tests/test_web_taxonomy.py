import unittest
import threading
import time
import urllib.request
import urllib.error
import json
from http.server import HTTPServer
from pathlib import Path
from dms.web import make_handler

class TestWebTaxonomy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Setup dummy records dir
        cls.records_dir = Path("test_records_temp")
        cls.records_dir.mkdir(exist_ok=True)
        
        # Start server in background thread
        cls.port = 8123
        handler = make_handler(cls.records_dir)
        cls.server = HTTPServer(("127.0.0.1", cls.port), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.daemon = True
        cls.thread.start()
        
        # Allow server to start
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        import shutil
        if cls.records_dir.exists():
            shutil.rmtree(cls.records_dir)

    def test_api_taxonomy_list(self):
        url = f"http://127.0.0.1:{self.port}/api/taxonomy"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            self.assertIn("types", data["vocabularies"])

    def test_api_taxonomy_voc(self):
        url = f"http://127.0.0.1:{self.port}/api/taxonomy/types"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            self.assertEqual(data["id"], "dms:HeritageTypes")

    def test_api_taxonomy_term_json(self):
        url = f"http://127.0.0.1:{self.port}/api/taxonomy/types/story"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            self.assertEqual(data["label"], "Story")

    def test_api_taxonomy_term_html(self):
        url = f"http://127.0.0.1:{self.port}/api/taxonomy/types/story"
        req = urllib.request.Request(url, headers={"Accept": "text/html"})
        with urllib.request.urlopen(req) as response:
            html = response.read().decode()
            self.assertIn("<h1>Story</h1>", html)
            self.assertIn("DMS Vocabulary", html)

    def test_api_taxonomy_deprecated(self):
        url = f"http://127.0.0.1:{self.port}/api/taxonomy/types/deprecated"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["id"], "dms:type/image")

    def test_api_taxonomy_terms_subset(self):
        url = f"http://127.0.0.1:{self.port}/api/taxonomy/types/terms?ids=story,photo"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            self.assertEqual(data["count"], 2)
            self.assertEqual({term["label"] for term in data["terms"]}, {"Story", "Photograph"})

    def test_api_taxonomy_structure(self):
        url = f"http://127.0.0.1:{self.port}/api/taxonomy/types/structure"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            self.assertEqual(data["kind"], "flat")
            self.assertTrue(data["supports_deprecations"])

    def test_api_taxonomy_changes(self):
        url = f"http://127.0.0.1:{self.port}/api/taxonomy/types/changes"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            self.assertTrue(any("Initial release" in entry["message"] for entry in data))

    def test_api_taxonomy_turtle(self):
        url = f"http://127.0.0.1:{self.port}/api/taxonomy/types?format=ttl"
        with urllib.request.urlopen(url) as response:
            payload = response.read().decode()
            self.assertIn("@prefix skos:", payload)
            self.assertIn("ConceptScheme", payload)

    def test_api_taxonomy_rdfxml(self):
        url = f"http://127.0.0.1:{self.port}/api/taxonomy/types?format=rdfxml"
        with urllib.request.urlopen(url) as response:
            payload = response.read().decode()
            self.assertIn("<rdf:RDF", payload)
            self.assertIn("<skos:ConceptScheme", payload)

    def test_api_schema_includes_v11_enums(self):
        url = f"http://127.0.0.1:{self.port}/api/schema"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            self.assertIn("obtained", data["consent_statuses"])
            self.assertIn("transcription_of", data["relation_types"])
            self.assertIn("sha256", data["checksum_algorithms"])

    def test_same_origin_post_is_allowed(self):
        url = f"http://127.0.0.1:{self.port}/api/validate"
        payload = json.dumps({
            "id": "b3e7c8a1-4d5f-6e7a-8b9c-0d1e2f3a4b5c",
            "title": "Test Record",
            "type": "story",
            "description": "A test heritage record.",
            "language": "en",
        }).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Origin": f"http://127.0.0.1:{self.port}",
            },
        )
        with urllib.request.urlopen(request) as response:
            data = json.loads(response.read().decode())
            self.assertTrue(data["valid"])
            self.assertEqual(
                response.headers.get("Access-Control-Allow-Origin"),
                f"http://127.0.0.1:{self.port}",
            )

    def test_cross_origin_post_is_rejected(self):
        url = f"http://127.0.0.1:{self.port}/api/validate"
        payload = json.dumps({
            "id": "b3e7c8a1-4d5f-6e7a-8b9c-0d1e2f3a4b5c",
            "title": "Test Record",
            "type": "story",
            "description": "A test heritage record.",
            "language": "en",
        }).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Origin": "https://evil.example",
            },
        )
        with self.assertRaises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(request)
        self.assertEqual(exc_info.exception.code, 403)
        body = json.loads(exc_info.exception.read().decode())
        self.assertIn("Cross-origin requests are not allowed", body["error"])

    def test_cross_origin_options_is_rejected(self):
        url = f"http://127.0.0.1:{self.port}/api/save"
        request = urllib.request.Request(
            url,
            method="OPTIONS",
            headers={
                "Origin": "https://evil.example",
            },
        )
        with self.assertRaises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(request)
        self.assertEqual(exc_info.exception.code, 403)
        body = json.loads(exc_info.exception.read().decode())
        self.assertIn("Cross-origin requests are not allowed", body["error"])

if __name__ == "__main__":
    unittest.main()
