import unittest
from unittest.mock import Mock, patch

from src.storefront_image_service import InfraiClient, InfraiError, ProductImage, prepare_for_listing


class ListingImageTest(unittest.TestCase):
    def test_upload_then_compress_marks_image_ready(self):
        client = Mock()
        client.upload.return_value = {"id": "uploaded-1"}
        client.compress.return_value = {"id": "compressed-1"}
        result = prepare_for_listing(ProductImage("shoe.jpg", "base64-data"), client)
        self.assertEqual(result, {"filename": "shoe.jpg", "image_id": "compressed-1", "status": "ready"})
        client.compress.assert_called_once_with("uploaded-1")

    @patch("src.storefront_image_service.request.urlopen")
    def test_non_json_upstream_response_becomes_infrai_error(self, urlopen):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.status = 502
        response.read.return_value = b"Bad Gateway"
        urlopen.return_value = response

        with self.assertRaises(InfraiError) as raised:
            InfraiClient("test-key").upload("base64-data", "shoe.jpg")

        self.assertEqual(raised.exception.code, "INVALID_RESPONSE")
        self.assertEqual(raised.exception.status, 502)


if __name__ == "__main__":
    unittest.main()
