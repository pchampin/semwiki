from nose.tools import eq_
from rdflib import Graph, URIRef

from semwiki.format import _SEM_MARKUP, wikitext_to_html
from semwiki.service import SemWikiService

_TEST_SEM_MARKUP = {
    ':prop->abc': (":prop", None, "prop", "abc", "abc", None),
    ':prop->"ab c"': (":prop", None, "prop", '"ab c"', None, "ab c"),
    ':prop->:abc': (":prop", None, "prop", ":abc", ":abc", None),
    ':prop-><http://a.com/>': (":prop", None, "prop",
                               "<http://a.com/>", "<http://a.com/>", None),
    ('<http://a.com/>->abc'): ("<http://a.com/>", "http://a.com/", None,
                               "abc", "abc", None),
    ('<http://a.com/>->"ab c"'): ("<http://a.com/>", "http://a.com/", None,
                                  '"ab c"', None, "ab c"),
    ('<http://a.com/>->:abc'): ("<http://a.com/>", "http://a.com/", None,
                                ":abc", ":abc", None),
    ('<http://a.com/>-><http://a.com/>'): ("<http://a.com/>", "http://a.com/",
                                           None, "<http://a.com/>",
                                           "<http://a.com/>", None),
}

def test_sem_markup():
    uri = "http://example.org/prop"

    def check_sem_markup_positive(text):
        groups = _TEST_SEM_MARKUP[text]
        match = _SEM_MARKUP.match(text)
        assert match
        eq_(match.groups(), groups)
    for text in _TEST_SEM_MARKUP:
        yield check_sem_markup_positive, text

    def check_sem_markup_negative(text):
        match = _SEM_MARKUP.match(text)
        assert not match
    for text in ["abc", ":prop->", "<http://a.com/>->"]:
        yield check_sem_markup_negative, text
    

_TEST_WIKITEXT_TO_HTML = {
    'line1 # comment': "line1 ",
    'line1\nline2': "line1\nline2",
    'line1\n#not a comment': "line1\n#not a comment",
    'line1\n # no line \nline2': "line1\nline2",
    'I said *hello world*.': "I said <em>hello world</em>.",
    ':foo': "<a href='http://localhost/foo'>foo</a>",
    '<http://a.com/>': "&lt;<a href='http://a.com/'>http://a.com/</a>&gt;",
    '<http://a.com/>': "&lt;<a href='http://a.com/'>http://a.com/</a>&gt;",
    '<http://a.com/#f>': "&lt;<a href='http://a.com/#f'>http://a.com/#f</a>&gt;",
    ':foo->42': "42<a href='http://localhost/foo'>*</a>",
    ':foo->"a b"': "a b<a href='http://localhost/foo'>*</a>",
    ':foo->:bar': ("<a href='http://localhost/bar'>bar</a>"
                   "<a href='http://localhost/foo'>*</a>"),
    '<http://a.com/>->42': "42<a href='http://a.com/'>*</a>",
    '<http://a.com/>->"a b"': "a b<a href='http://a.com/'>*</a>",
    '<http://a.com/>->:bar': ("<a href='http://localhost/bar'>bar</a>"
                              "<a href='http://a.com/'>*</a>"),
    '---': "---",
    '----': "<hr>",
    '--------': '<hr>',
    '----# comment': '<hr>',
    ' ----': ' ----',
}

def test_wikitext_to_html():
    store = Graph().store
    service = SemWikiService("http://localhost/", store, True)
    topic = service.get(URIRef("http://localhost/Home"))

    def check_wikitext_to_html(text):
        expected = _TEST_WIKITEXT_TO_HTML[text]
        eq_(wikitext_to_html(text, topic), expected)
    for text in _TEST_WIKITEXT_TO_HTML:
        yield check_wikitext_to_html, text
        
