from .tyto import Ontology, Ontobee, installation_path, multi_replace


SBO = Ontology(path=installation_path('ontologies/SBO_OWL.owl'),
               endpoints=[Ontobee],
               uri='http://biomodels.net/SBO/')
"""Ontology instance for Systems Biology Ontology"""


# Translate URIs to and from identifiers.org namespace
SBO._sanitize_uri = lambda uri: multi_replace(uri,
                                              ['http://identifiers.org/sbo/SBO:',
                                               'https://identifiers.org/SBO:'],
                                              'http://biomodels.net/SBO/SBO_')
SBO._reverse_sanitize_uri = lambda uri: uri.replace('http://biomodels.net/SBO/SBO_',
                                                    'https://identifiers.org/SBO:')
