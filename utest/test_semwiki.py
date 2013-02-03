from semwiki.service import SemWikiService, SemWiki, Topic
from semwiki.namespace import SW

from nose.tools import raises
from rdflib import BNode, Graph, Literal, RDFS, URIRef
from rdfrest.exceptions import RdfRestException
from rdfrest.local import unregister_service

ROOT_URI = URIRef("http://localhost:8001/")
NEW_URI = URIRef(ROOT_URI + "New")

def make_service():
    store = Graph().store # hack to get IOMemory store
    return SemWikiService(ROOT_URI, store, True)

class TestSemWiki():
    def setUp(self):
        self.service = make_service()

    def tearDown(self):
        unregister_service(self.service)
        self.service = None
        
    def test_service_root(self):
        assert isinstance(self.service.get(ROOT_URI), SemWiki)

    def test_get_new(self):
        assert isinstance(self.service.get(NEW_URI), Topic)

    @raises(RdfRestException)
    def test_put_incoming(self):
        page = self.service.get(NEW_URI)
        with page.edit() as editable:
            editable.add((ROOT_URI, RDFS.seeAlso, NEW_URI))

    @raises(RdfRestException)
    def test_put_bnode(self):
        page = self.service.get(NEW_URI)
        with page.edit() as editable:
            editable.add((NEW_URI, RDFS.seeAlso, BNode()))

    @raises(RdfRestException)
    def test_two_wikitext(self):
        page = self.service.get(NEW_URI)
        with page.edit() as editable:
            editable.add((NEW_URI, SW.wikitext, Literal("other")))

    def test_put_incoming(self):
        page = self.service.get(NEW_URI)
        with page.edit() as editable:
            editable.add((NEW_URI, RDFS.label, Literal("a label")))

    def test_put_working(self):
        page = self.service.get(NEW_URI)
        with page.edit(clear=True) as editable:
            editable.set((NEW_URI, SW.wikitext, Literal("""
            :name->"John Doe" :age->42 # :not->:parsed
            """)))
        ser = ">>>\n" + page.get_state().serialize(format="n3") + "\n<<<"
        assert len(page.get_state()) == 3, ser
        # should be triples sw:wikitext, :name and :age
