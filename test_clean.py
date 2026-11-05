from logclean import clean


def test_timestamps_removed():
    out = clean("2026-11-03T23:37:53.5962690Z pytest failed")
    assert "2026" not in out
    assert "pytest failed" in out


def test_numbers_and_hashes_removed():
    out = clean("commit 9fceb02d0ae598e95dc970b74767f19372d61af8 took 12.5 seconds")
    assert "9fceb02" not in out
    assert "12" not in out


def test_noise_lines_dropped():
    out = clean("Using cached numpy-1.0.whl\nAssertionError: boom")
    assert "cached" not in out
    assert "assertionerror" in out


def test_cleaning_is_lowercase():
    assert clean("ERROR Failed") == "error failed"
