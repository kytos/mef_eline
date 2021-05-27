"""Setup script.

Run "python3 setup.py --help-commands" to list all available commands and their
descriptions.
"""
import os
import shutil
import sys
from abc import abstractmethod
from pathlib import Path
from subprocess import CalledProcessError, call, check_call

from setuptools import Command, setup
from setuptools.command.develop import develop
from setuptools.command.egg_info import egg_info
from setuptools.command.install import install

if 'bdist_wheel' in sys.argv:
    raise RuntimeError("This setup.py does not support wheels")

# Paths setup with virtualenv detection
BASE_ENV = Path(os.environ.get('VIRTUAL_ENV', '/'))

NAPP_NAME = 'mef_eline'
NAPP_VERSION = '2.5.1'

# Kytos var folder
VAR_PATH = BASE_ENV / 'var' / 'lib' / 'kytos'
# Path for enabled NApps
ENABLED_PATH = VAR_PATH / 'napps'
# Path to install NApps
INSTALLED_PATH = VAR_PATH / 'napps' / '.installed'
CURRENT_DIR = Path('.').resolve()

# NApps enabled by default
CORE_NAPPS = ['of_core']


class SimpleCommand(Command):
    """Make Command implementation simpler."""

    user_options = []

    @abstractmethod
    def run(self):
        """Run when command is invoked.

        Use *call* instead of *check_call* to ignore failures.
        """

    def initialize_options(self):
        """Set default values for options."""

    def finalize_options(self):
        """Post-process options."""


# pylint: disable=attribute-defined-outside-init, abstract-method
class TestCommand(Command):
    """Test tags decorators."""

    user_options = [
        ('size=', None, 'Specify the size of tests to be executed.'),
        ('type=', None, 'Specify the type of tests to be executed.'),
    ]

    sizes = ('small', 'medium', 'large', 'all')
    types = ('unit', 'integration', 'e2e')

    def get_args(self):
        """Return args to be used in test command."""
        return '--size %s --type %s' % (self.size, self.type)

    def initialize_options(self):
        """Set default size and type args."""
        self.size = 'all'
        self.type = 'unit'

    def finalize_options(self):
        """Post-process."""
        try:
            assert self.size in self.sizes, ('ERROR: Invalid size:'
                                             f':{self.size}')
            assert self.type in self.types, ('ERROR: Invalid type:'
                                             f':{self.type}')
        except AssertionError as exc:
            print(exc)
            sys.exit(-1)


class Cleaner(SimpleCommand):
    """Custom clean command to tidy up the project root."""

    description = 'clean build, dist, pyc and egg from package and docs'

    def run(self):
        """Clean build, dist, pyc and egg from package and docs."""
        call('rm -vrf ./build ./dist ./*.egg-info', shell=True)
        call('find . -name __pycache__ -type d | xargs rm -rf', shell=True)
        call('make -C docs/ clean', shell=True)


class Test(TestCommand):
    """Run all tests."""

    description = 'run tests and display results'

    def get_args(self):
        """Return args to be used in test command."""
        markers = self.size
        if markers == "small":
            markers = 'not medium and not large'
        size_args = "" if self.size == "all" else "-m '%s'" % markers
        return '--addopts="tests/%s %s"' % (self.type, size_args)

    def run(self):
        """Run tests."""
        cmd = 'python setup.py pytest %s' % self.get_args()
        try:
            check_call(cmd, shell=True)
        except CalledProcessError as exc:
            print(exc)
            print('Unit tests failed. Fix the errors above and try again.')
            sys.exit(-1)


class TestCoverage(Test):
    """Display test coverage."""

    description = 'run tests and display code coverage'

    def run(self):
        """Run tests quietly and display coverage report."""
        cmd = 'coverage3 run setup.py pytest %s' % self.get_args()
        cmd += '&& coverage3 report'
        try:
            check_call(cmd, shell=True)
        except CalledProcessError as exc:
            print(exc)
            print('Coverage tests failed. Fix the errors above and try again.')
            sys.exit(-1)


class Linter(SimpleCommand):
    """Code linters."""

    description = 'lint Python source code'

    def run(self):
        """Run Yala."""
        print('Yala is running. It may take several seconds...')
        try:
            cmd = 'yala *.py tests'
            check_call(cmd, shell=True)
            print('No linter error found.')
        except CalledProcessError:
            print('Linter check failed. Fix the error(s) above and try again.')
            sys.exit(-1)


