import unittest

import bktest.utils


class UtilsTest(unittest.TestCase):

    def test_signum(self):
        self.assertEqual(bktest.utils.signum(1), 1)
        self.assertEqual(bktest.utils.signum(0), 0)
        self.assertEqual(bktest.utils.signum(-1), -1)

    def test_is_int(self):
        self.assertTrue(bktest.utils.is_int("1"))

        self.assertFalse(bktest.utils.is_int("1.5"))
        self.assertFalse(bktest.utils.is_int("hello"))

    def test_is_float(self):
        self.assertTrue(bktest.utils.is_float("1.5"))
        self.assertTrue(bktest.utils.is_float("1"))

        self.assertFalse(bktest.utils.is_float("hello"))

    def test_is_number(self):
        self.assertTrue(bktest.utils.is_number("1.5"))
        self.assertTrue(bktest.utils.is_number("1"))

        self.assertFalse(bktest.utils.is_number("hello"))

    def test_is_not_blank(self):
        self.assertTrue(bktest.utils.is_blank(None))
        self.assertTrue(bktest.utils.is_blank(""))
        self.assertTrue(bktest.utils.is_blank("   "))

        self.assertFalse(bktest.utils.is_blank("hello"))

    def test_ensure_not_blank(self):
        def case(value: str, property: str, message: str):
            with self.assertRaises(ValueError) as context:
                bktest.utils.ensure_not_blank(value, property)
            
            exception = context.exception
            self.assertEquals(message, str(exception))
        
        case(None, None, "must not be blank")
        case(None, "dummy", "dummy must not be blank")
        case("", None, "must not be blank")
        case("", "dummy", "dummy must not be blank")
        case("   ", None, "must not be blank")
        case("   ", "dummy", "dummy must not be blank")

        self.assertEqual("hello", bktest.utils.ensure_not_blank("hello"))
