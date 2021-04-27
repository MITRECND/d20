import pkg_resources

GAME_ENGINE_VERSION_RAW = "0.4.3"
GAME_ENGINE_VERSION = pkg_resources.parse_version(GAME_ENGINE_VERSION_RAW)


def parseVersion(version):
    return pkg_resources.parse_version(version)
