import unittest

import numpy
import pandas


def assertDataFramesEqual(self: unittest.TestCase, first: pandas.DataFrame, second: pandas.DataFrame) -> bool:
    for index, column in enumerate(first.columns):
        self.assertEqual(first.dtypes.iloc[index], second.dtypes.iloc[index], "type mismatch between dataframes")
        
        self.assertTrue((first[column].isna() == second[column].isna()).all(), "not all NaN are equal")

        if (
            pandas.api.types.is_integer_dtype(first[column])
            or pandas.api.types.is_string_dtype(first[column])
            or pandas.api.types.is_bool_dtype(first[column])
        ):
            self.assertTrue((first[~first[column].isna()][column] == second[~second[column].isna()][column]).all(), "not all non-NaN are equal in comparing int/string/bool")

        elif pandas.api.types.is_float_dtype(first[column]):
            self.assertTrue(numpy.allclose(first[~first[column].isna()][column], second[~second[column].isna()][column]), "not all non-NaN are equal in comparing float")

        else:
            self.fail(f"Column {column} is of an unknown type: {first[column].dtype}")
