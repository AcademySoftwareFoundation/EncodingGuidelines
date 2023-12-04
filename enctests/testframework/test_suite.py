import os
import sys
import time
import shlex
import yaml
import pathlib
from copy import deepcopy
from typing import Any

try:
    from yaml import CSafeLoader as SafeLoader
    from yaml import CSafeDumper as SafeDumper

except ImportError:
    from yaml import SafeLoader, SafeDumper

"""
A test of classes to help manage loading and querying the test suites and the associated source content.
"""

# Test config files
from .utils import (
    create_clip,
    get_media_info,
    get_source_path,
    get_nearest_model,
    get_test_metadata_dict,
    get_source_metadata_dict
)


class BaseYamlConfig:
    """
    Base class for reading the yaml file in, and storing the location of the file.
    """
    def __init__(self,
                 test_config_file: pathlib.Path):
        self.__config__ = {}
        self.__config_path = None
        self.parse_config_file(test_config_file)

    def dictcopy(self):
        return deepcopy(self.__config__)

    def parse_config_file(self, path: pathlib.Path):
        self.__config_path = path
        path = path.absolute().as_posix()
        self.__config__ = {}
        with open(path, 'rt') as f:
            self.__config__ = list(yaml.load_all(f, SafeLoader))
        return self.__config__
    
    def config_file(self):
        """Return the path to the config file that was read in."""
        return self.__config_path

            
    def __getattr__(self, __name: str) -> Any:
        return self.__config__[__name]

    def get(self, key, default=None):
        return self.__getattr__(key)

class SourceConfig(BaseYamlConfig):
    """
    Used for storing the data structure of the source config file.
    This is a little different to the BaseYamlConfig, since we assume the parameters are all on the
    top level of the yaml file.
    """
    def __init__(self,
                 test_config_file: pathlib.Path):
        self.__image_directly = False
        super(SourceConfig, self).__init__(test_config_file)

    def parse_config_file(self, path: pathlib.Path):
        if path.suffix in [".png", ".dpx", ".tif"]:
            self.__config__ = {'images': False,
                               'path': path.as_posix(),
                               'in': 0,
                               'duration': 1,
                               'rate': 25}
            self.__image_directly = True
            return
        self.__config__ = super(SourceConfig, self).parse_config_file(path)[0]

    def path(self):
        """Get the path to the imagery"""
        if self.__image_directly:
            return pathlib.Path(self.__config__['path'])
        p = pathlib.Path(self.__config__["path"])
        if not p.is_absolute():
            p = self.config_file().parent.joinpath(p).resolve()
        return p
            
    def __getattr__(self, __name: str) -> Any:
        if __name == "path":
            return self.path()
        return self.__config__[__name]
    
class TestConfig:
    """
    This is tracking an individual test within a config file.
    There could be still be multiple wedges within this test config.
    """
    def __init__(self, test_name: str, test_dict: dict, test_config: str):
        self.__name = test_name
        self.__config_path = test_config
        self.__test_dict = test_dict
    
    def sources(self):
        sources = self.__test_dict.get('sources', [])
        return [SourceConfig(pathlib.Path(path)) for path in sources]
    
    def __getattr__(self, __name: str) -> Any:
        return self.__test_dict[__name]
    
    def get(self, key, default=None):
        try:
            return self.__getattr__(key)
        except KeyError:
            return default
    
    def set_destination(self, destination: pathlib.Path):
        """Record where we are writing out the test results to."""
        self.__test_dict['destination'] = destination

    def config_file(self):
        return self.__config_path
    
class TestSuite(BaseYamlConfig):
    """
    This is the main testSuite config.
    """
    def __init__(self,
                 test_config_file: pathlib.Path):
        self.test_configs = []
        self.__report = None
        self._tests = None
        self.__destination = None
        self.__config__ = {}
        super(TestSuite, self).__init__(test_config_file)

    def parse_config_file(self, path: pathlib.Path):
        config = super(TestSuite, self).parse_config_file(path)

        test_configs = []
        report = None
        for test_dict in config:
            for test_name, test_config in test_dict.items():
                # Store path to config file for future reference.
                #test_name = next(iter(test_config))
                #print("TEST NAME:", test_name, test_config)
                if test_name == "reports":
                    report = test_config
                    continue
                if test_name.startswith('test_'):
                    # Only store config path for tests
                    test_config['test'] = test_name # TODO Should we warn if it exists, and isnt this?
                    test_config['test_config_path'] = self.config_file()
                    tst = TestConfig(test_name, test_config, self.config_file())
                    test_configs.append(tst)
                else:
                    print(f"Unattached param:{test_name} = {test_config}")
                    self.__config__[test_name] = test_config
    
        self.__tests = test_configs
        self.__report = report
    
    def tests(self):
        return self.__tests

    def sources(self):
        """Return all the sources in this testSuite"""
        sources = [tst.sources() for tst in self.test_configs]
        return sources
    
    def report(self):
        return self.__report

    def __getattr__(self, __name: str) -> Any:
        if __name == "path":
            return self.path()
        if __name == "destination":
            return self.__destination
        if __name == "app":
            # We are going to grab the app from the first test
            return self.tests()[0].get("app")
        return self.__config__[__name]
    
    def set_destination(self, destination: pathlib.Path):
        self.__destination = destination