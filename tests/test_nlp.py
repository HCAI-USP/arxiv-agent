from arxiv_agent.nlp import clean_text, tokenize


def test_clean_text_basic():
    s = "This  is a\r\n\r\ntest\xa0string."
    out = clean_text(s)
    assert "\r" not in out
    assert "\xa0" not in out
    assert "test string" in out


def test_tokenize():
    s = "Hello, world! 123"
    toks = tokenize(s)
    assert "Hello" in toks
    assert "world" in toks
    assert "123" in toks
