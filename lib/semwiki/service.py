"""
I contain the definition of the SemWiki service.
"""
from contextlib import contextmanager
from rdflib import BNode, Graph, Literal, RDF, URIRef, XSD
from rdflib.compare import graph_diff, isomorphic
from rdfrest.exceptions import InvalidDataError, InvalidParametersError, \
    MethodNotAllowedError, RdfRestException
from rdfrest.local import ILocalResource, Service, StandaloneResource
from rdfrest.mixins import WithCardinalityMixin, WithReservedNamespacesMixin, \
    WithTypedPropertiesMixin
from rdfrest.utils import Diagnosis

from .format import add_triples, ban_triples, make_initial_value, \
    wikitext_to_triples
from .namespace import SW

class SemWikiService(Service):
    """I specialise Service by returning Topic for every relevant URI.
    """
    # too few public methods (1/2) #pylint: disable=R0903
    def __init__(self, uri, store, create):
        init_service = create and init_semwiki
        Service.__init__(self, uri, store, [SemWiki], init_service)

    def get(self, uri, _rdf_type=None, _no_spawn=False):
        """I return a Topic for all resources 
        """
        ret = super(SemWikiService, self).get(uri, _rdf_type, _no_spawn)
        if ret is None \
                and uri.startswith(self.root_uri) \
                and len(uri) > len(self.root_uri) \
                and uri[len(self.root_uri)] != '@':
            return Topic(uri, self)
        else:
            return ret

def init_semwiki(service):
    """I initiatlize the store of `service`.
    """
    new_graph = Graph()
    new_graph.add((service.root_uri, RDF.type, SW.SemWiki))
    new_graph.add((service.root_uri, SW.home,
                   URIRef(service.root_uri + "Home")))
    SemWiki.create(service, service.root_uri, new_graph)

class SemWiki(StandaloneResource):
    """The root of a SemWiki.
    """
    RDF_MAIN_TYPE = SW.SemWiki

