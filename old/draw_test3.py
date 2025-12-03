import igraph as ig
import plotly.graph_objs as go
import random

def main():
    # ---------------------------------------------------------
    # 1. シミュレーション設定
    # ---------------------------------------------------------
    frames = []      # アニメーションの「コマ」を格納するリスト
    steps = 50       # 何ステップ（コマ）描画するか
    
    # 最初に空のグラフを作成
    G = ig.Graph(directed=False)

    print("シミュレーションとフレーム生成を開始します...")

    # ---------------------------------------------------------
    # 2. ループ処理：グラフを変化させながらフレームを作る
    # ---------------------------------------------------------
    for step in range(steps):
        # --- A. グラフ構造の動的な変更 ---
        # 新しいノードを1つ追加
        G.add_vertices(1)
        new_node_idx = G.vcount() - 1
        
        # 既存のノードがあれば、ランダムにエッジを結ぶ（成長）
        if new_node_idx > 0:
            # 接続先の候補（自分以外）
            targets = list(range(new_node_idx))
            # ランダムに1〜2本のエッジを引く
            num_edges = min(len(targets), random.randint(1, 2))
            chosen_targets = random.sample(targets, num_edges)
            for t in chosen_targets:
                G.add_edges([(new_node_idx, t)])

        # --- B. レイアウト（座標）の再計算 ---
        # ノードが増えるたびに形が変わるため、毎回計算する
        # dim=3 で3次元座標を取得
        if G.vcount() > 0:
            layt = G.layout('kk', dim=3) # kk: Kamada-Kawai法
            
            # 座標データの抽出
            N = G.vcount()
            Xn = [layt[k][0] for k in range(N)]
            Yn = [layt[k][1] for k in range(N)]
            Zn = [layt[k][2] for k in range(N)]
            
            # エッジの座標データの作成（Noneで区切る手法）
            Xe, Ye, Ze = [], [], []
            for e in G.get_edgelist():
                Xe += [layt[e[0]][0], layt[e[1]][0], None]
                Ye += [layt[e[0]][1], layt[e[1]][1], None]
                Ze += [layt[e[0]][2], layt[e[1]][2], None]
        else:
            Xn, Yn, Zn = [], [], []
            Xe, Ye, Ze = [], [], []

        # --- C. フレーム（1コマ）の作成 ---
        # この瞬間のエッジ(trace1)とノード(trace2)の状態を記録
        frames.append(go.Frame(
            data=[
                go.Scatter3d(x=Xe, y=Ye, z=Ze), # エッジの更新
                go.Scatter3d(x=Xn, y=Yn, z=Zn,  # ノードの更新
                             marker=dict(color=list(range(N)), colorscale='Viridis')) 
            ],
            name=f'frame_{step}' # フレームに名前をつける
        ))

    print(f"{steps} ステップのフレーム生成完了。描画準備中...")

    # ---------------------------------------------------------
    # 3. 初期状態の描画データ作成（最初のフレームと同じでOK）
    # ---------------------------------------------------------
    # 空の状態からスタートするためのプレースホルダー
    initial_trace_edges = go.Scatter3d(
        x=[], y=[], z=[],
        mode='lines',
        line=dict(color='rgb(125,125,125)', width=1),
        name='edges'
    )
    initial_trace_nodes = go.Scatter3d(
        x=[], y=[], z=[],
        mode='markers',
        marker=dict(symbol='circle', size=6, colorscale='Viridis'),
        name='nodes'
    )

    # ---------------------------------------------------------
    # 4. アニメーション設定とFigure作成
    # ---------------------------------------------------------
    fig = go.Figure(
        data=[initial_trace_edges, initial_trace_nodes],
        frames=frames # ここで作ったフレームを渡す
    )

    # レイアウト設定（再生ボタンや軸の固定）
    fig.update_layout(
        title="Growing Network Animation (3D)",
        width=1000, height=800,
        scene=dict(
            # カメラがブレないように軸の範囲を少し広めに固定（適宜調整）
            xaxis=dict(range=[-3, 3], autorange=False),
            yaxis=dict(range=[-3, 3], autorange=False),
            zaxis=dict(range=[-3, 3], autorange=False),
            aspectmode='cube'
        ),
        # アニメーション制御ボタン（再生・一時停止）
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            buttons=[dict(
                label="Play",
                method="animate",
                args=[None, dict(
                    frame=dict(duration=1000, redraw=True), # 1コマ1000ms
                    fromcurrent=True,
                    transition=dict(duration=50) # 50msかけて滑らかに移動
                )]
            )]
        )]
    )

    fig.show()

if __name__ == "__main__":
    main()
