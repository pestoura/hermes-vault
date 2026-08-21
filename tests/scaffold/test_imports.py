def test_harness_importable():
    import pytest  # fixture sanity
    assert pytest.__version__ >= "7.0"
