from .tyto import Ontology, Ontobee, installation_path, multi_replace


EDAM = Ontology(endpoints=[Ontobee],
                uri='http://edamontology.org/EDAM.owl')
"""EDAM (EMBRACE Data and Methods) is an ontology of common bioinformatics operations, topics, types of data including identifiers, and formats. EDAM comprises common concepts (shared within the bioinformatics community) that apply to semantic annotation of resources."""

