import json
import unittest
from http import HTTPStatus
from os.path import dirname, join

# from src import constants
import bucket
import constants


class TestBucket(unittest.TestCase):
    def test_put(self):
        event = self.get_event()
        response = bucket.put_by_bucket(event, {})
        assert response["statusCode"] == 201


    def test_get(self):
        event = self.get_event()
        response = bucket.get_by_bucket(event, {})
        self.assertEqual(response["statusCode"], 200)


    def get_event(self):
        event_json = join(dirname(dirname(__file__)),
                          "samples",
                          "bucket_put.json")

        return json.loads(open(event_json).read())

if __name__ == '__main__':
    unittest.main()
