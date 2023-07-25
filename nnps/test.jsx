
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

// シェイプを描画するパスを定義
var pathName = "testpath";
var points = [];
var subPaths = [];
points.push(xy(0,0), xy(100, 0), xy(100,100), xy(0,100));
subPaths[0] = new SubPathInfo();
subPaths[0].operation = ShapeOperation.SHAPEADD;
subPaths[0].closed = true;
subPaths[0].entireSubPath = points;

var points = [];
points.push(xy(100,0), xy(200, 0), xy(200,100), xy(100,100));
subPaths[1] = new SubPathInfo();
subPaths[1].operation = ShapeOperation.SHAPEADD;
subPaths[1].closed = true;
subPaths[1].entireSubPath = points;

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