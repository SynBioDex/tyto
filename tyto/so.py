from .tyto import Ontology, Ontobee, installation_path, multi_replace


SO = Ontology(path=installation_path('ontologies/so.owl'),
              endpoints=[Ontobee],
              uri='http://purl.obolibrary.org/obo/so.owl')
"""Ontology instance for Sequence Ontology"""

# Translate URIs to and from the identifiers.org namespace
SO._sanitize_uri = lambda uri: multi_replace(uri,
                                             ['https://identifiers.org/SO:',
                                              'http://identifiers.org/so/SO:'],
                                             'http://purl.obolibrary.org/obo/SO_')
SO._reverse_sanitize_uri = lambda uri: uri.replace('http://purl.obolibrary.org/obo/SO_',
                                                   'https://identifiers.org/SO:')

SO._sanitize_term = lambda term: term
