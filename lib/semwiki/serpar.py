"""
Serializers and Parsers for SemWiki
"""

from rdflib import Graph, Literal, URIRef
from rdfrest.parsers import register_parser, ParseError, wrap_exceptions
from rdfrest.serializers import iter_serializers, register_serializer, \
    SerializeError, _HTML_STYLE, _HTML_SCRIPT, _HTML_FOOTER

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

@register_serializer("text/html", "html", 80, SW.Topic)
@wrap_exceptions(SerializeError)
def serialize_html(graph, resource, _bindings=None):
    """Wiki rendering"""
    uri = resource.uri
    ret = "<h1>"
    crumbs = uri.split("/")
    crumbs[:3] = [ "/".join(crumbs[:3]) ]
    for i in xrange(len(crumbs)-1):
        link = "/".join(crumbs[:i+1]) + "/"
        ret += u'<a href="%s">%s</a>' % (link, crumbs[i] + "/",)
    ret += u'<a href="%s">%s</a></h1>\n' % (uri, crumbs[-1])

    ret += "<div class='formats'>Available formats:\n"
    seen_ext = set()
    for _, _, ext in iter_serializers(SW.Topic):
        if ext is not None  and  ext not in seen_ext:
            ret += u'<a href="%s.%s">%s</a>\n' % (uri, ext, ext)
            seen_ext.add(ext)
    ret += "</div>\n"

    wikitext = graph.value(URIRef(uri), SW.wikitext)
    
    ret += "<pre>\n%s</pre>\n" % wikitext_to_html(wikitext, resource)

    page = u"""<html>
    <head>
    <title>%(uri)s</title>
    <style text="text/css">%(style)s
      pre { font-size: 120%% }
    </style>
    <script text="text/javascript">%(script)s</script>
    </head>
    <body onload="init_page()">
    %(body)s
    %(footer)s
    </body>\n</html>""" % {
        "uri": uri,
        "style": _HTML_STYLE,
        "script": _HTML_SCRIPT,
        "body": ret,
        "footer": _HTML_FOOTER,
    }

    return [page.encode("utf-8")]

