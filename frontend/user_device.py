from functools import total_ordering
import re

@total_ordering
class Version(object):
    def __init__(self, version_major, version_minor, version_revision=None):
        self.version_major = version_major
        self.version_minor = version_minor
        self.version_revision = version_revision

    def __eq__(self, other):
        r1 = self.version_revision
        if r1 is  None:
            r1 = 0
        r2 = other.version_revision
        if r2 is None:
            r2 = 0
        return (self.version_major, self.version_minor, r1) == (other.version_major, other.version_minor, r2)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        r1 = self.version_revision
        if r1 is  None:
            r1 = 0
        r2 = other.version_revision
        if r2 is None:
            r2 = 0
        return (self.version_major, self.version_minor, r1) < (other.version_major, other.version_minor, r2)

    def __str__(self):
        if self.version_revision is None:
            return str(self.version_major) + '.' + str(self.version_minor)
        else:
            return str(self.version_major) + '.' + str(self.version_minor) + '.' + str(self.version_revision)

    def __repr__(self):
        return 'Version(' + repr(self.version_major) + ', ' + repr(self.version_minor) + ', ' + repr(self.version_revision) + ')'


def parse_version(version_str):
    m = re.match(r'(\d+).(\d+).(\d+)', version_str)
    if m:
        return Version(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r'(\d+).(\d+)', version_str)
    if m:
        return Version(int(m.group(1)), int(m.group(2)))
    return None


class UserDevice(object):
    def __init__(self, os, version):
        self.os = os
        self.version = version


def get_device(user_agent_str):
    ua = user_agent_str.lower()

    if ua.find('iphone') > 0:
        return UserDevice('iOS', get_ios_version(user_agent_str))

    if ua.find('android') > 0:
        return UserDevice('Android', get_android_version(user_agent_str))

    return UserDevice('other', None)


def get_ios_version(user_agent_str):
    m = re.search(r'iPhone OS (\d+)_(\d+)_(\d+)', user_agent_str)
    if m:
        return Version(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r'iPhone OS (\d+)_(\d+)', user_agent_str)
    if m:
        return Version(int(m.group(1)), int(m.group(2)))
    return None

def get_android_version(user_agent_str):
    m = re.search(r'Android (\d+)\.(\d+)\.(\d+)', user_agent_str)
    if m:
        return Version(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r'Android (\d+)\.(\d+)', user_agent_str)
    if m:
        return Version(int(m.group(1)), int(m.group(2)))
    return None
