from setuptools import setup

setup(name='Owlet',
      version='1.0a',
      description='Automatically generates Python symbols for ontology terms',
      python_requires='>=3.6',
      url='https://github.com/SynBioDex/Owlet',
      author='Bryan Bartley',
      author_email='bartleyba@sbolstandard.org',
      license='Apache-2',
      # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
            # How mature is this project? Common values are
            #   3 - Alpha
            #   4 - Beta
            #   5 - Production/Stable
            'Development Status :: 3 - Alpha',

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
      packages=['Owlet'],
      package_data={'Owlet': ['ontologies/*.owl',
                              'ontologies/*.rdf',
                              'ontologies/*.ttl']},
      include_package_data=True,
      install_requires=[
            'rdflib>=5.0',
            'SPARQLWrapper'
      ],
      test_suite='test',
      tests_require=[
            'pycodestyle>=2.6.0'
      ])
