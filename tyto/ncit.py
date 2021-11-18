from .tyto import Ontology, Ontobee, multi_replace


NCIT = Ontology(path=None,
                endpoints=[Ontobee],
                uri='http://purl.obolibrary.org/obo/ncit.owl')
"""Ontology instance for National Cancer Institute Thesaurus"""

# Convert PURL URIs to identifiers.org
NCIT._sanitize_uri = lambda uri: multi_replace(uri,
                                               ['http://identifiers.org/ncit/ncit:',
                                                'https://identifiers.org/ncit:'],
                                               'http://purl.obolibrary.org/obo/NCIT_')
NCIT._reverse_sanitize_uri = lambda uri: uri.replace('http://purl.obolibrary.org/obo/NCIT_',
                                                     'https://identifiers.org/ncit:')

