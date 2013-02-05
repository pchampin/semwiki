"""
This is a standalone version of an HTTP-based SemWiki.
"""
import logging
from optparse import OptionParser, OptionGroup
from os.path import exists
from rdflib import plugin as rdflib_plugin
from rdflib.store import Store
from rdfrest.http_server import HttpFrontend
from rdfrest.serializers import bind_prefix, get_prefix_bindings
from socket import getaddrinfo, AF_INET6, AF_INET, SOCK_STREAM
from wsgiref.simple_server import WSGIServer, make_server

from .namespace import SW
from .service import SemWikiService

OPTIONS = None
LOG = logging.getLogger("semwiki")

def main():
    """I launch SemWiki as a standalone HTTP server.
    """
    global OPTIONS # global statement #pylint: disable=W0603
    OPTIONS = parse_options()

    log_level = getattr(logging, OPTIONS.log_level.upper())
    logging.basicConfig(level=log_level) # configure logging

    for plugin_name in OPTIONS.plugin or ():
        try:
            plugin = __import__(plugin_name, fromlist="start_plugin")
        except ImportError:
            plugin = __import__("semwiki.plugins." + plugin_name,
                                fromlist="start_plugin")
        plugin.start_plugin()
    uri = "http://%(host_name)s:%(port)s%(base_path)s/" % OPTIONS.__dict__

    repository = OPTIONS.repository
    if repository is None:
        create = True
        repository = ":IOMemory:"
    elif repository[0] != ":":
        create = not exists(repository)
        repository = ":Sleepycat:%s" % repository
    _, store_type, config_str = repository.split(":", 2)
    store = rdflib_plugin.get(store_type, Store)(config_str)
    sw_service = SemWikiService(uri, store, create)

    wsgifront_options = {}
    if OPTIONS.no_cache:
        wsgifront_options["cache_control"] = (lambda x: None)
    application = HttpFrontend(sw_service, **wsgifront_options)
    if OPTIONS.flash_allow:
        application = FlashAllower(application)

    for nsprefix in OPTIONS.ns_prefix or ():
        prefix, uri = nsprefix.split(1)
        bind_prefix(prefix, uri)
    prefix_bindings = get_prefix_bindings()
    for prefix in ["", "sw", "semwiki", "semwikins"]:
        if prefix not in prefix_bindings:
            bind_prefix(prefix, SW)
            break


    httpd = make_server(OPTIONS.host_name, OPTIONS.port, application,
                        MyWSGIServer)
    LOG.info("SemWiki server at %s" % uri)
    requests = OPTIONS.requests
    if requests == -1:
        httpd.serve_forever()
    else:
        while requests:
            httpd.handle_request()
            requests -= 1


def parse_options():
    """I parse sys.argv for the main.
    """
    opt = OptionParser(description="HTTP-based Kernel for Trace-Based Systems")
    opt.add_option("-H", "--host-name", default="localhost")
    opt.add_option("-p", "--port", default=8001, type=int)
    opt.add_option("-b", "--base-path", default="")
    opt.add_option("-r", "--repository",
                  help="the filename/identifier of the RDF database (default: "
                       "in memory)")
    opt.add_option("-n", "--ns-prefix", action="append",
                  help="a namespace prefix declaration as 'prefix:uri'")
    opt.add_option("-P", "--plugin", action="append",
                  help="loads the given plugin")

    ogr = OptionGroup(opt, "Advanced options")
    ogr.add_option("-4", "--ipv4", action="store_true", default=False,
                   help="Force IPv4")
    ogr.add_option("-B", "--max-bytes",
                   help="sets the maximum number of bytes of payloads"
                   "(no limit if unset)")
    ogr.add_option("-N", "--no-cache", default=0, type=int,
                   help="prevent SemWiki to send cache-control directives")
    ogr.add_option("-F", "--flash-allow", action="store_true",
                   help="serve a policy file allowing Flash applets to connect")
    ogr.add_option("-T", "--max-triples",
                   help="sets the maximum number of bytes of payloads"
                   "(no limit if unset)")
    opt.add_option_group(ogr)

    ogr = OptionGroup(opt, "Debug options")
    ogr.add_option("-l", "--log-level", default="info",
                   choices=["debug", "info", "warning", "error", "critical"],
                   help="serve only the given number of requests")
    ogr.add_option("-R", "--requests", type=int, default=-1,
                   help="serve only the given number of requests")
    ogr.add_option("-1", "--once", action="callback", callback=number_callback,
                   help="serve only one query (equivalent to -R1)")
    ogr.add_option("-2", action="callback", callback=number_callback,
                   help="serve only one query (equivalent to -R2)")
    opt.add_option_group(ogr)

    options, args = opt.parse_args()
    if args:
        opt.error("spurious arguments")
    return options
    

def number_callback(_option, opt, _value, parser):
    """I manage options -R, -1 and -2"""
    val = int(opt[1:])
    parser.values.requests = val


# We define MyWSGIServer here, so that it can access OPTIONS
class MyWSGIServer(WSGIServer):
    """
    I override WSGIServer to make it possibly IPV6-able.
    """
    def __init__(self, (host, port), handler_class):
        ipv = self.address_family = AF_INET
        if OPTIONS.ipv4:
            info = getaddrinfo(host, port, AF_INET, SOCK_STREAM)
        else:
            info = getaddrinfo(host, port, 0, SOCK_STREAM)
            # when IPV6 is available, prefer it to IPV4
            if [ i for i in info if i[0] == AF_INET6 ]:
                ipv = self.address_family =  AF_INET6
        LOG.info("Using IPV%s" % {AF_INET: 4, AF_INET6: 6}[ipv])
        WSGIServer.__init__(self, (host, port), handler_class)

class NoCache(object):
    """
    A strawman cache doing no real caching, used for debugging.
    """
    # too few public methods #pylint: disable=R0903
    @staticmethod
    def get(_key):
        "Always return None"
        return None
    def __setitem__(self, key, name):
        "Do not really store the item."
        pass

class FlashAllower(object):
    """
    I wrap a WSGI application in order to make it accessible to Flash applets.

    This is done by serving /crossdomain.xml .
    """
    #pylint: disable-msg=R0903
    #    too few public methods

    def __init__(self, app, *domains):
        """
        * app: the wrapped WSGI application
        * domains: a list of allowed domains (if empty, '*' is assumed)
        """
        if not domains:
            domains = ["*"]
        allow = [ '<allow-access-from domain="%s"/>' % i for i in domains ]
        self.xml = xml = (
           '<?xml version="1.0"?>\n'
           '<!DOCTYPE cross-domain-policy SYSTEM '
           '"http://www.macromedia.com/xml/dtds/cross-domain-policy.dtd">\n'
           '<cross-domain-policy>\n%s\n</cross-domain-policy>\n'
        ) % "\n".join(allow)
        self.size = str(len(xml))
        self.app = app

    def __call__(self, env, start_response):
        if env["PATH_INFO"] == "/crossdomain.xml":
            start_response("200 OK", [
              ("content-type", "application/xml"),
              ("content-size", self.size),
            ])
            return [self.xml]
        else:
            return self.app(env, start_response)
