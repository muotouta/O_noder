import json
import os
import webbrowser
import sys
import time
import threading
from http.server import SimpleHTTPRequestHandler
import socketserver

# ---------------------------------------------------------
# 設定
# ---------------------------------------------------------
JSON_FILENAME = 'miserables.json'
HTML_FILENAME = 'network_3d_images_spaced.html' # ファイル名を変更
PORT = 8000

def main():
    # 1. データ読み込み
    if not os.path.exists(JSON_FILENAME):
        print(f"エラー: '{JSON_FILENAME}' が見つかりません。")
        return

    with open(JSON_FILENAME, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 2. HTML生成
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ margin: 0; overflow: hidden; background-color: #000; }}
    #graph-container {{ width: 100vw; height: 100vh; }}
  </style>
  
  <script src="https://unpkg.com/d3@7"></script>
  <script src="https://unpkg.com/three@0.160.0/build/three.min.js"></script>
  <script src="https://unpkg.com/3d-force-graph@1.73.1/dist/3d-force-graph.min.js"></script>
</head>
<body>
  <div id="graph-container"></div>

  <script>
    const gData = {json.dumps(data)};
    
    // 画像読み込み設定
    const textureLoader = new THREE.TextureLoader();
    textureLoader.crossOrigin = "Anonymous";

    // グラフ初期化
    const Graph = ForceGraph3D()
      (document.getElementById('graph-container'))
      .graphData(gData)
      .backgroundColor('#000000')
      
      // --- 【調整1】 画像の設定 ---
      .nodeThreeObject(node => {{
        const imgUrl = `https://robohash.org/${{node.name}}.png?set=set1&size=150x150`;
        
        const map = textureLoader.load(imgUrl, (t)=>t, undefined, (e)=>console.log(e));
        const material = new THREE.SpriteMaterial({{ map: map }});
        const sprite = new THREE.Sprite(material);
        
        // サイズを少し小さくして重なりを軽減 (前回は10+でしたが、8+に変更)
        const size = 8 + (node.group || 0) * 0.5; 
        sprite.scale.set(size, size, 1);
        
        return sprite;
      }})
      
      // エッジの設定
      .linkWidth(0.5)
      .linkOpacity(0.5)
      .linkColor(() => '#aaaaaa')
      .nodeLabel('name')

      // --- 【調整2】 物理演算パラメータ（ここが重要） ---
      // 1. 電荷（Charge）: ノード同士の反発力を強くする（マイナス値を大きくする）
      .d3Force('charge', d3.forceManyBody().strength(-200))
      // 2. リンク（Link）: つながっているノード間の距離を広げる
      .d3Force('link', d3.forceLink().distance(60).id(d => d.id));

    // 自動回転の設定
    const controls = Graph.controls();
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.8;

    window.addEventListener('resize', () => {{
        Graph.width(window.innerWidth);
        Graph.height(window.innerHeight);
    }});
  </script>
</body>
</html>
    """

    with open(HTML_FILENAME, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"HTMLファイルを作成しました: {HTML_FILENAME}")

    # 3. サーバー起動とブラウザ表示
    def start_server():
        # ポートが使われている場合に備えて再利用設定
        class ReusableTCPServer(socketserver.TCPServer):
            allow_reuse_address = True
            
        with ReusableTCPServer(("", PORT), SimpleHTTPRequestHandler) as httpd:
            print(f"サーバーを起動しました: http://localhost:{PORT}")
            httpd.serve_forever()

    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()

    time.sleep(1)
    url = f"http://localhost:{PORT}/{HTML_FILENAME}"
    webbrowser.open(url)

    print("\nCtrl+C を押すとサーバーを停止して終了します...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n終了します。")
        sys.exit(0)

if __name__ == "__main__":
    main()
