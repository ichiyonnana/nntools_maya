"""Photoshopでシェイプを生成する関数群｡

Examples:
def rp(): return random.randint(0, 1000)

subpaths = []
for _ in range(20):
    points = [(rp(), rp()), (rp(), rp()), (rp(), rp()), (rp(), rp())]
    subpaths.append(SubPath([Point(x, y) for x, y in points]))

shape = Shape(subpaths)
create_shape_with_photoshop([shape])

"""
import subprocess
import tempfile


class Point:
    """2次元座標点を表すクラス。

    Args:
        x (float): X座標
        y (float): Y座標
    """
    def __init__(self, x, y):
        self.x = x
        self.y = y


class SubPath:
    """サブパス（連続した点列）を表すクラス。

    Args:
        points (list[Point]): サブパスを構成する点のリスト
    """
    def __init__(self, points):
        self.points = points


class Shape:
    """複数のサブパスからなるシェイプを表すクラス。

    Args:
        subpaths (list[SubPath]): シェイプを構成するサブパスのリスト
    """
    def __init__(self, subpaths):
        self.subpaths = subpaths


def make_points_block(points):
    """Pointオブジェクトのリストから、JSX用のpoints.push文を生成する。

    Args:
        points (list[Point]): 点のリスト
    Returns:
        str: JSXコード断片
    """
    points_block = ""
    for point in points:
        points_block += f"points.push(xy({point.x},{point.y}));\n"
    return points_block


def make_subpaths_block(subpaths):
    """サブパスリストから、JSXでサブパスを定義するコード断片を生成する。

    Args:
        subpaths (list[SubPath]): サブパスのリスト
    Returns:
        str: JSXコード断片
    """
    subpaths_block = "// サブパスの作成\n"
    for subpath in subpaths:
        points_block = make_points_block(subpath.points)
        subpaths_block += "    points = [];\n"
        subpaths_block += points_block
        subpaths_block += r"""
        // サブパス情報の追加
        subPathInfo = new SubPathInfo();
        subPathInfo.operation = ShapeOperation.SHAPEADD;
        subPathInfo.closed = true;
        subPathInfo.entireSubPath = points;
        subPaths.push(subPathInfo);
        """

    return subpaths_block


def make_jsx_code(shapes):
    """Shapeオブジェクト群からPhotoshop用のJSXコードを生成する。

    Args:
        shapes (list[Shape]): シェイプのリスト
    Returns:
        str: JSXコード全体
    """
    jsx_code = r"""
        function xy(x, y){
            var pObj = new PathPointInfo(); // パス情報オブジェクトを作成
            pObj.kind = PointKind.CORNERPOINT;
            pObj.anchor = [x, y];   // アンカー座標
            pObj.leftDirection = [x, y];    // 左ハンドル部分のパス座標
            pObj.rightDirection = [x, y];   // 右ハンドル部分のパス座標
            return pObj;
        }

        var doc = app.activeDocument;
        var activeLayer = doc.activeLayer;
    """

    for shape in shapes:
        subpaths = shape.subpaths
        subpaths_block = make_subpaths_block(subpaths)
        jsx_code += r"""
        // シェイプを描画するパスを定義
        var pathName = "testpath";
        var points = [];
        var subPaths = [];
        """
        jsx_code += subpaths_block
        jsx_code += r"""
        // サブパスを一つのパスとして追加
        app.activeDocument.pathItems.add(pathName, subPaths);

        var d = new ActionDescriptor();
        var d2 = new ActionDescriptor();
        var d3 = new ActionDescriptor();
        var d4 = new ActionDescriptor();
        var r = new ActionReference();

        r.putClass( stringIDToTypeID( "contentLayer" ));
        d.putReference( charIDToTypeID( "null" ), r );
        d4.putDouble( charIDToTypeID( "Rd  " ), 255);
        d4.putDouble( charIDToTypeID( "Grn " ), 255);
        d4.putDouble( charIDToTypeID( "Bl  " ), 255);
        d3.putObject( charIDToTypeID( "Clr " ), charIDToTypeID( "RGBC" ), d4 );
        d2.putObject( charIDToTypeID( "Type" ), stringIDToTypeID( "solidColorLayer" ), d3 );
        d.putObject( charIDToTypeID( "Usng" ), stringIDToTypeID( "contentLayer" ), d2 );
        executeAction( charIDToTypeID( "Mk  " ), d, DialogModes.NO );

        app.activeDocument.pathItems.getByName(pathName).remove()
        """

    return jsx_code


def create_shape_with_photoshop(shapes):
    """
    Photoshopを自動操作してシェイプを生成・描画する。

    Args:
        shapes (list[Shape]): 描画するシェイプのリスト

    Returns:
        str: 実行したJSXファイルのパス

    Examples:
        >>> points = [Point(0, 0), Point(100, 0), Point(100, 100), Point(0, 100)]
        >>> subpath = SubPath(points)
        >>> shape = Shape([subpath])
        >>> create_shape_with_photoshop([shape])
    """
    # 実行中の Photoshop のパスを取得
    encoding = "sjis"
    cmd = """wmic process where "name = 'Photoshop.exe'" get commandline"""
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)

    if result:
        ps_path = result.stdout.decode(encoding).split("\r\r\n")[1].replace('"', '')

    else:
        raise

    # jsx コードを生成し一時ファイル経由で実行
    jsx_code = make_jsx_code(shapes)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsx", delete=False, encoding="utf-8") as tmp:
        tmp.write(jsx_code)
        jsx_path = tmp.name

    cmd = f'"{ps_path}" -r "{jsx_path}"'
    subprocess.run(cmd)

    return jsx_path
