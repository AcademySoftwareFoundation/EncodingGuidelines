import pathlib
from typing import Tuple
from abc import ABC, abstractmethod

import opentimelineio as otio


class ABCTestEncoder(ABC):
    @abstractmethod
    def __init__(
            self,
            source_clip: otio.schema.Clip,
            test_config: dict,
            destination: pathlib.Path
    ):
        self.source_clip = source_clip
        self.test_config = test_config
        self.destination = destination

    @abstractmethod
    def run_wedges(self) -> dict:
        """
        Encode the wedges described in the test configuration.
        Returns a dict containing otio.schema.MediaReferences
        """

    @abstractmethod
    def get_application_version(self) -> str:
        """Return version of encoder application"""

    @abstractmethod
    def prep_encoding_command(self, wedge: dict, out_file: pathlib.Path) -> str:
        """Assemble the command passed to subprocess for encoding"""

    @abstractmethod
    def get_output_filename(self, test_name: str) -> pathlib.Path:
        """Return a filename including test name suffix"""

    @abstractmethod
    def get_source_path(self) -> Tuple[pathlib.Path, str]:
        """
        Get a tuple containing path and frame abstraction based on
        self.source_clip formatted to support encoder syntax
        """
