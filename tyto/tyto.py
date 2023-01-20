import os
import logging
from functools import lru_cache

from .endpoint import Ontobee, EBIOntologyLookupService, GraphEndpoint, QueryBackend


LOGGER = logging.getLogger(__name__)
logging.basicConfig(format='[%(levelname)s] %(filename)s %(lineno)d: %(message)s')


class Ontology():

    """The Ontology class provides an abstraction layer for accessing ontologies, and a 
    back-end query dispatcher for interfacing with RESTful services, SPARQL endpoints,
    or local triple stores.
    
    :param path: A path to a local ontology file, defaults to None
    :type path: str, optional
    :param endpoints: A list of zero or more Endpoint objects that provide a query interface to an ontology resource, defaults to None
    :type endpoints: list, optional
    :param uri: The URI of the ontology
    :type str
    """

    def __init__(self, path=None, endpoints=None, uri=None):
        if not path and not endpoints:
            raise Exception('A sparql endpoint or a local path to an ontology must be specified')
        self.graph = None
        self.endpoints = None
        self.uri = uri
        if endpoints:
            if not type(endpoints) is list or not all([issubclass(type(e), QueryBackend) for e in endpoints]):
                raise TypeError('The endpoints argument requires a list of Endpoints')
            self.endpoints = endpoints
        if path:
            if not type(path) is str:
                raise TypeError('Invalid path specified')
            self.graph = GraphEndpoint(path)

    def __getattr__(self, name):
        """Enables use of ontology terms as dynamic attributes, e.g., SO.promoter 
        """
        if name in self.__getattribute__('__dict__'):
            return self.__getattribute__(name)
        else:
            return self.__getattribute__('get_uri_by_term')(name)

    def _handler(self, method_name, exception, *args):
        """Dispatches queries through Endpoints
        """
        response = None

        # If the ontology graph has already been loaded locally, query that rather
        # than querying over the network
        if self.graph and self.graph.is_loaded():
            method = getattr(self.graph, method_name)
            response = method(self, *args)
            if response is not None:
                return response
            #try:
            #    response = method(self, *args)
            #    if response is not None:
            #        return response
            #except Exception as x:
            #    LOGGER.error(x)

        # Try endpoints
        if self.endpoints:
            for e in self.endpoints:
                method = getattr(e, method_name)
                response = method(self, *args)
                if response is not None:
                    return response
                #try:
                #    response = method(self, *args)
                #    if response is not None:
                #        return response
                #except Exception as x:
                #    LOGGER.error(x)
                #    raise

        # If the connection fails or nothing found, fall back and load the ontology locally
        if self.graph and not self.graph.is_loaded():
            self.graph.load()
            method = getattr(self.graph, method_name)
            try:
                response = method(self, *args)
                if response is not None:
                    return response
            except Exception as x:
                LOGGER.error(x)

        if exception:
            raise exception
        return None

    def get_term_by_uri(self, uri):
        """Provides the ontology term (rdfs:label) associated with the given URI.

        :param uri: A uniform resource identifier corresponding to an ontology term
        :type uri: str

        :return: A human-readable term or label that corresponds to the given identifier
        :rtype: string
    """
        sanitized_uri = self._sanitize_uri(uri)
        exception = LookupError(f'No matching term found for {uri}')
        term = self._handler('get_term_by_uri', exception, sanitized_uri)
        return Term(self._reverse_sanitize_term(term), sanitized_uri, self)

    def get_uri_by_term(self, term):
        """Provides the URI associated with the given ontology term (rdfs:label).  The __getattr__ and __getitem__ methods delegate to this method. 

        :param term: an ontology term
        :type term: str
    
        :return: A human-readable term or label that corresponds to the given identifier
        :rtype: URI
        """
        sanitized_term = self._sanitize_term(term)
        exception = LookupError(f'{term} is not a valid ontology term')
        uri = self._handler('get_uri_by_term', exception, sanitized_term)
        return URI(self._reverse_sanitize_uri(uri), self)

    def _sanitize_uri(self, uri):
        """Some Ontology instances may override this method to translate a URI
        from purl to identifiers.org namespaces
        """
        return uri

    def _reverse_sanitize_uri(self, uri):
        """Some Ontology instances may override this method to reverse-translate a URI
        from identifiers.org back into purl namespace
        """
        return uri

    def _sanitize_term(self, term):
        """Some Ontology instances may override this method in order to convert a Pythonic representation of a label into a more human-readable representation, such as replacing underscores with spaces
        """
        return term.replace('_', ' ')

    def _reverse_sanitize_term(self, term):
        """Some Ontology instances may override this method to undo the conversion done by _sanitize_term and return a Pythonic label from free text label 
        """
        return term

    def __getitem__(self, key):
        """Enables use of an ontology term as a subscript. This method is a useful alternative to dynamic attributes in case a term contains special characters

        :return: A uniform resource identifier associated with the provided term
        :rtype: URI
        """
        return self.get_uri_by_term(key)

