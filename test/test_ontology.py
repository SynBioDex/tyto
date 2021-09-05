import unittest
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

    def test_parent_of(self):
        self.assertFalse(SO.inducible_promoter.is_parent_of(SO.promoter))
        self.assertTrue(SO.promoter.is_parent_of(SO.inducible_promoter))


class TestOLS(unittest.TestCase):

    def test_SO(self):
        restore_endpoints = SO.endpoints
        restore_graph = SO.graph
        SO.endpoints = [EBIOntologyLookupService]
        SO.graph = None
        uri = 'https://identifiers.org/SO:0000167'
        self.assertEqual(SO.get_term_by_uri(uri), 'promoter')
        self.assertEqual(SO.promoter, uri)
        uri = uri.replace('0000167', 'xxxxxxx')
        with self.assertRaises(LookupError):
            self.assertEqual(SO.get_term_by_uri(uri), 'promoter')
        with self.assertRaises(LookupError):
            self.assertIsNone(SO.foo)
        SO.endpoints = restore_endpoints
        SO.graph = restore_graph

    def test_SBO(self):
        restore_endpoints = SBO.endpoints
        restore_graph = SBO.graph
        uri = 'https://identifiers.org/SBO:0000241'
        self.assertEqual(SBO.get_term_by_uri(uri), 'functional entity')


if __name__ == '__main__':
    unittest.main()
