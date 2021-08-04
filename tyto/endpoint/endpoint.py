from __future__ import annotations
import abc

import rdflib
from SPARQLWrapper import SPARQLWrapper, JSON


class QueryBackend(abc.ABC):

    @abc.abstractmethod
    def get_term_by_uri(self, ontology: Ontology, uri: str):
        return

    @abc.abstractmethod
    def get_uri_by_term(self, ontology: Ontology, term: str):
        return

    @abc.abstractmethod
    def query(self, ontology: Ontology, sparql: str):
        return

    @abc.abstractmethod
    def convert(self, response):
        return


class SPARQLBuilder():

    def get_term_by_uri(self, ontology, uri):
        '''
        Get the ontology term (e.g., "promoter") corresponding to the given URI
        :param uri: The URI for the term
        :return: str
        '''
        query = '''
            SELECT distinct ?label
            WHERE
            {{{{
                optional
                {{{{
                    <{uri}> rdfs:label ?label .
                     filter langMatches(lang(?label), "en")
                }}}}
                optional
                {{{{
                    <{uri}> rdfs:label ?label .
                }}}}
            }}}}
            '''.format(uri=uri)
        error_msg = '{} not found'.format(uri)
        response = self.query(ontology, query, error_msg)
        if not response:
            return None
        response = response[0]
        return response

    def get_uri_by_term(self, ontology: Ontology, term: str) -> str:
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
        query = '''
            SELECT distinct ?uri
            {{from_clause}}
            WHERE
            {{{{
                optional 
                {{{{
                    ?uri rdfs:label "{term}"@en
                }}}}
                optional
                {{{{ 
                    ?uri rdfs:label "{term}"
                }}}}
                optional
                {{{{ 
                    ?uri rdfs:label "{term}"^^xsd:string
                }}}}
            }}}}
            '''.format(term=term)
        error_msg = '{} not a valid ontology term'.format(term)
        response = self.query(ontology, query, error_msg)
        if not response:
            return None
        response = response[0]
        return response

    def is_subclass_of(self, ontology: Ontology, subclass_uri: str, superclass_uri: str) -> bool:
        query = '''
            SELECT distinct ?subclass 
            {{from_clause}}
            WHERE 
            {{{{
                ?subclass rdf:type owl:Class .
                ?subclass rdfs:subClassOf <{}>
            }}}}
            '''.format(superclass_uri)
        error_msg = ''
        subclasses = self.query(ontology, query, error_msg)
        return subclass_uri in subclasses

    def get_ontology(self):
        query = '''
            SELECT distinct ?ontology_uri
            WHERE
              {
                ?ontology_uri a owl:Ontology
              }
            '''
        error_msg = 'Graph not found'
        response = self._query(ontology, query, error_msg)[0]
        return response


class Endpoint(QueryBackend, abc.ABC):
    pass


class SPARQLEndpoint(SPARQLBuilder, Endpoint):

    def __init__(self, url):
        self.endpoint = SPARQLWrapper(url)
        self.endpoint.setReturnFormat(JSON)

    def query(self, ontology, sparql, err_msg):
        self.endpoint.setQuery(sparql)
        response = self.endpoint.query()
        return self.convert(response)

    def convert(self, response):
        '''
        Returns standard SPARQL query JSON. This extracts and flattens the queried
        variables into a list.

        See https://www.w3.org/TR/2013/REC-sparql11-results-json-20130321/
        '''
        converted_response = []
        if response:
            response = response.convert()  # Convert http response to JSON
            for var, binding in zip(response['head']['vars'],
                                    response['results']['bindings']):
                if var in binding:
                    converted_response.append(binding[var]['value'])
        return converted_response


class Graph(SPARQLBuilder, Endpoint):

    def __init__(self, file_path):
        self.graph = rdflib.Graph()
        self.path = file_path

    def is_loaded(self):
        return bool(self.graph)

    def load(self):
        self.graph.parse(self.path)

    def query(self, ontology, sparql, err_msg):
        sparql_final = sparql.format(from_clause='')  # Because only one ontology per file, delete the from clause
        response = self.graph.query(sparql_final)
        return self.convert(response)

    def convert(self, response):
        '''
        Extracts and flattens queried variables from rdflib response into a list
        '''
        return [str(row[0]) for row in response]


class OntobeeEndpoint(SPARQLEndpoint):

    def __init__(self):
        super().__init__('http://sparql.hegroup.org/sparql/')

    def query(self, ontology, sparql, err_msg):
        # The general naming pattern for an Ontobee graph URI is to transform a PURL
        # http://purl.obolibrary.org/obo/$foo.owl (note foo must be all lowercase
        # by OBO conventions) to http://purl.obolibrary.org/obo/merged/uppercase($foo).
        from_clause = ''
        if ontology.uri:
            ontology_uri = ontology.uri
            if 'http://purl.obolibrary.org/obo/' in ontology_uri:
                ontology_uri = ontology_uri.replace('http://purl.obolibrary.org/obo/', '')
                ontology_uri = ontology_uri.replace('.owl', '')
                ontology_uri = ontology_uri.upper()
                ontology_uri = 'http://purl.obolibrary.org/obo/merged/' + ontology_uri
            from_clause = f'FROM <{ontology_uri}>'
        sparql = sparql.format(from_clause=from_clause)
        response = super().query(ontology, sparql, err_msg)
        return response




Ontobee = OntobeeEndpoint()
