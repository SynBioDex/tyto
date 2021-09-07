from .tyto import Ontology, EBIOntologyLookupService, installation_path, multi_replace


NCBITaxon = Ontology(endpoints=[EBIOntologyLookupService], uri='http://purl.obolibrary.org/obo/ncbitaxon.owl')

# Translate URIs to and from the identifiers.org namespace
NCBITaxon._sanitize_uri = lambda uri: uri.replace('https://identifiers.org/taxonomy:',
                                           'http://purl.obolibrary.org/obo/NCBITaxon_')
NCBITaxon._reverse_sanitize_uri = lambda uri: uri.replace('http://purl.obolibrary.org/obo/NCBITaxon_',
                                                  'https://identifiers.org/taxonomy:')

# Convert spaces in terms to underscore
NCBITaxon._sanitize_term = lambda term: term.replace('_', ' ')