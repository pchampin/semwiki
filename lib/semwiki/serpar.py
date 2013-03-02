"""
Serializers and Parsers for SemWiki
"""

from rdflib import Graph, Literal, RDF, URIRef
from rdfrest.parsers import register_parser, ParseError, wrap_exceptions
from rdfrest.serializers import iter_serializers, register_serializer, \
    SerializeError
from rdfrest.serializers_html import serialize_htmlized_turtle, \
    generate_ajax_client_js, generate_crumbs, generate_formats

from .format import wikitext_to_html
from .namespace import SW

## Wikitext

@register_serializer("text/plain", "txt", 90, SW.Topic)
@wrap_exceptions(SerializeError)
def serialize_wikitext(graph, resource, bindings=None):
    """I serialize a SemWiki Topic in plain text.
    """
    # 'binding' not used #pylint: disable=W0613
    wikitext = graph.value(resource.uri, SW.wikitext)
    if wikitext is None:
        wikitext = ""
    return [unicode(wikitext).encode("utf-8")]

@register_parser("text/plain", 90)
@wrap_exceptions(ParseError)
def parse_wikitext(content, base_uri=None, encoding="utf-8", graph=None):
    """I parse a SemWiki Topic using the wikitext syntax.
    """
    topic_uri = URIRef(base_uri)
    if graph is None:
        graph = Graph
    graph.add((topic_uri, SW.wikitext, Literal(content.decode(encoding))))
    return graph


## HTML

def generate_semwiki_js(graph, resource, bindings, ctypes, _cache=[]):
    """I patch default JS to make text/plain the default mediatype.
    """
    if not _cache:
        _cache.append(
            generate_ajax_client_js(graph, resource, bindings, ctypes)
            .replace('.value = "text/turtle";', '.value = "text/plain";')
            )
    ret = _cache[0]
    return ret

def generate_header(graph, resource, bindings, ctypes):
    """
    I generate a header with breadcrumbs and format list.
    """
    return ("<h1>"
            + generate_crumbs(graph, resource, bindings, ctypes)
            + "</h1>\n"
            + generate_formats(graph, resource, bindings, ctypes)
            )

def render_wikitext(graph, resource, bindings, ctypes):
    """I render the wikitext of resource."""
    wikitext = graph.value(URIRef(resource.uri), SW.wikitext)    
    return "<pre>\n%s</pre>\n" % wikitext_to_html(wikitext, resource)



@register_serializer("text/html", "html", 80, SW.Topic)
@wrap_exceptions(SerializeError)
def serialize_html(graph, resource, bindings=None):
    """Wiki rendering"""
    ctypes = {}
    rdf_types = list(graph.objects(resource.uri, RDF.type)) + [None]
    for typ in rdf_types:
        for _, ctype, ext in iter_serializers(typ):
            if ext is not None  and  ctype not in ctypes:
                ctypes[ctype] = ext
    return serialize_htmlized_turtle(graph, resource, bindings or {}, ctypes,
                                     generate_script=generate_semwiki_js,
                                     generate_header=generate_header,
                                     generate_body=render_wikitext,
                                     )
