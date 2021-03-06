# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import csv
import six
from itertools import chain
from codecs import iterencode
from ..parser import Parser
from .. import helpers
from .. import config


# Module API

class CSVParser(Parser):
    """Parser to parse CSV data format.
    """

    # Public

    options = [
        'delimiter',
        'doublequote',
        'escapechar',
        'quotechar',
        'quoting',
        'skipinitialspace',
        'lineterminator'
    ]

    def __init__(self, loader, **options):

        # Make bytes
        if six.PY2:
            for key, value in options.items():
                if isinstance(value, six.string_types):
                    options[key] = str(value)

        # Set attributes
        self.__loader = loader
        self.__options = options
        self.__force_parse = None
        self.__extended_rows = None
        self.__chars = None

    @property
    def closed(self):
        return self.__chars is None or self.__chars.closed

    def open(self, source, encoding=None, force_parse=False):
        self.close()
        self.__force_parse = force_parse
        self.__chars = self.__loader.load(source, encoding=encoding)
        self.reset()

    def close(self):
        if not self.closed:
            self.__chars.close()

    def reset(self):
        helpers.reset_stream(self.__chars)
        self.__extended_rows = self.__iter_extended_rows()

    @property
    def extended_rows(self):
        return self.__extended_rows

    # Private

    def __iter_extended_rows(self):

        # For PY2 encode/decode
        if six.PY2:
            # Reader requires utf-8 encoded stream
            bytes = iterencode(self.__chars, 'utf-8')
            sample, dialect = self.__prepare_dialect(bytes)
            items = csv.reader(chain(sample, bytes), dialect=dialect)
            for row_number, item in enumerate(items, start=1):
                values = []
                for value in item:
                    value = value.decode('utf-8')
                    values.append(value)
                yield (row_number, None, list(values))

        # For PY3 use chars
        else:
            sample, dialect = self.__prepare_dialect(self.__chars)
            items = csv.reader(chain(sample, self.__chars), dialect=dialect)
            for row_number, item in enumerate(items, start=1):
                yield (row_number, None, list(item))

    def __prepare_dialect(self, stream):

        # Get sample
        sample = []
        while True:
            try:
                sample.append(next(stream))
            except StopIteration:
                break
            if len(sample) >= config.CSV_SAMPLE_LINES:
                break

        # Get dialect
        try:
            separator = b'' if six.PY2 else ''
            delimiter = self.__options.get('delimiter', ',\t;|')
            dialect = csv.Sniffer().sniff(separator.join(sample), delimiter)
            if not dialect.escapechar:
                dialect.doublequote = True
        except csv.Error:
            dialect = csv.excel
        for key, value in self.__options.items():
            setattr(dialect, key, value)

        return sample, dialect
