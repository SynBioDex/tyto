import abc
import requests
import urllib.parse
import json
from io import StringIO

import rdflib
from SPARQLWrapper import SPARQLWrapper, JSON


class QueryBackend(abc.ABC):

    @abc.abstractmethod
    def get_term_by_uri(self, ontology: "Ontology", uri: str):
        return

    @abc.abstractmethod
    def get_uri_by_term(self, ontology: "Ontology", term: str):
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

    def get_uri_by_term(self, ontology: "Ontology", term: str) -> str:
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

    def is_child_of(self, ontology: "Ontology", child_uri: str, parent_uri: str) -> bool:
        query = f'''
            SELECT distinct ?child 
            {{from_clause}}
            WHERE 
            {{{{
                ?child rdf:type owl:Class .
                ?child rdfs:subClassOf <{parent_uri}>
            }}}}
            '''
        error_msg = ''
        child_terms = self.query(ontology, query, error_msg)
        return child_uri in child_terms

    def is_parent_of(self, ontology: "Ontology", parent_uri: str, child_uri: str) -> bool:
        query = f'''
            SELECT distinct ?parent
            {{from_clause}}
            WHERE 
            {{{{
                <{child_uri}> rdf:type owl:Class .
                <{child_uri}> rdfs:subClassOf ?parent
            }}}}
            '''
        error_msg = ''
        parent_terms = self.query(ontology, query, error_msg)
        return parent_uri in parent_terms

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

    def __init__(self, url):
        self.url = url


class RESTEndpoint(QueryBackend, abc.ABC):

    def __init__(self, url):
        self.url = url

    def _get_request(self, ontology: "Ontology", request: str):
        response = requests.get(request)
        if response.status_code == 200:
            return response.json()
        raise urllib.error.HTTPError(request, response.status_code, response.reason, response.headers, None)


class SPARQLEndpoint(SPARQLBuilder, Endpoint):

    def __init__(self, url):
        super().__init__(url)
        self._endpoint = SPARQLWrapper(url)
        self._endpoint.setReturnFormat(JSON)

    def query(self, ontology, sparql, err_msg):
        self._endpoint.setQuery(sparql)
        response = self._endpoint.query()
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


class GraphEndpoint(SPARQLBuilder, Endpoint):

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


class EBIOntologyLookupServiceAPI(RESTEndpoint):

    def __init__(self):
        super().__init__('http://www.ebi.ac.uk/ols/api')
        self.ontology_short_ids = {}  # Set by the _load_ontology method

    def _load_ontology_ids(self):
        response = requests.get(f'{self.url}/ontologies?size=1')
        response = response.json()
        total_ontologies = response['page']['totalElements']
        response = requests.get(f'{self.url}/ontologies?size={total_ontologies}')
        response = response.json()
        for o in response['_embedded']['ontologies']:
            short_id = o['ontologyId']
            iri = o['config']['id']
            self.ontology_short_ids[iri] = short_id

    def _get_request(self, ontology: "Ontology", get_request: str):
        if not self.ontology_short_ids:
            self._load_ontology_ids()
        if ontology.uri not in self.ontology_short_ids:
            raise LookupError(f'Ontology {ontology.uri} is not available at EBI Ontology Lookup Service')
        short_id = self.ontology_short_ids[ontology.uri]
        get_request = get_request.format(url=self.url, ontology=short_id)
        return super()._get_request(ontology, get_request)

    def get_term_by_uri(self, ontology: "Ontology", uri: str):
        if not self.ontology_short_ids:
            self._load_ontology_ids()
        if ontology.uri not in self.ontology_short_ids:
            raise LookupError(f'Ontology {ontology.uri} is not available at EBI Ontology Lookup Service')
        short_id = self.ontology_short_ids[ontology.uri]
        get_query = f'{self.url}/ontologies/{short_id}/terms/' + urllib.parse.quote_plus(urllib.parse.quote_plus(uri))
        response = requests.get(get_query)
        if response.status_code == 200:
            return response.json()['label']
        if response.status_code == 404:
            return None
        raise urllib.error.HTTPError(get_query, response.status_code, response.reason, response.headers, None)

    def get_uri_by_term(self, ontology: "Ontology", term: str):
        if not self.ontology_short_ids:
            self._load_ontology_ids()
        if ontology.uri not in self.ontology_short_ids:
            raise LookupError(f'Ontology {ontology.uri} is not available at EBI Ontology Lookup Service')
        short_id = self.ontology_short_ids[ontology.uri]

        get_query = f'{self.url}/search?q={term}&ontology={short_id}&queryFields=label'
        response = requests.get(get_query)
        if response.status_code == 200:
            response = response.json()
            if not response or not len(response['response']['docs']):
                return None
            return response['response']['docs'][0]['iri']
        raise urllib.error.HTTPError(get_query, response.status_code, response.reason, response.headers, None)

    def get_parents(self, ontology: "Ontology", uri: str):
        sanitized_uri = ontology._sanitize_uri(uri)
        encoded_uri = urllib.parse.quote_plus(urllib.parse.quote_plus(sanitized_uri)) 
        encoded_uri = urllib.parse.quote_plus(sanitized_uri)

        request = '{url}/ontologies/{ontology}/parents?id=' + encoded_uri
        response = self._get_request(ontology, request)
        parents = []
        if '_embedded' in response and 'terms' in response['_embedded']:
             parents = [term['iri'] for term in response['_embedded']['terms']]
             parents = [ontology._reverse_sanitize_uri(iri) for iri in parents]
        return parents

    def get_children(self, ontology: "Ontology", uri: str):
        sanitized_uri = ontology._sanitize_uri(uri)
        encoded_uri = urllib.parse.quote_plus(urllib.parse.quote_plus(sanitized_uri)) 
        encoded_uri = urllib.parse.quote_plus(sanitized_uri)

        request = '{url}/ontologies/{ontology}/children?id=' + encoded_uri
        response = self._get_request(ontology, request)
        children = []
        if '_embedded' in response and 'terms' in response['_embedded']:
             children = [term['iri'] for term in response['_embedded']['terms']]
             children = [ontology._reverse_sanitize_uri(iri) for iri in children]
        return children

    def is_parent_of(self, ontology: "Ontology", parent_uri: str, child_uri: str) -> bool:
        parent_uri = ontology._reverse_sanitize_uri(parent_uri)
        return parent_uri in self.get_parents(ontology, child_uri) 	

    def is_child_of(self, ontology: "Ontology", child_uri: str, parent_uri: str) -> bool:
        child_uri = ontology._reverse_sanitize_uri(child_uri)
        return child_uri in self.get_children(ontology, parent_uri)

    def convert(self, response):
        pass

    def query(self, query):
        pass


Ontobee = OntobeeEndpoint()
EBIOntologyLookupService = EBIOntologyLookupServiceAPI()
