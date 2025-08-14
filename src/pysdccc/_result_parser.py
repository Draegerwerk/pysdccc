"""Parser for the JUnit XML test results provided by SDCcc including custom elements.

This module provides classes to parse and handle JUnit XML test results with custom elements specific to SDCcc.
It includes custom elements for test identifiers and descriptions, as well as custom test case and test suite classes.

Classes
-------

TestIdentifierElement
    Represents the test identifier element in the JUnit XML.
TestDescriptionElement
    Represents the test description element in the JUnit XML.
TestCase
    Represents a test case with custom elements.
TestSuite
    Represents a test suite with custom test cases.

Usage
-----

.. code-block:: python

    from result_parser import TestSuite

    # Parse a test suite from a file
    test_suite = TestSuite.from_file("path/to/test_results.xml")

    # Iterate over test cases in the test suite
    for test_case in test_suite:
        print(test_case.test_identifier)
        print(test_case.test_description)
"""

from collections.abc import Iterator

import anyio.to_thread
from junitparser import junitparser

from pysdccc import _common


class TestIdentifierElement(junitparser.Element):
    """Element containing the test identifier.

    This class represents a custom XML element for the test identifier in the JUnit XML test results.
    It extends the `junitparser.Element` class and provides a property to access the text content of the element.
    """

    __test__ = False
    _tag = 'test-identifier'

    @property
    def text(self) -> str | None:
        """Retrieve the text content of the XML element.

        :return: The text content of the XML element, or None if the element has no text.
        """
        return self._elem.text


class TestDescriptionElement(junitparser.Element):
    """Element containing the test description.

    This class represents a custom XML element for the test description in the JUnit XML test results.
    It extends the `junitparser.Element` class and provides a property to access the text content of the element.
    """

    __test__ = False
    _tag = 'test-description'

    @property
    def text(self) -> str | None:
        """Retrieve the text content of the XML element.

        :return: The text content of the XML element, or None if the element has no text.
        """
        return self._elem.text


class TestCase(junitparser.TestCase):
    """Test case containing custom elements.

    This class extends the `junitparser.TestCase` class to include custom elements such as test identifier and test
    description. It provides properties to access these custom elements.
    """

    @property
    def test_identifier(self) -> str | None:
        """Links a test case with a unique test identifier.

        :return: The unique identifier for the test case.
        """
        elem = self.child(TestIdentifierElement)
        return elem.text if elem is not None else None

    @property
    def test_description(self) -> str | None:
        """Description of the test case itself, i.e. what is tested and how.

        :return: The description of the test case.
        """
        elem = self.child(TestDescriptionElement)
        return elem.text if elem is not None else None


class TestSuite(junitparser.TestSuite):
    """Test suite containing custom test cases.

    This class extends the `junitparser.TestSuite` class to include custom test cases with additional elements.
    It provides methods to iterate over the test cases and parse a test suite from a file.
    """

    def __iter__(self) -> Iterator[TestCase]:
        for elem in super().__iter__():
            test_case = TestCase.fromelem(elem)
            if test_case is not None:
                yield test_case

    @classmethod
    async def from_file(cls, file: _common.PATH_TYPE) -> 'TestSuite':
        """Parse a test suite from a given file.

        This method reads a JUnit XML file and parses it into a `TestSuite` object containing custom elements.

        :param file: The path to the test suite file to be parsed.
        :return: A `TestSuite` object containing the parsed test cases with custom elements.
        :raises ValueError: If the parsed file does not contain a `TestSuite` object.
        :raises FileNotFoundError: If the file does not exist.
        :raises TypeError: If the content of the xml is not a TestSuite.
        """
        suite_xml = await anyio.to_thread.run_sync(junitparser.JUnitXml.fromfile, str(file))
        suite = next(iter(suite_xml), None)
        if not isinstance(suite, junitparser.TestSuite):
            msg = f'Expected class {junitparser.TestSuite}, got {type(suite)}'
            raise TypeError(msg)
        result = cls.fromelem(suite)
        if result is None:
            msg = f'Failed to parse TestSuite from {file}.'
            raise ValueError(msg)
        return result