class _TopicBase(ILocalResource):
    """A specific :class:`~.local.ILocalResource` implementation for Topic.

    All topics share the same graph (named by the root of the service).
    It only contains outgoing triples about itself.
    It also contains a special triple sw:wikitext which must be kept consistent
    with the rest of the triples.
    """

    def __init__(self, uri, service):
        # not calling ILocalResource __init__ #pylint: disable=W0231
        self.uri = uri
        self.service = service
        self._graph = Graph(service.store, service.root_uri)
        self._state = Graph(identifier=uri)
        self._fill_state(self._state)

    ######## Specific API  ########

    def get_wikitext(self):
        """Return this topic's wikitext.
        """
        return unicode(self._state.value(self.uri, SW.wikitext))

    def set_wikitext(self, value):
        """Set this topic's wikitext.
        """
        with self.edit() as editable:
            editable.set(self.uri, SW.wikitext, Literal(value))

    wikitext = property(get_wikitext, set_wikitext)

    ######## IResource implementation  ########

    def factory(self, uri, _rdf_type=None, _no_spawn=False):
        """I implement :meth:`.interface.IResource.factory`.

        I simply rely on my service's get method.
        """
        return self.service.get(URIRef(uri), _rdf_type, _no_spawn)

    def get_state(self, parameters=None):
        """I implement `.interface.IResource.get_state`.

        I return the subgraph of the semantic wiki representing this topic.
        """
        self.check_parameters(parameters, "get_state")
        return self._state

    def force_state_refresh(self, parameters=None):
        """I override `.hosted.HostedResource.force_state_refresh`.
        """
        # nothing to do, there is no cache involved
        self.check_parameters(parameters, "force_state_refresh")
        if self._state is not None:
            self._state.remove((None, None, None))
            self._fill_state(self._state)
        return

    @contextmanager
    def edit(self, parameters=None, clear=False, _trust=False):
        """I implement `.interface.IResource.edit`.

        I do not support _trust nor embeded edit contexts (at least for the
        moment).
        """
        # unused arguments #pylint: disable=W0613
        self.check_parameters(parameters, "edit")
        editable = Graph()
        if not clear:
            editable_add = editable.add
            for t in self._state:
                editable_add(t)

        yield editable
        self.complete_new_graph(self.service, self.uri, parameters,
                                editable, self)
        diag = self.check_new_graph(self.service, self.uri, parameters,
                                    editable, self)
        if not diag:
            raise InvalidDataError(unicode(diag))
            
        self._graph.remove((self.uri, None, None))
        graph_add = self._graph.add
        for t in editable:
            graph_add(t)
        self.force_state_refresh()
        
    def post_graph(self, graph, parameters=None,
                   _trust=False, _created=None, _rdf_type=None):
        """I implement :meth:`.interface.IResource.post_graph`.

        Not supported (for the moment?).
        """
        # unused arguments #pylint: disable=W0613
        raise MethodNotAllowedError("POST not supported (yet?)")

    def delete(self, parameters=None, _trust=False):
        """I implement :meth:`.interface.IResource.delete`.

        Not supported (for the moment?).
        """
        # unused arguments #pylint: disable=W0613
        raise MethodNotAllowedError("DELETE not supported (yet?)")


    ######## ILocalResource (and mixins) implementation  ########

    def check_parameters(self, parameters, method):
        """I implement :meth:`ILocalResource.check_parameters`.

        I accepts no parameter (not even an empty query string).
        """
        # self is not used #pylint: disable=R0201
        # argument 'method' is not used #pylint: disable=W0613

        # Do NOT call super method, as this is the base implementation.
        if parameters is not None:
            if not parameters:
                raise InvalidParametersError("Unsupported parameters "
                                             "(empty dict instead of None)")
            else:
                raise InvalidParametersError("Unsupported parameter(s):" +
                                             ", ".join(parameters.keys()))

    @classmethod
    def complete_new_graph(cls, service, uri, parameters, new_graph,
                           resource=None):
        """I implement :meth:`ILocalResource.complete_new_graph`.

        If new_graph contains only a wikitext property, then all corresponding
        triples are generated.

        If new_graph contains other triples and either
        no wikitext *or* the same wikitext as previously,
        then the wikitext is updated to reflect the triples.

        If new_graph contains other triples and a wikitext different from
        the previous one, then the wikitext and the triples *have* to be
        consistent, or a InvalidDataError will be raised.
        """
        assert resource is not None # topics can only be created by PUT
        wikitexts = list(new_graph.objects(uri, SW.wikitext))
        if len(wikitexts) > 1:
            # leave it to WithCardinalityMixin to raise an error
            return

        if len(wikitexts) == 0:
            new_wikitext = None
        else:
            new_wikitext = unicode(wikitexts[0])

        if new_wikitext is not None  and  len(new_graph) == 1:
            # wikitext only: parse other triples from it
            wikitext_to_triples(resource, new_wikitext, into=new_graph)
            return

        if new_wikitext is not None  and  new_wikitext != resource.wikitext:
            # wikitext *and* triples were changed: they must be consistent
            from_text = wikitext_to_triples(resource, new_wikitext)
            from_text.add((uri, SW.wikitext, wikitexts[0]))
            if not isomorphic(from_text, new_graph):
                raise InvalidDataError("wikitext and triples are inconsistent")
            else:
                return

        # new_wikitext is either None or equal to old wikitext,
        # so we focus on the triples of new_graph
        if new_wikitext is None:
            old_wikitext = resource.get_state().value(uri, SW.wikitext)
            new_graph.add((uri, SW.wikitext, old_wikitext))
            new_wikitext = unicode(old_wikitext)
        _, added, removed = graph_diff(new_graph, resource.get_state())
        if added:
            new_wikitext = add_triples(resource, new_wikitext, added)
        if removed:
            new_wikitext = ban_triples(resource, new_wikitext, removed)
        if added or removed:
            new_graph.set((uri, SW.wikitext, Literal(new_wikitext)))
                      
    @classmethod
    def check_new_graph(cls, service, uri, parameters, new_graph,
                        resource=None, added=None, removed=None):
        """I implement :meth:`ILocalResource.check_new_graph`.

        I check what the mixins can not check.
        """
        diag = Diagnosis("check_new_graph")
        for subj, _pred, obj in new_graph:
            if subj != uri:
                diag.append("Wrong subject %s" % subj)
            if isinstance(obj, BNode):
                diag.append("BNode not supported")
        return diag

    @classmethod
    def mint_uri(cls, target, new_graph, created, basename="o", suffix=""):
        """I implement :meth:`rdfrest.local.ILocalResource.mint_uri`.

        I use the skos:prefLabel of the resource to mint a URI, else the
        basename.
        """
        raise RdfRestException("Topic can not be created as bnodes")

    @classmethod
    def create(cls, service, uri, new_graph):
        """I implement :meth:`ILocalResource.create`.

        I store `new_graph` as a new topic.
        """
        raise RdfRestException("Topic must be PUT to be created")

    ######## Private methods ########

    def _fill_state(self, state):
        """I fill the state with relevant triple.

        I also create user-friendly triples if resource does not exist.
        """
        add = state.add
        for t in self._graph.triples((self.uri, None, None)):
            add(t)
        if len(state) == 0:
            add((self.uri, SW.wikitext, Literal(make_initial_value(self))))


class Topic(WithCardinalityMixin, WithReservedNamespacesMixin,
            WithTypedPropertiesMixin, _TopicBase):
    """
    I provide the implementation of :Topic .
    """
    # NB: the only rationale for having this class separate from _TopicBase
    # is that _TopicBase provides the base implementation for
    # ILocalResource, so it must be *after* all mix-in classes in the MRO.

    RDF_MAIN_TYPE = SW.Topic

    RDF_RESERVED_NS =     [ SW ]
    RDF_EDITABLE_OUT =    [ SW.wikitext ]
    RDF_CARDINALITY_OUT = [ (SW.wikitext, 1, 1) ]
    RDF_TYPED_PROP =      [ (SW.wikitext, "literal", XSD.string) ]


# unused import #pylint: disable=W0611
# ensures registration of parsers/serializers 
import semwiki.serpar
