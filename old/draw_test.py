import json
import urllib.request
import igraph as ig
import plotly.graph_objs as go

def main():
    # ---------------------------------------------------------
    # 1. データの取得と準備
    # ---------------------------------------------------------
    print("データを取得中...")
    url = "https://raw.githubusercontent.com/plotly/datasets/master/miserables.json"
    req = urllib.request.Request(url)
    opener = urllib.request.build_opener()
    
    with opener.open(req) as f:
        data = json.loads(f.read().decode('utf-8'))
    
    print(data)

    # ノード数（登場人物の数）
    N = len(data['nodes'])
    print(f"ノード数: {N}")

    # エッジ（関係性）のリスト化とグラフ生成
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
    # 2. グラフレイアウトの計算 (3D)
    # ---------------------------------------------------------
    print("レイアウトを計算中...")
    # 'kk' は Kamada-Kawai アルゴリズム
    layt = G.layout('kk', dim=3)

    # ノードの座標リスト作成
    Xn = [layt[k][0] for k in range(N)]
    Yn = [layt[k][1] for k in range(N)]
    Zn = [layt[k][2] for k in range(N)]

    # エッジの座標リスト作成
    # Plotlyで線を引くため、始点・終点・None（区切り）の順で配列を作る
    Xe = []
    Ye = []
    Ze = []
    for e in Edges:
        Xe += [layt[e[0]][0], layt[e[1]][0], None]
        Ye += [layt[e[0]][1], layt[e[1]][1], None]
        Ze += [layt[e[0]][2], layt[e[1]][2], None]

    # ---------------------------------------------------------
    # 3. Plotlyによるグラフ描画設定
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

    # 軸の設定（背景やグリッドを消してシンプルにする）
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
                text="Data source: <a href='http://bost.ocks.org/mike/miserables/miserables.json'>[1] miserables.json</a>",
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
    # 4. グラフの表示
    # ---------------------------------------------------------
    print("ブラウザで表示します...")
    fig.show()

if __name__ == "__main__":
    main()