class CITest(TestCommand):
    """Run all CI tests."""

    description = 'run all CI tests: unit and doc tests, linter'

    def run(self):
        """Run unit tests with coverage, doc tests and linter."""
        coverage_cmd = 'python3.6 setup.py coverage %s' % self.get_args()
        lint_cmd = 'python3.6 setup.py lint'
        cmd = '%s && %s' % (coverage_cmd, lint_cmd)
        check_call(cmd, shell=True)


class KytosInstall:
    """Common code for all install types."""

    @staticmethod
    def enable_core_napps():
        """Enable a NAPP by creating a symlink."""
        (ENABLED_PATH / 'kytos').mkdir(parents=True, exist_ok=True)
        for napp in CORE_NAPPS:
            napp_path = Path('kytos', napp)
            src = ENABLED_PATH / napp_path
            dst = INSTALLED_PATH / napp_path
            symlink_if_different(src, dst)


class InstallMode(install):
    """Create files in var/lib/kytos."""

    description = 'To install NApps, use kytos-utils. Devs, see "develop".'

    def run(self):
        """Direct users to use kytos-utils to install NApps."""
        print(self.description)


class EggInfo(egg_info):
    """Prepare files to be packed."""

    def run(self):
        """Build css."""
        self._install_deps_wheels()
        super().run()

    @staticmethod
    def _install_deps_wheels():
        """Python wheels are much faster (no compiling)."""
        print('Installing dependencies...')
        check_call([sys.executable, '-m', 'pip', 'install', '-r',
                    'requirements/run.in'])


class DevelopMode(develop):
    """Recommended setup for kytos-napps developers.

    Instead of copying the files to the expected directories, a symlink is
    created on the system aiming the current source code.
    """

    description = 'Install NApps in development mode'

    def run(self):
        """Install the package in a developer mode."""
        super().run()
        if self.uninstall:
            shutil.rmtree(str(ENABLED_PATH), ignore_errors=True)
        else:
            self._create_folder_symlinks()
            # self._create_file_symlinks()
            KytosInstall.enable_core_napps()

    @staticmethod
    def _create_folder_symlinks():
        """Symlink to all Kytos NApps folders.

        ./napps/kytos/napp_name will generate a link in
        var/lib/kytos/napps/.installed/kytos/napp_name.
        """
        links = INSTALLED_PATH / 'kytos'
        links.mkdir(parents=True, exist_ok=True)
        code = CURRENT_DIR
        src = links / NAPP_NAME
        symlink_if_different(src, code)

        (ENABLED_PATH / 'kytos').mkdir(parents=True, exist_ok=True)
        dst = ENABLED_PATH / Path('kytos', NAPP_NAME)
        symlink_if_different(dst, src)

    @staticmethod
    def _create_file_symlinks():
        """Symlink to required files."""
        src = ENABLED_PATH / '__init__.py'
        dst = CURRENT_DIR / 'napps' / '__init__.py'
        symlink_if_different(src, dst)


def symlink_if_different(path, target):
    """Force symlink creation if it points anywhere else."""
    # print(f"symlinking {path} to target: {target}...", end=" ")
    if not path.exists():
        # print(f"path doesn't exist. linking...")
        path.symlink_to(target)
    elif not path.samefile(target):
        # print(f"path exists, but is different. removing and linking...")
        # Exists but points to a different file, so let's replace it
        path.unlink()
        path.symlink_to(target)


setup(name=f'kytos_{NAPP_NAME}',
      version=NAPP_VERSION,
      description='Core NApps developed by Kytos Team',
      url='http://github.com/kytos/{NAPP_NAME}',
      author='Kytos Team',
      author_email='of-ng-dev@ncc.unesp.br',
      license='MIT',
      install_requires=['setuptools >= 36.0.1'],
      setup_requires=['pytest-runner'],
      tests_require=['pytest'],
      extras_require={
          'dev': [
              'coverage',
              'pip-tools',
              'yala',
              'tox',
          ],
      },
      cmdclass={
          'clean': Cleaner,
          'ci': CITest,
          'coverage': TestCoverage,
          'develop': DevelopMode,
          'install': InstallMode,
          'lint': Linter,
          'egg_info': EggInfo,
          'test': Test,
      },
      zip_safe=False,
      classifiers=[
          'License :: OSI Approved :: MIT License',
          'Operating System :: POSIX :: Linux',
          'Programming Language :: Python :: 3.6',
          'Topic :: System :: Networking',
      ])
