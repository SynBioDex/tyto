import rdflib
from SPARQLWrapper import SPARQLWrapper, JSON
import urllib
import os
import posixpath

class Ontology():

    def __init__(self, path=None, endpoint=None, uri=None):
        if not path and not endpoint:
            raise Exception('A sparql endpoint or a local path to an ontology must be specified')
        self.path = path
        self.graph = rdflib.Graph()
        self.uri = uri
        self.endpoint = None
        if endpoint:
            self.endpoint = SPARQLWrapper(endpoint)
            self.endpoint.setReturnFormat(JSON)

    def _query(self, sparql, error_msg):
        '''
        This is a generalized back-end for querying ontologies. By default it performs
        SPARQL queries through a network endpoint, because loading an ontology from a
        local graph takes a while and uses up memory.  However, once a graph is loaded
        locally, subsequent queries will be performed directly on the graph.
        '''
        response = []
        if len(self.graph):
            # If the ontology graph has been loaded locally, query that rather
            # than querying over the network
            sparql_final = sparql.format(from_clause='')  # Because only one ontology per file, delete the from clause
            response = self.graph.query(sparql_final)
            response = Ontology._convert_rdflib_response(response)

        if self.endpoint:
            # print('Testing endpoint')
            # If no ontology graph is located, query the network endpoint
            # The general naming pattern for an Ontobee graph URI is to transform a PURL 
            # http://purl.obolibrary.org/obo/$foo.owl (note foo must be all lowercase 
            # by OBO conventions) to http://purl.obolibrary.org/obo/merged/uppercase($foo).
            from_clause = ''
            if self.uri:
                ontology = self.uri
                if 'http://purl.obolibrary.org/obo/' in self.uri:
                    ontology = ontology.replace('http://purl.obolibrary.org/obo/', '')
                    ontology = ontology.replace('.owl', '')
                    ontology = ontology.upper()
                    ontology = 'http://purl.obolibrary.org/obo/merged/' + ontology
                from_clause = f'FROM <{ontology}>'
            sparql_final = sparql.format(from_clause=from_clause)
            self.endpoint.setQuery(sparql_final)
            try:
                response = self.endpoint.query()
            except Exception as e:
                print(e)
            response = Ontology._convert_ontobee_response(response)

        else:
            #print('No endpoint specified. Querying local cache.')
            pass

        # If the connection fails or nothing found, load the ontology locally
        if not len(response) and self.path:
            # print('Testing local cache')
            try:
                self.graph.parse(self.path)
                sparql_final = sparql.format(from_clause='')  # Because only one ontology per file, delete the from clause
                response = self.graph.query(sparql_final)
                response = Ontology._convert_rdflib_response(response)
            except Exception as e:
                print(e)
        else:
            #print('No path to local cache specified.')
            pass

        if not len(response):
            raise LookupError(error_msg)
        return response

    def _convert_ontobee_response(response):
        '''
        Ontobee SPARQL interface returns JSON. This extracts and flattens the queried
        variables into a list
        '''
        converted_response = []
        if response:
            response = response.convert()  # Convert http response to JSON
            for var, binding in zip(response['head']['vars'],
                                    response['results']['bindings']):
                converted_response.append(binding[var]['value'])
        return converted_response

    def _convert_rdflib_response(response):
        '''
        Extracts and flattens queried variables from rdflib response into a list
        '''
        return [str(row[0]) for row in response]

    def get_term_by_uri(self, uri):
        '''
        Get the ontology term (e.g., "promoter") corresponding to the given URI
        :param uri: The URI for the term
        :return: str
        '''
        uri = self._from_user(uri)
        query = '''
            SELECT distinct ?label
            WHERE
            {{{{
                <{uri}> rdfs:label ?label .
            }}}}
            '''.format(uri=uri)
        error_msg = '{} not found'.format(uri)
        response = self._query(query, error_msg)
        return response[0]

    def get_uri_by_term(self, term):
        '''
        Get the URI assigned to an ontology term (e.g., "promoter")
        :param term: The ontology term
        :return: str
        '''
        
        # Queries to the sequence ontology require the xsd:string datatype
        # whereas queries to the systems biology ontology do not, hence the
        # UNION in the query. Additionally, terms in SBO have spaces rather
        # than underscores. This creates a problem when looking up terms by
        # an attribute, e.g., SBO.systems_biology_representation
        sanitized_term=self._sanitize_term(term)

        query = '''
            SELECT distinct ?uri
            {{from_clause}}
            WHERE
            {{{{
                {{{{?uri rdfs:label "{sanitized_term}"}}}} UNION
                {{{{?uri rdfs:label "{sanitized_term}"^^xsd:string}}}} UNION
                {{{{?uri rdfs:label "{sanitized_term}"@en}}}} UNION
                {{{{?uri rdfs:label "{sanitized_term}"@nl}}}}
            }}}}
            '''.format(sanitized_term=sanitized_term)

        error_msg = '{} not a valid ontology term'.format(term)
        response = self._query(query, error_msg)[0]
        return self._to_user(response)

    def _to_user(self, uri):
        # Some Ontology instances may override this method to translate a URI
        # from purl to identifiers.org namespaces
        return uri

    def _from_user(self, uri):
        # Some Ontology instances may override this method to translate a URI
        # from purl to identifiers.org namespaces
        return uri

    def _sanitize_term(self, term):
        # Some Ontology instances may override this method to perform string
        # manipulation of an ontology terms, for example, replacing spaces
        # or changing camel-case to snake-case
        return term

    def get_ontology(self):
        query = '''
            SELECT distinct ?ontology_uri
            WHERE
              {
                ?ontology_uri a owl:Ontology
              }
            '''
        error_msg = 'Graph not found'
        response = self._query(query, error_msg)
        return response[0]

    def __getattr__(self, name):
        if name in self.__getattribute__('__dict__'):
            return self.__getattribute__(name)
        else:
            return self.__getattribute__('get_uri_by_term')(name)


