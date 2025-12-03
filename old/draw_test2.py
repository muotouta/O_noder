import json
import urllib.request
import igraph as ig
import plotly.graph_objs as go
import os

def main():
    # ファイルのURLと保存するローカルファイル名
    url = "https://raw.githubusercontent.com/plotly/datasets/master/miserables.json"
    local_filename = "miserables.json"

    # ---------------------------------------------------------
    # 1. データをダウンロードしてローカルファイルに保存
    # ---------------------------------------------------------
    print(f"データをダウンロード中... ({url})")
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            raw_data = response.read()
            
        # データをローカルファイルに書き込み
        with open(local_filename, 'wb') as f:
            f.write(raw_data)
            
        print(f"保存完了: データを '{local_filename}' として保存しました。")
        
    except Exception as e:
        print(f"ダウンロードに失敗しました: {e}")
        return

    # ---------------------------------------------------------
    # 2. ローカルファイルからデータを読み込み
    # ---------------------------------------------------------
    print(f"ローカルファイル '{local_filename}' を読み込んでいます...")
    
    if not os.path.exists(local_filename):
        print(f"エラー: ファイル '{local_filename}' が見つかりません。")
        return

    with open(local_filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"type: {type(data)}")
    print()
    print(data)
    print()

    # ---------------------------------------------------------
    # 3. グラフデータの構築 (igraph)
    # ---------------------------------------------------------
    # ノード数（登場人物の数）
    
    N = len(data['nodes'])
    print(f"ノード数: {N}")

    # エッジ（関係性）のリスト化
    L = len(data['links'])
    Edges = [(data['links'][k]['source'], data['links'][k]['target']) for k in range(L)]
    
    # igraphのグラフオブジェクト生成
    G = ig.Graph(Edges, directed=False)

    # ノードの属性（名前とグループ）を取得
    labels = []
    group = []
    for node in data['nodes']:
        labels.append(node['name'])
        group.append(node['group'])

    # ---------------------------------------------------------
    # 4. グラフレイアウトの計算 (3D)
    # ---------------------------------------------------------
    print("レイアウトを計算中 (Kamada-Kawai)...")
    layt = G.layout('kk', dim=3)

    # ノードの座標リスト作成
    Xn = [layt[k][0] for k in range(N)]
    Yn = [layt[k][1] for k in range(N)]
    Zn = [layt[k][2] for k in range(N)]

    # エッジの座標リスト作成
    Xe = []
    Ye = []
    Ze = []
    for e in Edges:
        Xe += [layt[e[0]][0], layt[e[1]][0], None]
        Ye += [layt[e[0]][1], layt[e[1]][1], None]
        Ze += [layt[e[0]][2], layt[e[1]][2], None]

    # ---------------------------------------------------------
    # 5. Plotlyによるグラフ描画設定
    # ---------------------------------------------------------
    print("グラフを生成中...")

    # エッジ（線）の描画設定
    trace1 = go.Scatter3d(
        x=Xe, y=Ye, z=Ze,
        mode='lines',
        line=dict(color='rgb(125,125,125)', width=1),
        hoverinfo='none'
    )

    # ノード（点）の描画設定
    trace2 = go.Scatter3d(
        x=Xn, y=Yn, z=Zn,
        mode='markers',
        name='actors',
        marker=dict(
            symbol='circle',
            size=6,
            color=group,
            colorscale='Viridis',
            line=dict(color='rgb(50,50,50)', width=0.5)
        ),
        text=labels,
        hoverinfo='text'
    )

    # 軸の設定
    axis = dict(
        showbackground=False,
        showline=False,
        zeroline=False,
        showgrid=False,
        showticklabels=False,
        title=''
    )

    # 全体のレイアウト設定
    layout = go.Layout(
        title="Network of co-appearances of characters in Victor Hugo's novel<br> Les Miserables (3D visualization)",
        width=1000,
        height=1000,
        showlegend=False,
        scene=dict(
            xaxis=dict(axis),
            yaxis=dict(axis),
            zaxis=dict(axis),
        ),
        margin=dict(t=100),
        hovermode='closest',
        annotations=[
            dict(
                showarrow=False,
                text="Data source: [1] miserables.json (Local File)",
                xref='paper',
                yref='paper',
                x=0,
                y=0.1,
                xanchor='left',
                yanchor='bottom',
                font=dict(size=14)
            )
        ]
    )

    # Figureオブジェクトの作成
    data_traces = [trace1, trace2]
    fig = go.Figure(data=data_traces, layout=layout)

    # ---------------------------------------------------------
    # 6. グラフの表示
    # ---------------------------------------------------------
    print("ブラウザで表示します...")
    fig.show()

if __name__ == "__main__":
    main()
