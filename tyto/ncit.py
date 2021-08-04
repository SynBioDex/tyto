from .owlet import Ontology, Ontobee, multi_replace


NCIT = Ontology(path=None,
                endpoints=[Ontobee],
                uri='http://purl.obolibrary.org/obo/ncit.owl')

# Convert PURL URIs to identifiers.org
NCIT._sanitize_uri = lambda uri: multi_replace(uri,
                                               ['http://identifiers.org/ncit/ncit:',
                                                'https://identifiers.org/ncit:'],
                                               'http://purl.obolibrary.org/obo/NCIT_')
NCIT._reverse_sanitize_uri = lambda uri: uri.replace('http://purl.obolibrary.org/obo/NCIT_',
                                                     'https://identifiers.org/ncit:')

# Spaces are not allowed because they render an invalid Python symbol
NCIT._sanitize_term = lambda term: term.replace('_', ' ')
