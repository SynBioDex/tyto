from setuptools import setup, find_packages

setup(name='tyto',
      version='1.2.1',
      description='Automatically generates Python symbols for ontology terms',
      python_requires='>=3.6',
      url='https://github.com/SynBioDex/tyto',
      author='Bryan Bartley',
      author_email='bartleyba@sbolstandard.org',
      license='Apache-2',
      # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
            # How mature is this project? Common values are
            #   3 - Alpha
            #   4 - Beta
            #   5 - Production/Stable
            'Development Status :: 5 - Production/Stable',

            # Indicate who your project is intended for
            'Intended Audience :: Developers',

            # Pick your license as you wish (should match "license" above)
            'License :: OSI Approved :: Apache Software License',

            # Specify the Python versions you support here. In particular, ensure
            # that you indicate whether you support Python 2, Python 3 or both.
            'Programming Language :: Python :: 3'
      ],
      # What does your project relate to?
      keywords='ontologies',
      packages=find_packages(),
      package_data={'tyto': ['ontologies/*.owl',
                              'ontologies/*.rdf',
                              'ontologies/*.ttl',
                              'ontologies/sbol-owl3/sbolowl3.rdf',
                              'ontologies/sbol-owl/sbol.rdf',
                              'ontologies/paml/paml/paml.ttl',
                              'ontologies/paml/uml/uml.ttl']},
      include_package_data=True,
      install_requires=[
            'rdflib>=5.0',
            'SPARQLWrapper',
            'requests',
            'pyparsing<3'  # See https://github.com/RDFLib/rdflib/issues/1190
      ],
      test_suite='test',
      tests_require=[
            'pycodestyle>=2.6.0'
      ])
