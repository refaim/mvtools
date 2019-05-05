# coding: utf-8

from abc import ABCMeta, abstractmethod

from media import File
from formats import AudioCodec, VideoCodec


# TODO телевизор на КЗ
# TODO телевизор на кухне на КЗ
# TODO телевизор LG, который уехал на ГРН

# TODO h264/h265 profiles/levels

class Device:
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_supported_containers(self):
        pass

    def get_supported_video_codecs(self, container):
        if container not in self.get_supported_containers():
            return {}
        return self._safe_get_supported_video_codecs(container)

    @abstractmethod
    def _safe_get_supported_video_codecs(self, container):
        pass

    def get_max_video_resolution(self, container, codec):
        if codec not in self.get_supported_video_codecs(container):
            return None
        return self._safe_get_max_video_resolution(container, codec)

    @abstractmethod
    def _safe_get_max_video_resolution(self, container, codec):
        pass

    def get_max_video_fps(self, container, codec, width, height):
        max_resolution = self.get_max_video_resolution(container, codec)
        if max_resolution is None:
            return None
        max_width, max_height = max_resolution
        if width > max_width or height > max_height or width * height > max_width * max_height:
            return None
        return self._safe_get_max_video_fps(container, codec, width, height)

    @abstractmethod
    def _safe_get_max_video_fps(self, container, codec, width, height):
        pass

    def get_max_video_mbps(self, container, codec):
        if codec not in self.get_supported_video_codecs(container):
            return None
        return self._safe_get_max_video_mbps(container, codec)

    @abstractmethod
    def _safe_get_max_video_mbps(self, container, codec):
        pass

    def get_supported_audio_codecs(self, container):
        if container not in self.get_supported_containers():
            return {}
        return self._safe_get_supported_audio_codecs(container)

    @abstractmethod
    def _safe_get_supported_audio_codecs(self, container):
        pass

    @abstractmethod
    def get_max_audio_kbps(self, codec):
        pass

    def get_max_audio_channels_num(self, container, codec):
        if codec not in self.get_supported_audio_codecs(container):
            return None

    @abstractmethod
    def _safe_get_max_audio_channels_num(self, container, codec):
        pass

    def get_supported_subtitle_codecs(self, container):
        if container not in self.get_supported_containers():
            return {}
        return self._safe_get_supported_subtitle_codecs(container)

    @abstractmethod
    def _safe_get_supported_subtitle_codecs(self, container):
        pass

# TODO H.264 video, Baseline Profile up to Level 3.0
# TODO MPEG-4 video, Simple Profile
class IpodNano4G(Device):
    def get_supported_containers(self):
        return {File.FORMAT_M4V, File.FORMAT_MOV, File.FORMAT_MP4}

    def _safe_get_supported_video_codecs(self, container):
        return {VideoCodec.H264, VideoCodec.MPEG4}

    def _safe_get_max_video_resolution(self, container, codec):
        return 320, 240

    def _safe_get_max_video_fps(self, container, codec, width, height):
        return 30

    def _safe_get_max_video_mbps(self, container, codec):
        return 2.5

    def _safe_get_supported_audio_codecs(self, container):
        return {AudioCodec.AAC_LC}

    def _safe_get_max_audio_channels_num(self, container, codec):
        return 2

    def get_max_audio_kbps(self, codec):
        if codec == AudioCodec.AAC_LC:
            return 160
        return None

    def _safe_get_supported_subtitle_codecs(self, container):
        return {}

class IpodNano4GWithExternalDisplay(IpodNano4G):
    def _safe_get_max_video_resolution(self, container, codec):
        return 640, 480

class SamsungSMP601(Device):
    def get_supported_containers(self):
        return {File.FORMAT_3GP, File.FORMAT_AVI, File.FORMAT_FLV, File.FORMAT_M4V, File.FORMAT_MKV, File.FORMAT_MP4, File.FORMAT_WEBM, File.FORMAT_WMV}

    def _safe_get_supported_video_codecs(self, container):
        return {VideoCodec.FLV1, VideoCodec.H263, VideoCodec.H264, VideoCodec.MPEG4, VideoCodec.MSMPEG4V3, VideoCodec.VC1, VideoCodec.WMV1_WMV7, VideoCodec.WMV2_WMV8}

    def _safe_get_max_video_resolution(self, container, codec):
        return 1920, 1080

    def _safe_get_max_video_fps(self, container, codec, width, height):
        return 30

    # TODO 3GA, OGA, WAV, WMA, AWB, MIDI, XMF, MXMF, IMY, RTTTL, RTX, OTA
    def _safe_get_supported_audio_codecs(self, container):
        return {AudioCodec.AAC_LC, AudioCodec.AMR, AudioCodec.FLAC, AudioCodec.MP3, AudioCodec.VORBIS}

    def get_max_audio_kbps(self, codec):
        return None

    def _safe_get_max_audio_channels_num(self, container, codec):
        return 2

    # TODO really?
    def _safe_get_supported_subtitle_codecs(self, container):
        return {}

