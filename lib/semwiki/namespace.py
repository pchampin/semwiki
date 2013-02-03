"""
I contain useful namespace objects, as well as the definition of the SemWeb
vocabulary.

This module can be run as a program to generate the description:

* with no argument, it will output the original version (Turtle, with a
  reader-friendly layout);
* with an rdflib format as its argument, it will first convert it to that
  format, but the result might not be as reader-friendly.
"""

from StringIO import StringIO
from rdflib import Graph, plugin as rdflib_plugin, RDF, URIRef
from rdflib.store import Store
from rdflib.namespace import ClosedNamespace
from rdfrest.local import StandaloneResource, Service

SW_NS_URI = "http://liris.cnrs.fr/silex/2012/semwiki"
SW_NS_URIREF = URIRef(SW_NS_URI)

SW_NS_TTL = """
@base <%s> .
@prefix : <#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

<>
    a owl:Ontology;
    rdfs:label "SemWiki vocabulary v0.1"@en, "Vocabulaire SemWiki v0.1"@fr;
    owl:versionInfo "0.1";
    # TODO SOON more metadata about vocabulary?
.

:home a owl:ObjectProperty .
:wikitext a owl:DatatypeProperty .

:SemWiki a owl:Class .
:Topic a owl:Class .

# TODO define it

""" % SW_NS_URI

SW_NS_GRAPH = Graph("IOMemory", identifier=SW_NS_URIREF)
SW_NS_GRAPH.load(StringIO(SW_NS_TTL), SW_NS_URIREF, "n3")

SW_IDENTIFIERS = set()

for subject, _, _ in SW_NS_GRAPH.triples((None, RDF.type, None)):
    if subject.startswith(SW_NS_URI):
        splitted = subject.split("#", 1)
        if len(splitted) > 1:
            SW_IDENTIFIERS.add(splitted[1])

SW = ClosedNamespace(SW_NS_URI + "#", 
                       SW_IDENTIFIERS,
                       )

class _SemWikiNsResource(StandaloneResource):
    """I am the only resource class of SW_NS_SERVICE.

    SW_NS_SERVICE provides a local copy of the SemWiki namespace.
    """
    # too few public methods (1/2) #pylint: disable=R0903
    RDF_MAIN_TYPE = URIRef("http://www.w3.org/2002/07/owl#Ontology")

    @classmethod
    def init_service(cls, service):
        """I populate a service the SemWiki namespace at its root.
        """
        cls.create(service, SW_NS_URIREF, SW_NS_GRAPH)

SW_NS_SERVICE = Service(SW_NS_URI, rdflib_plugin.get("IOMemory", Store)(""),
                        classes=[_SemWikiNsResource],
                        init_with=_SemWikiNsResource.init_service)

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        print SW_NS_TTL
    else:
        SW_NS_GRAPH.serialize(sys.stdout, sys.argv[1])
