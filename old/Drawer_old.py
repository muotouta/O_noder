#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
O_noderにおける、グラフ描画用のコード
"""

__author__ = 'Muto Tao'
__version__ = '0.1.1'
__date__ = '2025.12.2'


import igraph as ig
import plotly.graph_objs as go


class Drawer:
    """
    グラフ描画のためのクラス
    """

    # ハイパーパラメータ
    LAYOUT_ALGORITHM = "kk"

    # データ
    node_data: dict
    edge_data: dict
    img_data: dict
    edges: list
    N: int
    L: int
    labels: list
    group: list

    # グラフの情報
    G: ig
    node_pos = {
        'Xn': list,
        'Yn': list,
        'Zn': list
    }
    edge_pos = {
        'Xe': list,
        'Ye': list,
        'Ze': list
    }
    fig: go


    def __init__(self, graph_data, img_data):
        """
        コンストラクタ
        """

        # グラフのデータを獲得
        self.node_data = graph_data['nodes']
        self.edge_data = graph_data['links']
        self.img_data = img_data
        self.N = len(graph_data['nodes'])
        self.L = len(graph_data['links'])
        self.edges = [(graph_data['links'][k]['source'], graph_data['links'][k]['target']) for k in range(self.L)]
        self.labels = []
        self.group = []
        for node in graph_data['nodes']:
            self.labels.append(node['name'])
            self.group.append(0)

        # グラフオブジェクトの生成
        self.G = ig.Graph(self.edges, directed=False)

        # 描画に向けた設定
        self.calc_layout()  # グラフのレイアウトを計算
        self.initialize_graph()  # グラフの描画設定

    
    def calc_layout(self):
        """
        ノードの座標を計算し、フィールドに保存する関数
        """

        layt = self.G.layout(self.LAYOUT_ALGORITHM, dim=3)

        # ノードの座標リスト作成
        self.node_pos['Xn'] = [layt[k][0] for k in range(self.N)]
        self.node_pos['Yn'] = [layt[k][1] for k in range(self.N)]
        self.node_pos['Zn'] = [layt[k][2] for k in range(self.N)]

        # エッジの座標リスト作成
        self.edge_pos['Xe'] = []
        self.edge_pos['Ye'] = []
        self.edge_pos['Ze'] = []
        for e in self.edges:
            self.edge_pos['Xe'] += [layt[e[0]][0], layt[e[1]][0], None]
            self.edge_pos['Ye'] += [layt[e[0]][1], layt[e[1]][1], None]
            self.edge_pos['Ze'] += [layt[e[0]][2], layt[e[1]][2], None]


    def initialize_graph(self):
        """
        グラフ描画のための設定を行いフィールドに保存する関数
        """

        # エッジ（線）の描画設定
        trace1 = go.Scatter3d(
            x=self.edge_pos['Xe'], y=self.edge_pos['Ye'], z=self.edge_pos['Ze'],
            mode='lines',
            line=dict(color='rgb(125,125,125)', width=1),
            hoverinfo='none'
        )

        # ホバーテキスト（ツールチップ）の作成（ノードの直接隣接ノードの名前をホバー時に表示するために、隣接ノードの情報を作成する。）
        hover_texts = []
        for i in range(self.N):
            my_name = self.labels[i]  # 自分自身の名前
            neighbor_indices = self.G.neighbors(i)  # 隣人のインデックスを取得 (igraphの機能)
            neighbor_names = [self.labels[n] for n in neighbor_indices]  # 隣人の名前リストに変換
            
            # 表示用テキストを作成 (<br>は改行)。例: "Valjean<br>Neighbors: Cosette, Marius"
            text = f"<b>{my_name}</b>"
            if neighbor_names:
                for each in neighbor_names:
                    text += f"<br>{each}"
 
            hover_texts.append(text)

        # ノード（点）の描画設定
        trace2 = go.Scatter3d(
            x=self.node_pos['Xn'], y=self.node_pos['Yn'], z=self.node_pos['Zn'],
            mode='markers',
            name='participants',
            marker=dict(
                symbol='circle',
                size=6,
                color=self.group,
                colorscale='Viridis',
                line=dict(color='rgb(50,50,50)', width=0.5)
            ),
            text=hover_texts,
            hoverinfo='text'
        )

        # 軸の設定
        axis = dict(
            showbackground=False,
            showline=False,
            zeroline=False,
            showgrid=False,
            showticklabels=False,
            showspikes=False,  # 3D空間上の位置を把握しやすくするための補助線をホバー時に表示する機能をオフ
            title=''
        )

        # 全体のレイアウト設定
        layout = go.Layout(
            title="",
            # width=1000,  # グラフが表示される領域の幅。これらを指定しないと、ブラウザのウィンドウサイズに合わせて自動調整される。
            # height=1000,  # グラフが表示される領域の高さ。これらを指定しないと、ブラウザのウィンドウサイズに合わせて自動調整される。
            showlegend=False,
            scene=dict(
                xaxis=dict(axis),
                yaxis=dict(axis),
                zaxis=dict(axis),
            ),
            # margin=dict(t=100),
            hovermode='closest',
            annotations=[
                # dict(
                #     showarrow=False,
                #     # text="Data source: [1] miserables.json (Local File)",
                #     xref='paper',
                #     yref='paper',
                #     x=0,
                #     y=0.1,
                #     xanchor='left',
                #     yanchor='bottom',
                #     font=dict(size=14)
                # )
            ]
        )

        data_traces = [trace1, trace2]
        self.fig = go.Figure(data=data_traces, layout=layout)


    def perfom(self):
        """
        描画を行う関数
        """

        # グラフ表示
        self.fig.show()


    def add_elements(self, add_data: list):
        """
        要素の追加を行う関数
        """
