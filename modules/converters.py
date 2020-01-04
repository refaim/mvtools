from abc import ABCMeta, abstractmethod

from modules.formats import FileFormat


class Converter:
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_supported_input_containers(self):
        pass

    def get_supported_input_video_codecs(self, container):
        if container not in self.get_supported_input_containers():
            return {}
        return self._safe_get_supported_input_video_codecs(container)

    @abstractmethod
    def _safe_get_supported_input_video_codecs(self, container):
        pass

    def get_supported_input_audio_codecs(self, container):
        if container not in self.get_supported_input_containers():
            return {}
        return self._safe_get_supported_input_audio_codecs(container)

    @abstractmethod
    def _safe_get_supported_input_audio_codecs(self, container):
        pass

    # def get_supported_subtitle_codecs(self, container):
    #     if container not in self.get_supported_containers():
    #         return {}
    #     return self._safe_get_supported_subtitle_codecs(container)
    #
    # @abstractmethod
    # def _safe_get_supported_subtitle_codecs(self, container):
    #     pass

class AudioConverter(Converter):
    __metaclass__ = ABCMeta

    def _safe_get_supported_input_video_codecs(self, container):
        return {}

class Eac3to(AudioConverter):
    def get_supported_input_containers(self):
        # TODO EVO, M2TS, RAW, (L)PCM, DTS-ES, DTS-96/24, DTS-HD Hi-Res, DTS-HD Master Audio, MP2, AAC, MLP, TrueHD, TrueHD/AC3
        return {
            FileFormat.AC3,
            FileFormat.DTS,  # TODO handle in media.py
            FileFormat.EAC3,
            FileFormat.FLAC,
            FileFormat.MKV,
            FileFormat.MP3,
            FileFormat.VOB,
            FileFormat.WAV,
        }

    def _safe_get_supported_input_audio_codecs(self, container):
        pass

    # def get_supported_input_codecs(self):
    #     # TODO AAC_HE? AAC_HE_V2?
    #     # TODO MP1, RAW, (L)PCM
    #     return {AudioCodec.AAC_LC, AudioCodec.AC3, AudioCodec.DTS, AudioCodec.DTS_ES, AudioCodec.DTS_MA, AudioCodec.EAC3, AudioCodec.FLAC, AudioCodec.MP2, AudioCodec.MP3, AudioCodec.TRUE_HD}

# Supported source formats:
# (1) RAW, (L)PCM
# (2) WAV (PCM, DTS and AC3), W64, RF64
# (3) AC3, E-AC3
# (4) DTS, DTS-ES, DTS-96/24, DTS-HD Hi-Res, DTS-HD Master Audio
# (5) MP1, MP2, MP3 audio
# (6) AAC audio
# (7) MLP, TrueHD, TrueHD/AC3
# (8) FLAC
# (9) EVO/VOB/(M2)TS and MKV
#
# Decoded audio data can be stored as / encoded to:
# (1) RAW, (L)PCM
# (2) WAV (PCM only), W64, RF64, AGM
# (3) WAVs (multiple mono WAV files, PCM only)
# (4) AC3
# (5) DTS
# (6) AAC
# (7) FLAC

# class MkvMerge(Program):
#     def get_supported_output_file_formats(self):
#         return {FileFormat.MKV}
#
# class Qaac(Program):
#     pass