import os
import json
import random
from flask import Flask, render_template, jsonify
import igraph as ig

app = Flask(__name__)

# JSONファイルのパス
JSON_FILE_PATH = 'data.json'

# --- テスト用データの作成関数（ファイルがない場合のみ実行） ---
def create_dummy_json_if_missing():
    if not os.path.exists(JSON_FILE_PATH):
        # 10個のノードを持つダミーデータを作成
        data = {
            "nodes": [{"id": str(i)} for i in range(10)],
            "edges": []
        }
        # ランダムにつなぐ
        for i in range(10):
            target = random.randint(0, 9)
            if i != target:
                data["edges"].append([str(i), str(target)])
        
        with open(JSON_FILE_PATH, 'w') as f:
            json.dump(data, f)
        print(f"テスト用の {JSON_FILE_PATH} を作成しました。")

# --- データの読み込みと座標計算 ---
def get_graph_data():
    # 1. JSONファイルの読み込み
    try:
        with open(JSON_FILE_PATH, 'r') as f:
            raw_data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON: {e}")
        return {"nodes": [], "links": []}

    # 2. igraphグラフの構築
    n_count = len(raw_data['nodes'])
    # IDからインデックスへのマッピングを作成
    id_map = {node['id']: i for i, node in enumerate(raw_data['nodes'])}
    
    edges = []
    for edge in raw_data['edges']:
        # エッジのIDが存在するか確認してから追加
        if edge[0] in id_map and edge[1] in id_map:
            edges.append((id_map[edge[0]], id_map[edge[1]]))
    
    g = ig.Graph(n_count, edges)
    
    # 3. 3D座標計算 (Kamada-Kawai法)
    layout = g.layout_kamada_kawai_3d()
    coords = layout.coords
    scale = 100 

    # 4. ブラウザ用データの構築
    nodes = []
    for i, node_info in enumerate(raw_data['nodes']):
        nodes.append({
            "id": node_info['id'],
            # 画像ファイル名を指定 (jpgに変更)
            # 画像がない場合は適当に割り振る（img1.jpg, img2.jpg）
            "img": f"img{i % 2 + 1}.jpg", 
            "fx": coords[i][0] * scale,
            "fy": coords[i][1] * scale,
            "fz": coords[i][2] * scale
        })

    links = []
    for edge in raw_data['edges']:
        links.append({"source": edge[0], "target": edge[1]})

    return {"nodes": nodes, "links": links}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def data():
    return jsonify(get_graph_data())

if __name__ == '__main__':
    # 初回起動時にダミーファイル作成
    create_dummy_json_if_missing()
    app.run(host='0.0.0.0', port=5001, debug=True)