class Honor8(Device):
    def get_supported_containers(self):
        return {File.FORMAT_3GP, File.FORMAT_MP4, File.FORMAT_RM, File.FORMAT_WMV}

    def _safe_get_supported_video_codecs(self, container):
        return {VideoCodec.H263, VideoCodec.H264, VideoCodec.H265, VideoCodec.MPEG4, VideoCodec.VP8}

    def _safe_get_max_video_resolution(self, container, codec):
        return 1920, 1080

    def _safe_get_max_video_fps(self, container, codec, width, height):
        return 30

    def _safe_get_supported_audio_codecs(self, container):
        # TODO PCM
        return {AudioCodec.AAC_LC, AudioCodec.AAC_HE, AudioCodec.AAC_HE_V2, AudioCodec.AMR, AudioCodec.MP3}

    def get_max_audio_kbps(self, codec):
        return None

    def _safe_get_max_audio_channels_num(self, container, codec):
        return 2

    def _safe_get_supported_subtitle_codecs(self, container):
        return {}

    # TODO other formats (???) mp3, mid, amr, 3gp, mp4, m4a, aac, wav, ogg, flac, mkv
    # TODO max resolution for vr

class SamsungTvUE48H6200AK(Device):
    # TODO mvc
    _HD_ONLY_CODECS = {VideoCodec.H263, VideoCodec.MJPEG, VideoCodec.MSMPEG4V1, VideoCodec.MSMPEG4V2, VideoCodec.MSMPEG4V3, VideoCodec.VP6, VideoCodec.WMV1_WMV7, VideoCodec.WMV2_WMV8}

    def get_supported_containers(self):
        # TODO *.vro, *.tp, *.trp, *.svi, *.m2tsm *.mts, *.divx
        return {File.FORMAT_3GP, File.FORMAT_AVI, File.FORMAT_FLV, File.FORMAT_MKV, File.FORMAT_MP4, File.FORMAT_MOV, File.FORMAT_MPG, File.FORMAT_TS, File.FORMAT_WEBM, File.FORMAT_WMV}

    # TODO Supports up to H.264, Level 4.1
    # TODO VC1 AP L4 is not supported
    # TODO GMC 2 or above is not supported.
    # TODO This can only support the BD MVC specifications.
    # TODO what h.265 profile is supported?
    def _safe_get_supported_video_codecs(self, container):
        if container == File.FORMAT_WEBM:
            return {VideoCodec.VP8}
        # TODO DivX 3.11 / 4 / 5 / 6, MVC
        result = {VideoCodec.H263, VideoCodec.H264, VideoCodec.MJPEG, VideoCodec.MPEG1, VideoCodec.MPEG2, VideoCodec.MSMPEG4V1, VideoCodec.MSMPEG4V2, VideoCodec.MSMPEG4V3, VideoCodec.VC1, VideoCodec.VP6, VideoCodec.WMV1_WMV7, VideoCodec.WMV2_WMV8, VideoCodec.WMV3_WMV9}
        if container in [File.FORMAT_MKV, File.FORMAT_MP4, File.FORMAT_TS]:
            result.add(VideoCodec.H265)
        return result

    def _safe_get_max_video_resolution(self, container, codec):
        if codec in self._HD_ONLY_CODECS:
            return 1280, 720
        return 1920, 1080

    def _safe_get_max_video_fps(self, container, codec, width, height):
        if codec in self._HD_ONLY_CODECS:
            return 30
        return 30  # TODO 30 for FHD, 60 for HD

    def _safe_get_max_video_mbps(self, container, codec):
        if container == File.FORMAT_WEBM:
            return 20
        return 30

    # TODO WMA is supported up to 10 Pro 5.1 channels.
    # TODO WMA Supports up to the M2 profile.
    # TODO WMA lossless audio is not supported
    # TODO The DTS LBR codec is only available for MKV / MP4 / TS containers.
    # TODO ape in *.ape
    # TODO AIFF in *.aif/*.aiff
    # TODO ALAC in *.m4a
    def _safe_get_supported_audio_codecs(self, container):
        if container == File.FORMAT_WEBM:
            return {AudioCodec.VORBIS}
        # TODO LPCM, WMA, DTS(Core, LBR), G.711(A-Law)
        return {AudioCodec.AAC_LC, AudioCodec.AAC_HE, AudioCodec.AC3, AudioCodec.ADPCM_IMA, AudioCodec.ADPCM_MS, AudioCodec.EAC3, AudioCodec.MP3, AudioCodec.PCM_MULAW}

    def _safe_get_max_audio_channels_num(self, container, codec):
        if codec in {AudioCodec.FLAC, AudioCodec.VORBIS}:
            return 2
        return 6

    def get_max_audio_kbps(self, codec):
        return None
