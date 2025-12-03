import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import igraph as ig
import json
import os

# 1. アプリケーションの初期化
app = dash.Dash(__name__)

# JSONファイルのパス
JSON_FILE_PATH = 'miserables.json'

# 2. レイアウトの定義（見た目）
app.layout = html.Div([
    html.H1("3D Real-time Network Graph"),
    
    # グラフ表示エリア
    dcc.Graph(id='network-graph', style={'height': '90vh'}),
    
    # 自動更新用タイマー（ここでは5000ミリ秒 = 5秒ごとに更新）
    dcc.Interval(
        id='interval-component',
        interval=5*1000, 
        n_intervals=0
    )
])

# 3. コールバック関数の定義（定期実行される処理）
@app.callback(
    Output('network-graph', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_graph(n):
    # --- A. JSONデータの読み込み ---
    # ファイルが存在しない場合や読み込み中のエラーハンドリングは適宜必要
    try:
        with open(JSON_FILE_PATH, 'r') as f:
            data = json.load(f)
    except Exception as e:
        # エラー時は空のグラフなどを返す
        return go.Figure()

    # --- B. igraphによるグラフ構築と座標計算 ---
    # JSON構造に合わせてノードとエッジを追加（ここはデータの形による）
    # 例: data = {"nodes": ["A", "B"], "edges": [["A", "B"]]}
    n_count = len(data['nodes'])
    edges = [(data['nodes'].index(src), data['nodes'].index(tgt)) for src, tgt in data['edges']]
    
    g = ig.Graph(n_count, edges)
    
    # 3Dレイアウト計算 (例: Kamada-Kawai法)
    layout = g.layout_kamada_kawai_3d()
    coords = layout.coords # [[x, y, z], ...]

    # --- C. Plotly用のデータ作成 ---
    Xn = [c[0] for c in coords]
    Yn = [c[1] for c in coords]
    Zn = [c[2] for c in coords]

    # ノードの描画設定
    trace_nodes = go.Scatter3d(
        x=Xn, y=Yn, z=Zn,
        mode='markers',
        marker=dict(symbol='circle', size=5, color='blue'),
        text=data['nodes'], # ホバー時に名前を表示
        hoverinfo='text'
    )

    # エッジの描画設定
    Xe, Ye, Ze = [], [], []
    for e in edges:
        Xe += [coords[e[0]][0], coords[e[1]][0], None] # Noneを入れると線が切れる
        Ye += [coords[e[0]][1], coords[e[1]][1], None]
        Ze += [coords[e[0]][2], coords[e[1]][2], None]

    trace_edges = go.Scatter3d(
        x=Xe, y=Ye, z=Ze,
        mode='lines',
        line=dict(color='gray', width=1),
        hoverinfo='none'
    )

    # --- D. グラフオブジェクトの構築と返却 ---
    layout_setting = go.Layout(
        title="Network Visualization",
        showlegend=False,
        scene=dict(
            xaxis=dict(showbackground=False),
            yaxis=dict(showbackground=False),
            zaxis=dict(showbackground=False)
        ),
        margin=dict(t=40, l=0, r=0, b=0)
    )

    return go.Figure(data=[trace_edges, trace_nodes], layout=layout_setting)

# 4. サーバーの起動
if __name__ == '__main__':
    # host='0.0.0.0' にすることで、外部PCからアクセス可能にする
    app.run_server(debug=True, host='0.0.0.0', port=8050)
