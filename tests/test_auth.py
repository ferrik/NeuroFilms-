import os
import unittest
from auth import resolve_role_from_api_key, has_required_role

class AuthTests(unittest.TestCase):
    def setUp(self):
        os.environ["CREATOR_API_KEY"] = "creator-key"
        os.environ["MODERATOR_API_KEY"] = "moderator-key"
        os.environ["ADMIN_API_KEY"] = "admin-key"

    def test_resolve_role(self):
        self.assertEqual(resolve_role_from_api_key("creator-key"), "creator")
        self.assertEqual(resolve_role_from_api_key("moderator-key"), "moderator")
        self.assertEqual(resolve_role_from_api_key("admin-key"), "admin")
        self.assertEqual(resolve_role_from_api_key("bad"), "anonymous")

    def test_role_hierarchy(self):
        self.assertTrue(has_required_role("admin", "moderator"))
        self.assertTrue(has_required_role("moderator", "creator"))
        self.assertFalse(has_required_role("creator", "admin"))

if __name__ == "__main__":
    unittest.main()
