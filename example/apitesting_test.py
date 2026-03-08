"""API testing – Rest-Assured style. Run: python -m cstesting example/apitesting_test.py"""
from cstesting import describe, it, expect, request

BASE = "https://jsonplaceholder.typicode.com"


def _api_suite():
    it("GET – expectStatus, expectJson", lambda: (
        request.get(f"{BASE}/users/1")
        .expect_status(200)
        .expect_json("id", 1)
        .expect_json("name", "Leanne Graham")
    ))

    def get_response():
        res = request.get(f"{BASE}/users/2")
        res.expect_status(200)
        r = res.get_response()
        expect(r.status).to_be(200)
        expect(r.body).to_be_defined()
        expect(r.body.get("email", "")).to_contain("@")

    it("GET – getResponse and expect", get_response)

    it("POST – expectStatus 201", lambda: (
        request.post(f"{BASE}/posts", {"title": "Foo", "body": "Bar", "userId": 1}).expect_status(201)
    ))

    it("verifyStatus GET", lambda: request.verify_status("GET", f"{BASE}/users/1", 200))
    it("verifyStatus DELETE", lambda: request.verify_status("DELETE", f"{BASE}/posts/1", 200))


describe("API testing", _api_suite)
