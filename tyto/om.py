from .tyto import Ontology, Ontobee, installation_path


OM = Ontology(path=installation_path('ontologies/om-2.0.rdf'),
              endpoints=None)
"""Ontology instance for Ontology of Units of Measure"""

# Support American English spellings
OM._sanitize_term = lambda term: term.replace('liter', 'litre').replace('meter', 'metre').replace('molar', 'molair').replace('_', ' ')
OM._reverse_sanitize_term = lambda term: term.replace('litre', 'liter').replace('metre', 'meter').replace('molair', 'molar')
