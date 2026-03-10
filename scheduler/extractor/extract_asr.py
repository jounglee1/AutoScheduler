from typing import List

from scheduler.models import Schedule


class ASRExtractor:
    def extract(self, asr_output: str) -> List[Schedule]:
        """
        Extract schedules from ASR (Automatic Speech Recognition) output.
        :param asr_output: Raw transcribed text from a speech recognition system.
        :return: List of Schedule objects.
        """
        # TODO: implement ASR-specific extraction (handle transcription noise, filler words, etc.)
        raise NotImplementedError
