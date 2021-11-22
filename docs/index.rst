
Take Your Terms from Ontologies (Tyto)
======================================
Tyto is a tool that supports standardized annotation practices using terms from controlled vocabularies and ontologies. Tyto allows a user to reference ontology terms in their code using human-readable labels rather than uniform resource identifiers (URIs), thus rendering code more readable and easier to understand.

Examples using dynamic attributes
*********************************

Tyto allows the user to reference an ontology term as an attribute on an Ontology instance. In the following example, the term ``promoter`` is referenced from an Ontology instance representing the `Sequence Ontology <http://www.sequenceontology.org/>`_.

.. code-block:: python 

   >>> SO.promoter
   'https://identifiers.org/SO:0000167'

Some ontology terms have spaces, such as the term ``functional entity`` from the Systems Biology Ontology. In these cases, replace the space with an underscore:

.. code-block:: python 

   >>> SBO.functional_entity
   'https://identifiers.org/SBO:0000241'

Example use with subscripts
***************************

Some ontology terms may have special characters, especially in the NCBI Taxonomy. In this case, dynamic attributes cannot be used as it would result in invalid Python symbols. Instead, use subscripting:

.. code-block:: python 

   >>> NCBITaxon['Escherichia coli O157:H-']
   'https://identifiers.org/taxonomy:183192'

Query Backend
=============
Tyto's back-end dynamically queries ontology lookup services for the URI that corresponds to the attribute name or subscript. This dynamic querying approach is in keeping with the principles of the semantic web, in which knowledge is interlinked and distributed across the web rather than concentrated in isolated resources. In this way, Tyto provides up-to-date access to hundreds of ontologies without the need for packaging a large amount of data with the distribution.

Currently Tyto supports queries to `Ontobee <http://www.ontobee.org/>`_ and the `EBI Ontology Lookup Service <https://www.ebi.ac.uk/ols/index>`_. In addition, it includes an extensible framework so that users may add their own REST services or SPARQL endpoints. It is also possible to query local OWL files for offline work.

Support for SBOL Ontologies
===========================
Tyto was originally developed to support use of the `Synthetic Biology Open Language <https://sbolstandard.org/>`_ which uses ontologies as a source of standardized terms for annotating synthetic biology data. Tyto provides "out-of-the-box" support for most of the ontologies used in SBOL:

* ``SO``: sequence ontology
* ``SBO``: systems biology ontology
* ``NCBITaxon``: NCBI taxonomy
* ``NCIT``: National Cancer Institute Thesaurus
* ``OM``: Ontology of Units of Measure

.. note::

   SBOL identifiers standardize on the ``identifiers.org`` namespace. By default most ontology lookup services standardize on the ``purl.org`` namespace. Tyto's built-in ``Ontology`` interfaces automatically translate from ``purl.org`` to ``identifiers.org`` namespaces.

Support for Other Ontologies
============================
Ontobee and EBI Ontology Lookup Service host hundreds of ontologies. Even though Tyto has built-in support for only a few of these, it is easy to define your own ``Ontology`` interface.

First identify the URI associated with the ontology you wish to use. To do this, use the ``get_ontologies`` method on your ``Endpoint`` instance to get a dictionary of available ontologies:

.. code-block:: python

   >>> for uri, ontology in tyto.EBIOntologyLookupService.get_ontologies().items():
   ...     print(uri, ontology)
   ... 
   http://purl.obolibrary.org/obo/aeo.owl aeo
   http://purl.allotrope.org/voc/afo/merged-OLS/REC/2019/05/10 afo
   http://purl.obolibrary.org/obo/agro-edit.owl agro
   .
   .
   .

Once you have identified the URI of your desired ontology, instantiate an ``Ontology``, specifying its URI and the lookup service:

.. code-block:: python 

   >>> from tyto import EBIOntologyLookupService, Ontology
   >>> KISAO = Ontology(uri='http://www.biomodels.net/kisao/KISAO_FULL#', endpoints=[EBIOntologyLookupService])
   >>> KISAO.Gillespie_direct_algorithm
   'http://www.biomodels.net/kisao/KISAO#KISAO_0000029'

Inference
=========
Tyto can be used to reason about the relationships between terms in an ontology.

For example:

.. code-block:: python

   >>> SO.inducible_promoter.is_a(SO.promoter)
   True
   >>> SO.inducible_promoter.is_a(SO.ribosome_entry_site)
   False

Other supported inference methods include:

.. code-block:: python

   term1.is_a(term2)
   term1.is_descendant_of(term2)
   term1.is_ancestor_of(term2)
   term1.is_child_of(term2)
   term1.is_parent_of(term2)


.. toctree::
   :maxdepth: 2

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. highlight:: python
