import unittest

from backend.http_admin_assets import AdminAssetNotFoundError, build_admin_asset_response


class HttpAdminAssetsTests(unittest.TestCase):
    def test_build_admin_index_response(self) -> None:
        response = build_admin_asset_response("index.html")

        self.assertEqual(response.content_type, "text/html; charset=utf-8")
        self.assertIn("ssh-todolist-services".encode("utf-8"), response.body)
        self.assertIn(b"list-create-form", response.body)
        self.assertIn(b"todo-create-form", response.body)

    def test_build_admin_js_response(self) -> None:
        response = build_admin_asset_response("admin.js")

        self.assertEqual(response.content_type, "text/javascript; charset=utf-8")
        self.assertIn(b"TOKEN_STORAGE_KEY", response.body)
        self.assertIn(b"handleCreateList", response.body)
        self.assertIn(b"renderListManager", response.body)

    def test_missing_admin_asset_raises_not_found(self) -> None:
        with self.assertRaises(AdminAssetNotFoundError) as ctx:
            build_admin_asset_response("missing-file.txt")

        self.assertEqual(ctx.exception.message, "admin asset not found")


if __name__ == "__main__":
    unittest.main()
