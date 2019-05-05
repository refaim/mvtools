from modules.misc import MyEnum

class VideoCodec(MyEnum):
    FLV1 = MyEnum.auto()
    H263 = MyEnum.auto()
    H264 = MyEnum.auto()
    H265 = MyEnum.auto()
    MJPEG = MyEnum.auto()
    MPEG1 = MyEnum.auto()
    MPEG2 = MyEnum.auto()
    MPEG4 = MyEnum.auto()
    MSMPEG4V1 = MyEnum.auto()
    MSMPEG4V2 = MyEnum.auto()
    MSMPEG4V3 = MyEnum.auto()
    RV30 = MyEnum.auto()
    RV40 = MyEnum.auto()
    VC1 = MyEnum.auto()
    VP6 = MyEnum.auto()
    VP6F = MyEnum.auto()
    VP8 = MyEnum.auto()
    WMV1_WMV7 = MyEnum.auto()
    WMV2_WMV8 = MyEnum.auto()
    WMV3_WMV9 = MyEnum.auto()

class VideoCodecProfile(MyEnum):
    BASELINE = MyEnum.auto()
    MAIN = MyEnum.auto()
    HIGH = MyEnum.auto()

class VideoCodecLevel(MyEnum):
    L10 = MyEnum.auto()
    L11 = MyEnum.auto()
    L12 = MyEnum.auto()
    L13 = MyEnum.auto()
    L20 = MyEnum.auto()
    L21 = MyEnum.auto()
    L22 = MyEnum.auto()
    L30 = MyEnum.auto()
    L31 = MyEnum.auto()
    L32 = MyEnum.auto()
    L40 = MyEnum.auto()
    L41 = MyEnum.auto()
    L42 = MyEnum.auto()
    L50 = MyEnum.auto()
    L51 = MyEnum.auto()
    L52 = MyEnum.auto()
    L60 = MyEnum.auto()
    L61 = MyEnum.auto()
    L62 = MyEnum.auto()

class VideoFpsStandard(MyEnum):
    DEINTERLACED = MyEnum.auto()
    NTSC = MyEnum.auto()
    PAL = MyEnum.auto()
    PORN = MyEnum.auto()
    WEBCAM = MyEnum.auto()

class ColorRange(MyEnum):
    PC = MyEnum.auto()
    TV = MyEnum.auto()

class ColorSpace(MyEnum):
    BT_601_NTSC = MyEnum.auto()
    BT_601_PAL = MyEnum.auto()
    BT_709 = MyEnum.auto()
    FCC = MyEnum.auto()

class FieldOrder(MyEnum):
    PROGRESSIVE = MyEnum.auto()
    INTERLACED_TOP = MyEnum.auto()
    INTERLACED_BOT = MyEnum.auto()

class PictureFormat(MyEnum):
    YUV420P = MyEnum.auto()
    YUVJ420P = MyEnum.auto()
    YUV420P10LE = MyEnum.auto()

class AudioCodec(MyEnum):
    AAC_HE = MyEnum.auto()  # AAC+
    AAC_HE_V2 = MyEnum.auto()  # eAAC+
    AAC_LC = MyEnum.auto()
    AC3 = MyEnum.auto()
    AMR = MyEnum.auto()
    ASAO = MyEnum.auto()
    COOK = MyEnum.auto()
    DTS = MyEnum.auto()
    DTS_ES = MyEnum.auto()
    DTS_HRA = MyEnum.auto()
    DTS_MA = MyEnum.auto()
    EAC3 = MyEnum.auto()
    FLAC = MyEnum.auto()
    ADPCM_IMA = MyEnum.auto()
    ADPCM_MS = MyEnum.auto()
    ADPCM_SWF = MyEnum.auto()
    MP2 = MyEnum.auto()
    MP3 = MyEnum.auto()
    OPUS = MyEnum.auto()
    PCM_S16L = MyEnum.auto()
    PCM_MULAW = MyEnum.auto()
    SPEEX = MyEnum.auto()
    TRUE_HD = MyEnum.auto()
    VORBIS = MyEnum.auto()
    WMA_PRO = MyEnum.auto()
    WMA_V2 = MyEnum.auto()

class SubtitleCodec(MyEnum):
    ASS = MyEnum.auto()
    MOV = MyEnum.auto()
    PGS = MyEnum.auto()
    SRT = MyEnum.auto()
    VOBSUB = MyEnum.auto()
