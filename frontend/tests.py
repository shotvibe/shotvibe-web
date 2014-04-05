"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase

from frontend.user_device import Version, get_device, get_ios_version, get_android_version

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)


class UserDeviceTest(TestCase):
    def test_version_cmp(self):
        self.assertEqual(Version(1, 0, 0), Version(1, 0, 0))

        self.assertNotEqual(Version(1, 0, 0), Version(1, 1, 0))

        self.assertLess(Version(1, 0, 0), Version(1, 0, 1))
        self.assertLess(Version(1, 9, 9), Version(2, 0, 0))
        self.assertLess(Version(1, 1, 1), Version(2, 0))

        self.assertGreater(Version(1, 0, 1), Version(1, 0, 0))
        self.assertGreater(Version(2, 0, 0), Version(1, 9, 9))
        self.assertGreater(Version(2, 0), Version(1, 1, 1))

    def test_ios_version(self):
        self.assertEqual(get_ios_version("Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_1 like Mac OS X; en-us) AppleWebKit/532.9 (KHTML, like Gecko) Version/4.0.5 Mobile/8B117 Safari/6531.22.7"), Version(4, 1))
        self.assertEqual(get_ios_version("Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_3_1 like Mac OS X; he-il) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8G4 Safari/6533.18.5"), Version(4, 3, 1))
        self.assertEqual(get_ios_version("Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_3_2 like Mac OS X; he-il) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8H7 Safari/6533.18.5"), Version(4, 3, 2))
        self.assertEqual(get_ios_version("Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_3_3 like Mac OS X; he-il) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8J2 Safari/6533.18.5"), Version(4, 3, 3))
        self.assertEqual(get_ios_version("Mozilla/5.0 (iPhone; CPU iPhone OS 5_0_1 like Mac OS X) AppleWebKit/534.46 (KHTML, like Gecko) Version/5.1 Mobile/9A406 Safari/7534.48.3"), Version(5, 0, 1))
        self.assertEqual(get_ios_version("Mozilla/5.0 (iPhone; CPU iPhone OS 5_1 like Mac OS X) AppleWebKit/534.46 (KHTML, like Gecko) Version/5.1 Mobile/9B176 Safari/7534.48.3"), Version(5, 1))
        self.assertEqual(get_ios_version("Mozilla/5.0 (iPhone; CPU iPhone OS 5_1_1 like Mac OS X) AppleWebKit/534.46 (KHTML, like Gecko) Version/5.1 Mobile/9B206 Safari/7534.48.3"), Version(5, 1, 1))
        self.assertEqual(get_ios_version("Mozilla/5.0 (iPod; CPU iPhone OS 6_0_1 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Mobile/10A523"), Version(6, 0, 1))
        self.assertEqual(get_ios_version("Mozilla/5.0 (iPhone; CPU iPhone OS 6_1_3 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10B329 Safari/8536.25"), Version(6, 1, 3))
        self.assertEqual(get_ios_version("Mozilla/5.0 (iPhone; CPU iPhone OS 6_1_4 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10B350 Safari/8536.25"), Version(6, 1, 4))
        self.assertEqual(get_ios_version("Mozilla/5.0 (iPhone; CPU iPhone OS 7_0 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11A465 Safari/9537.53"),Version(7, 0))
        self.assertEqual(get_ios_version("Mozilla/5.0 (iPhone; CPU iPhone OS 7_0_3 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11B511 Safari/9537.53"), Version(7, 0, 3))
        self.assertEqual(get_ios_version("Mozilla/5.0 (iPhone; CPU iPhone OS 7_0_4 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) CriOS/33.0.1750.21 Mobile/11B554a Safari/9537.53"), Version(7, 0, 4))
        self.assertEqual(get_ios_version("Mozilla/5.0 (iPhone; CPU iPhone OS 7_0_5 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11B601 Safari/9537.53"), Version(7, 0, 5))
        self.assertEqual(get_ios_version("Mozilla/5.0 (iPhone; CPU iPhone OS 7_0_6 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11B651 Safari/9537.53"), Version(7, 0, 6))
        self.assertEqual(get_ios_version("Mozilla/5.0 (iPhone; CPU iPhone OS 7_1 like Mac OS X) AppleWebKit/537.51.2 (KHTML, like Gecko) Version/7.0 Mobile/11D167 Safari/9537.53"), Version(7, 1))

    def test_android_version(self):
        self.assertEqual(get_android_version("Mozilla/5.0 (Linux; U; Android 2.2; he-il; GT-I9000 Build/FROYO) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1"), Version(2, 2))
        self.assertEqual(get_android_version("Mozilla/5.0 (Linux; U; Android 2.3.3; ru-ru; GT-I9100T Build/GINGERBREAD) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1"), Version(2, 3, 3))
        self.assertEqual(get_android_version("Mozilla/5.0 (Linux; U; Android 2.3.4; iw-il; LG-P690f Build/GRJ22) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1 MMS/LG-Android-MMS-V1.0/1.2"), Version(2, 3, 4))
        self.assertEqual(get_android_version("Mozilla/5.0 (Linux; U; Android 2.3.5; he-il; GT-I9100 Build/GINGERBREAD) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1"), Version(2, 3, 5))
        self.assertEqual(get_android_version("Mozilla/5.0 (Linux; U; Android 2.3.6; iw-il; GT-S5360T Build/GINGERBREAD) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1"), Version(2, 3, 6))
        self.assertEqual(get_android_version("Mozilla/5.0 (Linux; U; Android 2.3.7; iw-il; SonyEricssonST25a Build/6.0.B.3.184) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1"), Version(2, 3, 7))
        self.assertEqual(get_android_version("Mozilla/5.0 (Linux; U; Android 4.0.3; he-il; GT-I9100 Build/IML74K) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30"), Version(4, 0, 3))
        self.assertEqual(get_android_version("Mozilla/5.0 (Linux; Android 4.0.3; GT-I9100 Build/IML74K) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.166 Mobile Safari/535.19"), Version(4, 0, 3))
        self.assertEqual(get_android_version("Mozilla/5.0 (Linux; U; Android 4.0.4; he-il; GT-I9100 Build/IMM76D) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30"), Version(4, 0, 4))
        self.assertEqual(get_android_version("Mozilla/5.0 (Linux; U; Android 4.1.2; en-us; GT-I8190 Build/JZO54K) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30"), Version(4, 1, 2))
        self.assertEqual(get_android_version("Mozilla/5.0 (Linux; Android 4.1.2; GT-I9300 Build/JZO54K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1700.99 Mobile Safari/537.36"), Version(4, 1, 2))
        self.assertEqual(get_android_version("Mozilla/5.0 (Linux; Android 4.2.1; ZP980 Build/JOP40D) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.136 Mobile Safari/537.36"), Version(4, 2, 1))
        self.assertEqual(get_android_version("Mozilla/5.0 (Linux; Android 4.2.2; GT-I9500 Build/JDQ39) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.59 Mobile Safari/537.36"), Version(4, 2, 2))
        self.assertEqual(get_android_version("Mozilla/5.0 (Linux; U; Android 4.3; he-il; GT-I9300 Build/JSS15J) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30"), Version(4, 3))
        self.assertEqual(get_android_version("Mozilla/5.0 (Linux; Android 4.4.2; Nexus 5 Build/KOT49H) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1700.99 Mobile Safari/537.36"), Version(4, 4, 2))
