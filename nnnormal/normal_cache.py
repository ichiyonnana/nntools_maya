# coding:utf-8
import nnutil.decorator as deco


class NormalCache():
    """シェイプの法線をキャッシュし、コマンドやAPIによる取得・設定をを一度で済ませるためのクラス
    """
    def __init__(self, shape):
        """コンストラクタ。shape の法線を保持する

        Args:
            shape (Mesh): 法線をキャッシュするシェイプ
        """
        self.shape = shape
        self.original_normals = shape.getNormals()
        self.original_ids = shape.getNormalIds()
        self.normals = []  # self.normals[face_index][vf_index] で法線を取得できる

        vertexface_counts = self.original_ids[0]
        vertexface_normal_ids = self.original_ids[1]

        for vertex_count in vertexface_counts:
            normal_ids = vertexface_normal_ids[0:vertex_count]
            vertexface_normal_ids = vertexface_normal_ids[vertex_count:]
            normals_per_face = [self.original_normals[id] for id in normal_ids]

            self.normals.append(normals_per_face)

    def _get_vertexface_normal(self, vertex_face):
        """指定した VertexFace の法線を取得する。クラス内部で使用する関数

        Args:
            vertex_face (MeshVertexFace): 法線を取得する VertexFace

        Returns:
            FloatVector: VertexFace の法線
        """
        v_index = vertex_face.indices()[0][0]
        f_index = vertex_face.indices()[0][1]
        vf_index = list(self.shape.f[f_index].getVertices()).index(v_index)

        return self.normals[f_index][vf_index]

        # normal_index = shape.face[f_index].normalIndex(vf_index)
        # return self.original_normals[normal_index]

    def get_vertexface_normals(self, vertex_faces):
        """指定した VertexFace の法線を取得しリストで返す

        Args:
            vertex_face (list[MeshVertexFace]): 法線を取得する VertexFace のリスト

        Returns:
            list[FloatVector]: VertexFace の法線のリスト
        """
        return [self._get_vertexface_normal(vf) for vf in vertex_faces]

    def get_vertexface_normal(self, vertex_face):
        """指定した VertexFace の法線を取得する

        Args:
            vertex_face (MeshVertexFace): 法線を取得する VertexFace

        Returns:
            FloatVector: VertexFace の法線
        """
        return self._get_vertexface_normal(vertex_face)

    def _set_vertexface_normal(self, vertex_face, normal):
        """指定した VertexFace の法線を設定する。クラス内部で使用する関数

        Args:
            vertex_face (MeshVertexFace): 法線を設定する VertexFace
            normals (FloatVector): 設定する法線
        """
        v_index = vertex_face.indices()[0][0]
        f_index = vertex_face.indices()[0][1]
        vf_index = list(self.shape.f[f_index].getVertices()).index(v_index)

        self.normals[f_index][vf_index] = normal

    def set_vertexface_normal(self, vertex_face, normal):
        """指定した VertexFace の法線を設定する。クラス内部で使用する関数

        Args:
            vertex_face (MeshVertexFace): 法線を設定する VertexFace
            normal (FloatVector): 設定する法線
        """
        self._set_vertexface_normal(vertex_face, normal)

    def set_vertexface_normals(self, vertex_faces, normals):
        """指定した VertexFace の法線を設定する

        vertex_faces と normals の要素数が一致しない場合は例外 (Exception) を発生させる

        Args:
            vertex_face (list[MeshVertexFace]): 法線を設定する VertexFace のリスト
            normals (list[FloatVector]): 設定する法線のリスト
        """
        if len(vertex_faces) != len(normals):
            raise(Exception("引数の頂点フェースとノーマルの数が一致していません"))

        for i in len(vertex_faces):
            self._set_vertexface_normal(vertex_faces[i], normals[i])

    @deco.timer
    def update_normals(self):
        """クラス内部で変更した法線を元のシェイプに反映する
        """
        flatten_vector = [vector for vector_list in self.normals for vector in vector_list]
        self.shape.setNormals(flatten_vector)
        self.shape.updateSurface()
