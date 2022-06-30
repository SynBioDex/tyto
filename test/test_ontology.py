import unittest
import os

from tyto import *
from tyto.endpoint import EBIOntologyLookupService


class TestOntology(unittest.TestCase):

    def test_SO(self):
        term_a = 'sequence_feature'
        uri = SO.get_uri_by_term(term_a)  # Confirm term query with underscore works
        self.assertEqual(uri, 'https://identifiers.org/SO:0000110')
        term_b = SO.get_term_by_uri(uri)
        self.assertEqual(term_a, term_b)
        with self.assertRaises(LookupError):
            uri = SO.get_uri_by_term('not_a_term')
        # Test deprecated identifier format
        term_b = SO.get_term_by_uri('http://identifiers.org/so/SO:0000110')
        self.assertEqual(term_a, term_b)
        # test handling of OWL anonymous node problem (https://github.com/SynBioDex/tyto/issues/65)
        term_c = SO.deletion
        self.assertEqual(term_c, 'https://identifiers.org/SO:0000159')

    def test_getitem(self):
        # For terms with special characters, we must use subscripting
        # rather than dynamic attributes for ontology terms
        term_a = 'Escherichia coli #1/H766'
        uri = NCBITaxon[term_a]
        self.assertEqual(uri, 'https://identifiers.org/taxonomy:1354003')

    def test_SBO(self):
        uri_a = 'https://identifiers.org/SBO:0000000'
        term = SBO.get_term_by_uri(uri_a)
        # Confirm term query with space works
        self.assertEqual(term, 'systems biology representation')
        uri_b = SBO.get_uri_by_term(term)
        self.assertEqual(uri_a, uri_b)
        # Test deprecated identifier format
        term = SBO.get_term_by_uri('http://identifiers.org/sbo/SBO:0000000')
        self.assertEqual(term, 'systems biology representation')

    def test_dynamic_ontology_attributes(self):
        # Tests that our override of the __getattr__ method is working.
        # Tests dynamic generation of attributes for ontology terms; also verifies that
        # the Ontology's other methods (e.g., get_uri_by_term) remain accessible
        self.assertEqual(SO.promoter, SO.get_uri_by_term('promoter'))

        # When an Ontology term has spaces, the attribute that is dynamically generated
        # should replace these with underscores
        self.assertEqual(SBO.systems_biology_representation,
                         SBO.get_uri_by_term('systems biology representation'))

        self.assertNotEqual(SBO.systems_biology_representation,
                            SBO.reactant)

        # Raise an exception if an invalid term is specified
        with self.assertRaises(LookupError):
            not_a_term = SO.not_a_term

    def test_NCIT(self):
        self.assertEqual(NCIT.Growth_Medium, 'https://identifiers.org/ncit:C85504')

    def test_OM(self):
        self.assertEqual(OM.molar, OM.molair)
        self.assertEqual(OM.liter, OM.liter)
        self.assertEqual(OM.meter, OM.metre)
        self.assertEqual(OM.get_term_by_uri('http://www.ontology-of-units-of-measure.org/resource/om-2/hour'),
                         'hour')

    def test_child_of(self):
        self.assertTrue(type(SO.promoter) is URI)
        self.assertTrue(SO.inducible_promoter.is_child_of(SO.promoter))
        self.assertFalse(SO.promoter.is_child_of(SO.inducible_promoter))
        self.assertTrue(NCBITaxon.Escherichia_coli.is_child_of(NCBITaxon.Escherichia))

    def test_parent_of(self):
        self.assertFalse(SO.inducible_promoter.is_parent_of(SO.promoter))
        self.assertTrue(SO.promoter.is_parent_of(SO.inducible_promoter))

    def test_descendants(self):
        self.assertTrue(SO.RNApol_III_promoter.is_descendant_of(SO.promoter))
        self.assertFalse(SO.promoter.is_descendant_of(SO.RNApol_III_promoter))

    def test_ancestors(self):
        self.assertTrue(SO.promoter.is_ancestor_of(SO.RNApol_III_promoter))
        self.assertFalse(SO.promoter.is_descendant_of(SO.RNApol_III_promoter))

    def test_case_insensitivity(self):
        self.assertEqual(SBO.NON_CODING_RNA, SBO.non_coding_rna)

    def test_nonunique_labels(self):
        test_ontology = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_case_0.owl')
        o = Ontology(path=test_ontology,
                     uri='http://purl.obolibrary.org/obo/so.owl')
        with self.assertRaises(LookupError):
            uri = o.foobar

    def test_get_ontologies(self):
       self.assertEqual(tyto.Ontobee.get_ontologies()\
                        ['http://purl.obolibrary.org/obo/ecao.owl'],
                        'Echinoderm Anatomy and Development Ontology')
       self.assertEqual(tyto.EBIOntologyLookupService.get_ontologies()
                        ['http://purl.obolibrary.org/obo/gno.owl'],
                        'gno')

    def test_relation_checks(self):
        #Term('inducible_promoter', SO).is_a('promoter')
        URI(SO.inducible_promoter, SO).is_a(SO.promoter)