class URI(str):

    """The URI class wraps the Python string primitive type, enabling the use of inference methods on the represented uniform resource identifier

    :param value: A string value representing a uniform resource identifier
    :type value: str
    :param ontology: links a term to a particular Ontology instance
    :type ontology: Ontology
    """

    def __new__(cls, value: str, ontology: Ontology):
        term = str.__new__(cls, value)
        term.ontology = ontology
        return term

    def is_child_of(self, parent_uri: str):
        """Determine whether this URI is an immediate subclass or subtype of the  argument URI
    
        :param parent_uri: URI corresponding to the putative parent term
        :type parent_uri: str
    
        :rtype: bool
        """
        child_uri = self.ontology._sanitize_uri(self)
        parent_uri = self.ontology._sanitize_uri(parent_uri)
        return self.ontology._handler('is_child_of', None, child_uri, parent_uri)

    def is_parent_of(self, child_uri: str):
        """Determine whether this URI is an immediate superclass or supertype of the argument URI
    
        :param parent_uri: URI corresponding to the putative parent term
        :type parent_uri: str
    
        :rtype: bool
        """
        parent_uri = self.ontology._sanitize_uri(self)
        child_uri = self.ontology._sanitize_uri(child_uri)
        return self.ontology._handler('is_parent_of', None, parent_uri, child_uri)

    def is_descendant_of(self, ancestor_uri: str):
        """Determine whether this URI is a taxonomic subcategory of the argument URI
    
        :param ancestor_uri: URI corresponding to the putative ancestor
        :type ancestor_uri: str
    
        :rtype: bool
        """

        descendant_uri = self.ontology._sanitize_uri(self)
        ancestor_uri = self.ontology._sanitize_uri(ancestor_uri)
        return self.ontology._handler('is_descendant_of', None, descendant_uri, ancestor_uri)

    def is_ancestor_of(self, descendant_uri: str):
        """Determine whether this URI is a taxonomic superclass or supertype of the argument URI
    
        :param descendant_uri: URI corresponding to the putative descendant
        :type descendant_uri: str
    
        :rtype: bool
        """

        ancestor_uri = self.ontology._sanitize_uri(self)
        descendant_uri = self.ontology._sanitize_uri(descendant_uri)
        return self.ontology._handler('is_ancestor_of', None, ancestor_uri, descendant_uri)

    def is_subtype_of(self, supertype: str):
        """Alias of is_descendant_of. Determines whether this URI is a derivative subclass or subtype of the argument URI
    
        :param supertype: URI corresponding to the putative supertype
        :type supertype: str
    
        :rtype: bool
        """

        return self.is_descendant_of(supertype)

    def is_supertype_of(self, subtype: str):
        """Alias of is_ancestor_of. Determines whether this URI is a superclass or supertype of the argument URI
    
        :param subtype: URI corresponding to the putative subtype
        :type subtype: str
    
        :rtype: bool
        """
        return self.is_ancestor_of(subtype)
  
    def is_a(self, term: "URI"):
        if term == self:
            return True
        if self.is_subtype_of(term):
            return True
        return False

    def is_instance(self):
        return self.ontology._handler('is_instance', None, self)

    def get_instances(self):
        return self.ontology._handler('get_instances', None, self)

    def get_parents(self):
        return self.ontology._handler('get_parents', None, self)

    def get_children(self):
        return self.ontology._handler('get_children', None, self)

    def get_ancestors(self):
        return self.ontology._handler('get_ancestors', None, self)

    def get_descendants(self):
        return self.ontology._handler('get_descendants', None, self)


class Term(str):

    def __new__(cls, value, uri, ontology):
        term = super().__new__(cls, value)
        term.uri = uri
        term.ontology = ontology
        return term

    def is_instance(self):
        return self.ontology._handler('is_instance', None, self.uri)


# Utility functions
def installation_path(relative_path):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)),
                        relative_path)


def multi_replace(target_uri, old_namespaces, new_namespace):
    for ns in old_namespaces:
        if ns in target_uri:
            return target_uri.replace(ns, new_namespace)
    return target_uri


def configure_cache_size(maxsize=1000):
    """Set the size of the in-memory cache in order to optimize performance and frequency of queries over the network

    :param maxsize: The maximum number of cached query results
    :type maxsize: int
    """
    if not '__wrapped__' in Ontology.get_term_by_uri.__dict__:
        # Initialize cache
        Ontology.get_term_by_uri = lru_cache(maxsize=maxsize)(Ontology.get_term_by_uri)
        Ontology.get_uri_by_term = lru_cache(maxsize=maxsize)(Ontology.get_uri_by_term)
    else:
        # Reset cache-size if it was previously set
        Ontology.get_term_by_uri = lru_cache(maxsize=maxsize)(Ontology.get_term_by_uri.__wrapped__)
        Ontology.get_uri_by_term = lru_cache(maxsize=maxsize)(Ontology.get_uri_by_term.__wrapped__)

# Initialize cache
configure_cache_size()
