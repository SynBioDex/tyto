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
    """Mixin class that provides SPARQL queries to SPARQLEndpoint and GraphEndpoint classes
    """

    def get_term_by_uri(self, ontology, uri):
        """Query for a term by its URI

        :param uri: The URI for the term
        :uri: URI
        :param ontology: The Ontology to query
        :ontology: Ontology
        """
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
        """Query for the URI associated with the given an ontology term (e.g., "promoter")
        :param term: The ontology term
        :term: str
        :param ontology: The ontology to query
        :ontology: Ontology
        """

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
                {{{{
                    ?uri rdfs:label ?term
                }}}}
                FILTER(REGEX(?term, '{term}', "i"))
            }}}}
            '''.format(term='^' + term.replace(' ', r'[\\-\\_\\s]') + '$')
        error_msg = '{} not a valid ontology term'.format(term)
        response = self.query(ontology, query, error_msg)
        if not response:
            return None
        if len(response) > 1:
            # If response was ambiguous, try again with a case-sensitive query instead:
            case_sensitive_query = '''
                SELECT distinct ?uri
                {{from_clause}}
                WHERE
                {{{{
                    {{{{
                        ?uri rdfs:label ?term
                    }}}}
                    FILTER(REGEX(?term, '{term}'))
                }}}}
                '''.format(term='^' + term.replace(' ', r'[\\-\\_\\s]') + '$')
            response = self.query(ontology, case_sensitive_query, error_msg)
            if not response:
                # if it was ambiguous before, but got nothing now, then it's the wrong case
                return None
            if len(response) > 1:
                # if it's still ambiguous, then raise an exception
                raise Exception(f'Ambiguous term {term}--found multiple URIs {response}')
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

    def is_ancestor_of(self, ontology: "Ontology", ancestor_uri: str, descendant_uri: str) -> bool:
        query = f'''
            SELECT distinct ?superclass
            {{from_clause}}
            WHERE 
            {{{{
                <{descendant_uri}> rdfs:subClassOf* ?superclass .
                ?superclass rdf:type owl:Class .
            }}}}
            '''
        error_msg = ''
        ancestors = self.query(ontology, query, error_msg)
        return ancestor_uri in ancestors

    def is_descendant_of(self, ontology: "Ontology", descendant_uri: str, ancestor_uri: str) -> bool:
        query = f'''
            SELECT distinct ?descendant
            {{from_clause}}
            WHERE 
            {{{{
                ?descendant rdf:type owl:Class .
                ?descendant rdfs:subClassOf* <{ancestor_uri}>
            }}}}
            '''
        error_msg = ''
        descendants = self.query(ontology, query, error_msg)
        return descendant_uri in descendants

    def get_ontologies(self):
        query = '''
            SELECT distinct ?ontology_uri ?title
            {from_clause}
            WHERE
              {{
                ?ontology_uri a owl:Ontology .
                ?ontology_uri <http://purl.org/dc/elements/1.1/title> ?title
              }}
            '''
        error_msg = 'Graph not found'
        response = self.query(None, query, error_msg)
        if not response or len(response) == 0:
            raise Exception('No ontologies found for this endpoint')

        # Response is a flat list; pack into tuples of (uri, ontology name)
        ontologies = {}
        n_ontologies = int(len(response) / 2)
        for uri, ontology_name in zip(response[:n_ontologies], response[n_ontologies:]):
            ontologies[uri] = ontology_name
        return ontologies

    def is_instance(self, ontology: "Ontology", uri: str) -> bool:
        query = f'''
            SELECT distinct ?instance
            {{from_clause}}
            WHERE
              {{{{
                BIND(<{uri}> AS ?instance)
                ?instance a owl:NamedIndividual .
              }}}}
            '''
        error_msg = ''
        response = self.query(None, query, error_msg)
        if not response or len(response) == 0:
            return False
        else:
            return True

    def get_instances(self, ontology: "Ontology", cls: "URI") -> bool:
        query = f'''
            SELECT distinct ?instance
            {{from_clause}}
            WHERE
              {{{{
                ?instance a owl:NamedIndividual .
                ?instance a <{cls}> .
              }}}}
            '''
        error_msg = ''
        instances = self.query(None, query, error_msg)
        if not instances or len(instances) == 0:
            raise Exception(f'{cls} has no instances')
        else:
            return instances



class Endpoint(QueryBackend, abc.ABC):

    def __init__(self, url):
        """
        :param url: The URL for the endpoint
        :url: str        
        """
        self.url = url


class RESTEndpoint(QueryBackend, abc.ABC):
    """Class for issuing and handling HTTP requests
    """

    def __init__(self, url):
        """
        :param url: The base URL for the REST endpoints
        :url: str        
        """
        self.url = url

    def _get_request(self, ontology: "Ontology", request: str):
        response = requests.get(request)
        if response.status_code == 200:
            return response.json()
        raise urllib.error.HTTPError(request, response.status_code, response.reason, response.headers, None)


class SPARQLEndpoint(SPARQLBuilder, Endpoint):
    """Class which issues SPARQL queries to an endpoint
    """

    def __init__(self, url):
        """
        :param url: The SPARQL endpoint
        :url: str        
        """
        super().__init__(url)
        self._endpoint = SPARQLWrapper(url)
        self._endpoint.setReturnFormat(JSON)

    def query(self, ontology, sparql, err_msg):
        """Issues SPARQL query
        """
        self._endpoint.setQuery(sparql)
        response = self._endpoint.query()
        return self.convert(response)

    def convert(self, response):
        '''Converts standard SPARQL query JSON into a flat list.

        See https://www.w3.org/TR/2013/REC-sparql11-results-json-20130321/
        '''
        converted_response = []
        if response:
            response = response.convert()  # Convert http response to JSON
            var = response['head']['vars'][0]
            for var in response['head']['vars']:
                for binding in response['results']['bindings']:
                    if var in binding:
                        converted_response.append(binding[var]['value'])
        return converted_response


class GraphEndpoint(SPARQLBuilder, Endpoint):
    """Class for querying a local graph from a file
    """
    def __init__(self, file_path):
        """
        """
        self.graph = rdflib.Graph()
        self.path = file_path

    def is_loaded(self):
        return bool(self.graph)

    def load(self):
        if self.path.split('.')[-1] == 'ttl':
            self.graph.parse(self.path, format='ttl')
        else:
            self.graph.parse(self.path)

    def query(self, ontology, sparql, err_msg):
        sparql_final = sparql.format(from_clause='')  # Because only one ontology per file, delete the from clause
        response = self.graph.query(sparql_final)
        return self.convert(response)

    def convert(self, response):
        """Extracts and flattens queried variables from rdflib response into a list
        """
        return [str(row[0]) for row in response]


class OntobeeEndpoint(SPARQLEndpoint):

    def __init__(self):
        super().__init__('http://sparql.hegroup.org/sparql/')

    def query(self, ontology, sparql, err_msg):
        # The general naming pattern for an Ontobee graph URI is to transform a PURL
        # http://purl.obolibrary.org/obo/$foo.owl (note foo must be all lowercase
        # by OBO conventions) to http://purl.obolibrary.org/obo/merged/uppercase($foo).
        from_clause = ''
        if ontology:
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

        term = urllib.parse.quote_plus(term)
        get_query = f'{self.url}/search?q={term}&ontology={short_id}&queryFields=label'
        response = requests.get(get_query)
        if response.status_code == 200:
            response = response.json()
            if not response or not len(response['response']['docs']):
                return None
            #if len(response['response']['docs']) > 1 and response['response']['docs'][0]['label'] == response['response']['docs'][1]['label']:
            #    raise Exception('Ambiguous term--more than one matching URI found')
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

    def get_descendants(self, ontology: "Ontology", uri: str):
        sanitized_uri = ontology._sanitize_uri(uri)
        encoded_uri = urllib.parse.quote_plus(urllib.parse.quote_plus(sanitized_uri)) 
        encoded_uri = urllib.parse.quote_plus(sanitized_uri)

        request = '{url}/ontologies/{ontology}/descendants?id=' + encoded_uri
        response = self._get_request(ontology, request)
        descendants = []
        if '_embedded' in response and 'terms' in response['_embedded']:
             descendants = [term['iri'] for term in response['_embedded']['terms']]
             descendants = [ontology._reverse_sanitize_uri(iri) for iri in descendants]
        return descendants

    def get_ancestors(self, ontology: "Ontology", uri: str):
        sanitized_uri = ontology._sanitize_uri(uri)
        encoded_uri = urllib.parse.quote_plus(urllib.parse.quote_plus(sanitized_uri)) 
        encoded_uri = urllib.parse.quote_plus(sanitized_uri)

        request = '{url}/ontologies/{ontology}/ancestors?id=' + encoded_uri
        response = self._get_request(ontology, request)
        descendants = []
        if '_embedded' in response and 'terms' in response['_embedded']:
             ancestors = [term['iri'] for term in response['_embedded']['terms']]
             ancestors = [ontology._reverse_sanitize_uri(iri) for iri in ancestors]
        return ancestors

    def is_parent_of(self, ontology: "Ontology", parent_uri: str, child_uri: str) -> bool:
        parent_uri = ontology._reverse_sanitize_uri(parent_uri)
        return parent_uri in self.get_parents(ontology, child_uri) 	

    def is_child_of(self, ontology: "Ontology", child_uri: str, parent_uri: str) -> bool:
        child_uri = ontology._reverse_sanitize_uri(child_uri)
        return child_uri in self.get_children(ontology, parent_uri)

    def is_descendant_of(self, ontology: "Ontology", descendant_uri: str, ancestor: str) -> bool:
        descendant_uri = ontology._reverse_sanitize_uri(descendant_uri)
        return descendant_uri in self.get_descendants(ontology, ancestor) 	

    def is_ancestor_of(self, ontology: "Ontology", ancestor_uri: str, descendant_uri: str) -> bool:
        ancestor_uri = ontology._reverse_sanitize_uri(ancestor_uri)
        return ancestor_uri in self.get_ancestors(ontology, descendant_uri)

    def get_ontologies(self):
        if not self.ontology_short_ids:
            self._load_ontology_ids()
        return self.ontology_short_ids

    def convert(self, response):
        pass

    def query(self, query):
        pass

class PUG_REST(RESTEndpoint):

    def __init__(self):
        super().__init__('https://pubchem.ncbi.nlm.nih.gov/rest/pug/substance')

    def get_term_by_uri(self, ontology: "Ontology", uri: str):
        if 'https://identifiers.org/pubchem.substance:' in uri:
            uri = uri.replace('https://identifiers.org/pubchem.substance:',
                              'https://pubchem.ncbi.nlm.nih.gov/rest/pug/substance/sid/')
        get_query = f'{uri}/synonyms/JSON'
        response = requests.get(get_query)
        if response.status_code == 200:
            return response.json()['InformationList']['Information'][0]['Synonym'][0]
        if response.status_code == 404:
            return None
        raise urllib.error.HTTPError(get_query, response.status_code, response.reason, response.headers, None)

    def get_uri_by_term(self, ontology: "Ontology", term: str):
        term = urllib.parse.quote(term)
        get_query = f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/substance/name/{term}/sids/JSON'
        response = requests.get(get_query)
        if response.status_code == 200:
            response = response.json()
            if not response:
                return None
            if len(response['IdentifierList']['SID']) > 1:
                raise LookupError('Ambiguous term--more than one matching ID found')
            return f"https://identifiers.org/pubchem.substance:{response['IdentifierList']['SID'][0]}"
        raise urllib.error.HTTPError(get_query, response.status_code, response.reason, response.headers, None)


Ontobee = OntobeeEndpoint()
"""Endpoint instance representing Ontobee. Ontobee is the default linked data server for most OBO Foundry library ontologies, but is also been used for many non-OBO ontologies. 
"""

EBIOntologyLookupService = EBIOntologyLookupServiceAPI()
"""The Ontology Lookup Service (OLS) is a repository for biomedical ontologies that aims to provide a single point of access to the latest ontology versions. Hosted by the European Bioinformatics Institute
"""

PubChemAPI = PUG_REST()