class TestOLS(unittest.TestCase):

    SO_endpoints = SO.endpoints
    SO_graph = SO.graph
    SBO_endpoints = SBO.endpoints
    SBO_graph = SBO.graph

    @classmethod
    def setUpClass(cls):
        SO.endpoints = [EBIOntologyLookupService]
        SO.graph = None
        SBO.endpoints = [EBIOntologyLookupService]
        SBO.graph = None

    @classmethod
    def tearDownClass(cls):
        SO.endpoints = TestOLS.SO_endpoints
        SO.graph = TestOLS.SO_graph
        SBO.endpoints = TestOLS.SBO_endpoints
        SBO.graph = TestOLS.SBO_graph

    def test_SO(self):
        uri = 'https://identifiers.org/SO:0000167'
        self.assertEqual(SO.get_term_by_uri(uri), 'promoter')
        self.assertEqual(SO.promoter, uri)
        uri = uri.replace('0000167', 'xxxxxxx')
        with self.assertRaises(LookupError):
            self.assertEqual(SO.get_term_by_uri(uri), 'promoter')
        with self.assertRaises(LookupError):
            self.assertIsNone(SO.foo)

    def test_parents(self):
        self.assertCountEqual(EBIOntologyLookupService.get_parents(SO, SO.inducible_promoter),
                              [SO.promoter])
        self.assertTrue(SO.inducible_promoter.is_child_of(SO.promoter))

    def test_children(self):
        children = EBIOntologyLookupService.get_children(SO, SO.promoter) 
        self.assertIn(SO.inducible_promoter, children)
        self.assertNotIn(SO.RNApol_III_promoter, children)  # is a descendant, not a child
        self.assertEqual(len(children), 7)
        self.assertTrue(SO.promoter.is_parent_of(SO.inducible_promoter))

    def test_descendants(self):
        descendants = EBIOntologyLookupService.get_descendants(SO, SO.promoter) 
        self.assertIn(SO.RNApol_III_promoter, descendants)

    def test_ancestors(self):
        ancestors = EBIOntologyLookupService.get_ancestors(NCBITaxon, NCBITaxon.Escherichia_coli)
        self.assertIn(NCBITaxon.Bacteria, ancestors)

    def test_SBO(self):
        uri = 'https://identifiers.org/SBO:0000241'
        self.assertEqual(SBO.get_term_by_uri(uri), 'functional entity')

class TestSBOL(unittest.TestCase):

    def test_sbol2(self):
        self.assertEqual(SBOL2.inline, 'http://sbols.org/v2#inline')
        self.assertEqual(SBOL2.reverseComplement, 'http://sbols.org/v2#reverseComplement')
        self.assertEqual(SBOL2.ComponentDefinition, 'http://sbols.org/v2#ComponentDefinition')

    def test_sbol3(self):
        self.assertEqual(SBOL3.inline, 'http://sbols.org/v3#inline')
        self.assertEqual(SBOL3.reverseComplement, 'http://sbols.org/v3#reverseComplement')
        self.assertEqual(SBOL3.Component, 'http://sbols.org/v3#Component')

class TestPubChem(unittest.TestCase):

    def test_pubchem(self):
        self.assertEqual(PubChem['LUDOX(R) CL-X colloidal silica, 45 wt. % suspension in H2O'], 'https://identifiers.org/pubchem.substance:24866361')
        self.assertEqual(PubChem.get_term_by_uri('https://identifiers.org/pubchem.substance:24866361'), 'LUDOX(R) CL-X colloidal silica, 45 wt. % suspension in H2O')
        with self.assertRaises(LookupError):
            # Ambiguous term matches many SIDs
            PubChem['water']

class TestPAML(unittest.TestCase):

    def test_paml(self):
        self.assertEqual(PAML.SampleArray, 'http://bioprotocols.org/paml#SampleArray')

if __name__ == '__main__':
    unittest.main()
