"""I implement the wiki format.
"""
from rdflib import Graph, Literal, URIRef, XSD
from rdfrest.exceptions import InvalidDataError
from re import compile as regex, search, sub
from StringIO import StringIO

def make_initial_value(topic):
    """Generate the initial wikitext for `topic`.
    """
    short_name = topic.uri[len(topic.service.root_uri):]
    return """
    This is topic :%s .
    *Edit* it to create it.
    """ % short_name

def wikitext_to_triples(topic, wikitext, into=None):
    """I return a graph corresponding to `wikitext`.
    """
    if into is None:
        into = Graph()

    pieces = []
    for line in wikitext.split("\n"):
        line = _COMMENT.sub("", line)
        for groups in _SEM_MARKUP.findall(line):
            pieces.append("%s %s" % (groups[0], groups[3]))

    if pieces:
        topic_uri = topic.uri
        wiki_uri = topic.service.root_uri
        header = "@prefix : <%s> . <%s>\n" % (wiki_uri, topic_uri)
        turtle = header + ";\n".join(pieces) + "\n."
        into.parse(StringIO(turtle), format="n3")

    return into

def add_triples(topic, wikitext, triples):
    """I return a version of `wikitext` amended with `triples`.
    """
    wiki_uri = topic.service.root_uri
    pieces = [wikitext]
    if not "----# auto" in wikitext:
        pieces.append("\n----# auto\n")
    for _, pred, obj in triples:
        pieces.append("%s->%s (auto)\n" % (
            to_n3(pred, wiki_uri),
            to_n3(obj, wiki_uri),
            ))
    return "".join(pieces)

def ban_triples(topic, wikitext, triples):
    """I return a version of `wikitext` where `triples` are removed and banned.
    """
    # unused argument (since itis not implemented yet) #pylint: disable=W0613
    wiki_uri = topic.service.root_uri
    for _, pred, obj in triples:
        pred = to_n3(pred, wiki_uri)
        obj = to_n3(obj, wiki_uri)
        sem_markup = r'%s->(%s)' % (pred, obj)
        match = search(r'%s \(auto\)\n' % sem_markup, wikitext)
        if match:
            ifrom, ito = match.span()
            wikitext = wikitext[:ifrom] + wikitext[ito:]
        wikitext = sub(sem_markup, r'\1', wikitext)
        wikitext += "\n# banned: %s->%s" % (pred, obj)
    return wikitext

def to_n3(node, wiki_uri):
    """Convert `node` to a nice serialization for the wikitext.
    """
    if isinstance(node, URIRef):
        if node.startswith(wiki_uri):
            return ":%s" % (node[len(wiki_uri):])
        else:
            return "<%s>" % node
    elif isinstance(node, Literal):
        if node.datatype in (XSD.integer, XSD.decimal, XSD.boolean):
            return "%s" % node
        else:
            return node.n3()
    else:
        raise InvalidDataError("Can not handle blank nodes in SemWiki")

def wikitext_to_html(wikitext, resource):
    """I return the HTML corresponding to `wikitext`.
    """
    root_uri = resource.service.root_uri
    lines = []

    def repl_sem_markup(match):
        """I replace a sem markup"""
        groups = match.groups()
        ret = groups[4] or groups[5]
        if groups[1]:
            link = groups[1]
        else:
            link = "%s%s" % (root_uri, groups[2])
        ret += "<a href='%s'>*</a>" % link
        return ret

    def repl_link(match):
        """I replace a link"""
        groups = match.groups()
        if groups[1]:
            return "&lt;<a href='%s'>%s</a>&gt;" % (groups[1], groups[1])
        else:
            assert groups[2]
            return "<a href='%s%s'>%s</a>" % (root_uri, groups[2], groups[2])

    for line in wikitext.split("\n"):
        if _WHOLE_LINE_COMMENT.match(line):
            continue
        line = _COMMENT.sub("", line)
        line = _SEM_MARKUP.sub(repl_sem_markup, line)
        line = _LINK.sub(repl_link, line)
        line = _EMPH.sub(r"<em>\1</em>", line)
        line = _HR.sub(r"<hr>", line)
        lines.append(line)
    return "\n".join(lines)
    

_COMMENT = regex(r"#\s.*$")
_WHOLE_LINE_COMMENT = regex(r"^\s*%s" % _COMMENT.pattern)
_INT_LINK = r":([A-Za-z][\w/]*)"
_EXT_LINK = r"<([^/][^ >]*)>"
_LINK = regex(r"(%s|%s)" % (_EXT_LINK, _INT_LINK))
_SEM_MARKUP = regex(r'%s->(([^"\s]\S*)|"([^"]+)")' % _LINK.pattern)
_EMPH = regex(r"\*([^\*<]+)\*")
_HR = regex(r"^----+$")
