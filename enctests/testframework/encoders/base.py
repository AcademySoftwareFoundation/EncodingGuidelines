import pathlib
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
