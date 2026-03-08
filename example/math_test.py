"""Simple unit tests — no browser. Run: python -m cstesting example/"""
from cstesting import describe, it, expect


def _suite():
    it("adds numbers", lambda: expect(1 + 1).to_be(2))
    it("compares objects", lambda: expect({"a": 1}).to_equal({"a": 1}))
    it("to_contain in string", lambda: expect("hello").to_contain("ell"))
    it("to_contain in list", lambda: expect([1, 2, 3]).to_contain(2))
    it("to_have_length", lambda: expect([1, 2, 3]).to_have_length(3))


describe("Math", _suite)
