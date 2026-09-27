import array
import struct


class FastWeightFile(object):
    """速度重視の独自バイナリ形式のウェイトファイル

    ファイルの構成:
        [ヘッダ (HEADER_FORMAT)][NAME_SEPARATOR (0x0A) 区切りのインフルエンス名 UTF-8][ウェイト double 配列]

    ヘッダは 頂点数 int32 / maxInfluences int32 / maintainMaxInfluences uint8 / インフルエンス名部分のバイト数 int64。
    ウェイトは頂点ごとに全インフルエンスの値を並べた配列で、MFnSkinCluster.getWeights と同じ並び。
    """
    HEADER_FORMAT = "<iiBq"
    NAME_SEPARATOR = b"\x0a"
    EXTENSION = ".fwt"

    def __init__(self, influences, weights, vertex_count, max_influences, maintain_max_influences):
        """
        Args:
            influences (list[str]): インフルエンス名。weights の列の順番と一致させる
            weights (sequence[float]): 頂点ごとに全インフルエンスの値を並べたウェイト
            vertex_count (int): 頂点数
            max_influences (int): skinCluster の maxInfluences
            maintain_max_influences (bool): skinCluster の maintainMaxInfluences
        """
        self.influences = influences
        self.weights = array.array("d", weights)
        self.vertex_count = vertex_count
        self.max_influences = max_influences
        self.maintain_max_influences = maintain_max_influences

    def write(self, path):
        names = self.NAME_SEPARATOR.join(name.encode("utf-8") for name in self.influences)

        with open(path, "wb") as f:
            f.write(struct.pack(self.HEADER_FORMAT, self.vertex_count, self.max_influences, self.maintain_max_influences, len(names)))
            f.write(names)
            self.weights.tofile(f)

    @classmethod
    def read(cls, path):
        with open(path, "rb") as f:
            vertex_count, max_influences, maintain_max_influences, names_size = struct.unpack(cls.HEADER_FORMAT, f.read(struct.calcsize(cls.HEADER_FORMAT)))
            influences = [name.decode("utf-8") for name in f.read(names_size).split(cls.NAME_SEPARATOR)]
            weights = array.array("d")
            weights.frombytes(f.read())

        return cls(influences, weights, vertex_count, max_influences, bool(maintain_max_influences))
