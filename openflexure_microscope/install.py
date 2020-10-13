import os

from pynpm import NPMPackage

dir_path = os.path.dirname(os.path.realpath(__file__))
pkg_path = os.path.join(dir_path, "api", "static", "package.json")

pkg = NPMPackage(pkg_path)


def install():
    pkg.install()


def build():
    pkg.install()
    pkg.run_script("build")
