"""计算引擎单元测试。"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.compute import (
    content_hash, hash_dedup, text_similarity,
    rate_limit_check, batch_partition, retry_calculator,
)

class TestContentHash:
    def test_content_hash_str(self):
        h = content_hash("hello world")
        assert len(h) == 64
        assert h == content_hash("hello world")

    def test_content_hash_bytes(self):
        h = content_hash(b"hello")
        assert len(h) == 64

    def test_content_hash_md5(self):
        h = content_hash("test", "md5")
        assert len(h) == 32

class TestHashDedup:
    def test_no_duplicates(self):
        items = [
            {"id": 1, "name": "a"},
            {"id": 2, "name": "b"},
        ]
        result, removed = hash_dedup(items, ["name"])
        assert len(result) == 2
        assert removed == 0

    def test_with_duplicates(self):
        items = [
            {"id": 1, "name": "a"},
            {"id": 2, "name": "a"},
            {"id": 3, "name": "b"},
        ]
        result, removed = hash_dedup(items, ["name"])
        assert len(result) == 2
        assert removed == 1

    def test_empty_list(self):
        result, removed = hash_dedup([], ["name"])
        assert result == []
        assert removed == 0

class TestTextSimilarity:
    def test_identical(self):
        assert text_similarity("hello", "hello") == 1.0

    def test_completely_different(self):
        assert text_similarity("aaa", "bbb") < 0.5

    def test_empty_strings(self):
        assert text_similarity("", "") == 1.0
        assert text_similarity("a", "") == 0.0

class TestRateLimitCheck:
    def test_pass(self):
        passed, wait = rate_limit_check(50, 60, 10)
        assert passed is True
        assert wait == 0.0

    def test_fail(self):
        passed, wait = rate_limit_check(1000, 60, 10)
        assert passed is False
        assert wait > 0

    def test_zero_window(self):
        passed, wait = rate_limit_check(100, 0, 10)
        assert passed is True

class TestBatchPartition:
    def test_exact_division(self):
        parts = batch_partition(list(range(10)), 5)
        assert len(parts) == 2
        assert len(parts[0]) == 5

    def test_uneven(self):
        parts = batch_partition(list(range(10)), 3)
        assert len(parts) == 4
        assert len(parts[0]) == 3

    def test_min_batches(self):
        parts = batch_partition([1, 2], 10, min_batches=4)
        assert len(parts) >= 4

    def test_empty(self):
        assert batch_partition([], 5) == []

class TestRetryCalculator:
    def test_first_attempt(self):
        d = retry_calculator(1, base_delay=1.0)
        assert 0.5 <= d <= 1.0

    def test_third_attempt(self):
        d = retry_calculator(3, base_delay=1.0)
        assert 2.0 <= d <= 4.0

    def test_max_delay(self):
        d = retry_calculator(100, base_delay=1.0, max_delay=60)
        assert d <= 60.0

    def test_no_jitter(self):
        d = retry_calculator(2, base_delay=2.0, jitter=False)
        assert d == 4.0