def installation_path(relative_path):
    return posixpath.join(os.path.dirname(os.path.realpath(__file__)),
                          relative_path)

def multi_replace(target_uri, old_namespaces, new_namespace):
    for ns in old_namespaces:
        if ns in target_uri:
            return target_uri.replace(ns, new_namespace)
    return target_uri

SO = Ontology(path=installation_path('ontologies/so.owl'),
              endpoint='http://sparql.hegroup.org/sparql/',
              uri='http://purl.obolibrary.org/obo/so.owl')
SO._to_user = lambda uri: uri.replace('http://purl.obolibrary.org/obo/SO_',
                                      'https://identifiers.org/SO:')
SO._from_user = lambda uri: multi_replace(uri,
                                          ['https://identifiers.org/SO:',
                                           'http://identifiers.org/so/SO:'],
                                           'http://purl.obolibrary.org/obo/SO_')

SBO = Ontology(path=installation_path('ontologies/SBO_OWL.owl'),
               endpoint='http://sparql.hegroup.org/sparql/',
               uri='http://purl.obolibrary.org/obo/sbo.owl')
SBO._to_user = lambda uri: uri.replace('http://biomodels.net/SBO/SBO_',
                                      'https://identifiers.org/SBO:')
SBO._from_user = lambda uri: multi_replace(uri,
                                          ['http://identifiers.org/sbo/SBO:',
                                          'https://identifiers.org/SBO:'],
                                          'http://biomodels.net/SBO/SBO_')
SBO._sanitize_term = lambda term: term.replace('_', ' ')

NCIT = Ontology(path=None,
                endpoint='http://sparql.hegroup.org/sparql/',
                uri='http://purl.obolibrary.org/obo/ncit.owl')

NCIT._to_user = lambda uri: uri.replace('http://purl.obolibrary.org/obo/NCIT_',
                                      'https://identifiers.org/ncit:')
NCIT._from_user = lambda uri: multi_replace(uri,
                                           ['http://identifiers.org/ncit/ncit:',
                                           'https://identifiers.org/ncit:'],
                                           'http://purl.obolibrary.org/obo/NCIT_')
NCIT._sanitize_term = lambda term: term.replace('_', ' ')


OM = Ontology(path=installation_path('ontologies/om-2.0.rdf'),
              endpoint=None)

'''
'http://purl.obolibrary.org/obo/SO_0000167'
'http://biomodels.net/SBO/SBO_0000241'
'http://purl.obolibrary.org/obo/NCIT_C20865'
'''

