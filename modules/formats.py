from modules.misc import MyEnum

class FileFormat(MyEnum):
    x3GP = MyEnum.auto()
    AC3 = MyEnum.auto()
    AMR = MyEnum.auto()
    AVI = MyEnum.auto()
    CHA = MyEnum.auto()
    DTS = MyEnum.auto()
    EAC3 = MyEnum.auto()
    FLAC = MyEnum.auto()
    FLV = MyEnum.auto()
    M4A = MyEnum.auto()
    M4V = MyEnum.auto()
    MKV = MyEnum.auto()
    MOV = MyEnum.auto()
    MP2 = MyEnum.auto()
    MP3 = MyEnum.auto()
    MP4 = MyEnum.auto()
    MPG = MyEnum.auto()
    OGG = MyEnum.auto()
    RM = MyEnum.auto()
    SMK = MyEnum.auto()
    SRT = MyEnum.auto()
    SSA = MyEnum.auto()
    SUP = MyEnum.auto()
    TS = MyEnum.auto()
    VOB = MyEnum.auto()
    WAV = MyEnum.auto()
    WEBM = MyEnum.auto()
    WMV = MyEnum.auto()

class TrackType(MyEnum):
    AUD = MyEnum.auto()
    VID = MyEnum.auto()
    SUB = MyEnum.auto()
    CHA = MyEnum.auto()


FILE_FORMAT_SUPPORTED_TRACK_TYPES = {
    FileFormat.AC3: {TrackType.AUD},
    FileFormat.AMR: {TrackType.AUD},
    FileFormat.AVI: {TrackType.VID, TrackType.AUD},
    FileFormat.CHA: {TrackType.CHA},
    FileFormat.DTS: {TrackType.AUD},
    FileFormat.EAC3: {TrackType.AUD},
    FileFormat.FLAC: {TrackType.AUD},
    FileFormat.FLV: {TrackType.VID, TrackType.AUD},
    FileFormat.M4A: {TrackType.AUD},
    FileFormat.M4V: {TrackType.VID, TrackType.AUD, TrackType.SUB},
    FileFormat.MKV: {TrackType.VID, TrackType.AUD, TrackType.SUB},
    FileFormat.MOV: {TrackType.VID, TrackType.AUD, TrackType.SUB},
    FileFormat.MP2: {TrackType.AUD},
    FileFormat.MP3: {TrackType.AUD},
    FileFormat.MP4: {TrackType.VID, TrackType.AUD, TrackType.SUB},
    FileFormat.MPG: {TrackType.VID, TrackType.AUD, TrackType.SUB},
    FileFormat.OGG: {TrackType.VID, TrackType.AUD, TrackType.SUB},
    FileFormat.RM: {TrackType.VID, TrackType.AUD},
    FileFormat.SMK: {TrackType.VID, TrackType.AUD},
    FileFormat.SRT: {TrackType.SUB},
    FileFormat.SSA: {TrackType.SUB},
    FileFormat.SUP: {TrackType.SUB},
    FileFormat.TS: {TrackType.VID, TrackType.AUD, TrackType.SUB},
    FileFormat.VOB: {TrackType.VID, TrackType.AUD, TrackType.SUB},
    FileFormat.WAV: {TrackType.AUD},
    FileFormat.WEBM: {TrackType.VID, TrackType.AUD},
    FileFormat.WMV: {TrackType.VID, TrackType.AUD, TrackType.SUB},
    FileFormat.x3GP: {TrackType.VID, TrackType.AUD},
}

FILE_FORMAT_FILENAME_WILDCARDS = {
    '*.3gp': FileFormat.x3GP,
    '*.ac3': FileFormat.AC3,
    '*.amr': FileFormat.AMR,
    '*.asf': FileFormat.WMV,
    '*.ass': FileFormat.SSA,
    '*.avi': FileFormat.AVI,
    '*.dts': FileFormat.DTS,
    '*.eac3': FileFormat.EAC3,
    '*.flac': FileFormat.FLAC,
    '*.flv': FileFormat.FLV,
    '*.m4a': FileFormat.M4A,
    '*.m4v': FileFormat.M4V,
    '*.mkv': FileFormat.MKV,
    '*.mov': FileFormat.MOV,
    '*.mp2': FileFormat.MP2,
    '*.mp3': FileFormat.MP3,
    '*.mp4': FileFormat.MP4,
    '*.mpeg': FileFormat.MPG,
    '*.mpg': FileFormat.MPG,
    '*.ogg': FileFormat.OGG,
    '*.ogv': FileFormat.OGG,
    '*.opus': FileFormat.OGG,
    '*.ra': FileFormat.RM,
    '*.rm': FileFormat.RM,
    '*.rmvb': FileFormat.RM,
    '*.smk': FileFormat.SMK,
    '*.srt': FileFormat.SRT,
    '*.ssa': FileFormat.SSA,
    '*.sup': FileFormat.SUP,
    '*.ts': FileFormat.TS,
    '*.vob': FileFormat.VOB,
    '*.wav': FileFormat.WAV,
    '*.webm': FileFormat.WEBM,
    '*.wma': FileFormat.WMV,
    '*.wmv': FileFormat.WMV,
    '*chapters*.txt': FileFormat.CHA,
    '*chapters*.xml': FileFormat.CHA,
}

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
    SMK = MyEnum.auto()
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
    PAL8 = MyEnum.auto()
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
    SMK = MyEnum.auto()
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
