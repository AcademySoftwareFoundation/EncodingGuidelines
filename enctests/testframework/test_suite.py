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
        self._config = {}
        self._config_path = None
        self.parse_config_file(test_config_file)

    def dictcopy(self):
        return deepcopy(self._config)

    def parse_config_file(self, path: pathlib.Path):
        self._config_path = path
        path = path.absolute().as_posix()
        self._config = {}
        with open(path, 'rt') as f:
            self._config = list(yaml.load_all(f, SafeLoader))
        return self._config
    
    def config_file(self):
        """Return the path to the config file that was read in."""
        return self._config_path
<<<<<<< HEAD
=======

>>>>>>> fb3f021 (Cleanup of class variables.)
            
    def __getattr__(self, name: str) -> Any:
        return self._config[name]

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
        self._image_directly = False
        super(SourceConfig, self).__init__(test_config_file)

    def parse_config_file(self, path: pathlib.Path):
        if path.suffix not in [".yml", ".yaml"]:
            self._config = {'images': False,
<<<<<<< HEAD
                               'path': path.as_posix(), #Dont want it as a pathLib here, since this can end up referenced in otio
=======
                               'path': path,
>>>>>>> fb3f021 (Cleanup of class variables.)
                               'in': 0,
                               'duration': 1,
                               'rate': 25}
            self._image_directly = True
            return self._config
        self._config = super(SourceConfig, self).parse_config_file(path)[0]
        return self._config
    
    def path(self):
        """Get the path to the imagery"""
        if self._image_directly:
            return pathlib.Path(self._config['path'])
        # We convert to pathlib.Path class here, since SourceConfig will typically be getting the path from a yml config,
        # but to be consistent, we want to use the resulting path as a Path class object.
        p = pathlib.Path(self._config["path"])
        if not p.is_absolute():
            p = self.config_file().parent.joinpath(p).resolve()
        return p
            
    def __getattr__(self, name: str) -> Any:
        if name == "path":
            return self.path()
        return self._config[name]
    
class TestConfig:
    """
    This is tracking an individual test within a config file.
    There could be still be multiple wedges within this test config.
    """
    def __init__(self, test_name: str, test_dict: dict, test_config: str):
        self._name = test_name
        self._config_path = test_config
        self._test_dict = test_dict
    
    def sources(self):
        sources = self._test_dict.get('sources', [])
        return [SourceConfig(pathlib.Path(path)) for path in sources]
    
    def __getattr__(self, name: str) -> Any:
        return self._test_dict[name]
    
    def get(self, key, default=None):
        try:
            return self.__getattr__(key)
        except KeyError:
            return default
    
    def set_destination(self, destination: pathlib.Path):
        """Record where we are writing out the test results to."""
        self._test_dict['destination'] = destination

    def config_file(self):
        return self._config_path
    
class TestSuite(BaseYamlConfig):
    """
    This is the main testSuite config.
    """
    def __init__(self,
                 test_config_file: pathlib.Path):
        self.test_configs = []
        self._report = None
        self._tests = None
        self._destination = None
        self._config = {}
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
                    self._config[test_name] = test_config
    
        self._tests = test_configs
        self._report = report
    
    def tests(self):
        return self._tests

    def sources(self):
        """Return all the sources in this testSuite"""
        sources = [tst.sources() for tst in self.test_configs]
        return sources
    
    def report(self):
        return self._report

    def __getattr__(self, name: str) -> Any:
        if name == "destination":
            return self._destination
        if name == "app":
            # We are going to grab the app from the first test
            return self.tests()[0].get("app")
        return self._config[name]
    
    def set_destination(self, destination: pathlib.Path):
        self._destination = destination

