#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
O_noderにおける、グラフ描画用のコード
"""

__author__ = 'Muto Tao'
__version__ = '0.2.0'
__date__ = '2025.12.3'


import os
import json
import random
import igraph as ig


class Drawer:
    """
    グラフ描画のためのクラス
    """

    # ハイパーパラメータ
    LAYOUT_ALGORITHM = "kk"

    # データ
    data: dict
    node_data: dict
    edge_data: dict
    img_data: dict
    edges: list
    N: int
    L: int
    labels: list
    group: list

    # グラフの情報
    lyout: ig
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


    def __init__(self, graph_data, img_data):
        """
        コンストラクタ
        """

        # グラフのデータを獲得
        self.data = graph_data
        # self.node_data = graph_data['nodes']
        # self.edge_data = graph_data['links']
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
        self.laout = ig.Graph(self.edges, directed=False).layout(self.LAYOUT_ALGORITHM, dim=3)

        # 描画に向けた設定
        self.set_coord()  # グラフの要素の座標を計算
        self.const_view_data()  # グラフの描画設定

    
    def set_coord(self):
        """
        グラフの要素（ノードとエッジ）の座標を計算し、フィールドに保存する関数
        """

        # ノードの座標リスト作成
        self.node_pos['Xn'] = [self.laout[k][0] for k in range(self.N)]
        self.node_pos['Yn'] = [self.laout[k][1] for k in range(self.N)]
        self.node_pos['Zn'] = [self.laout[k][2] for k in range(self.N)]

        # エッジの座標リスト作成
        self.edge_pos['Xe'] = []
        self.edge_pos['Ye'] = []
        self.edge_pos['Ze'] = []
        for e in self.edges:
            self.edge_pos['Xe'] += [self.laout[e[0]][0], self.laout[e[1]][0], None]
            self.edge_pos['Ye'] += [self.laout[e[0]][1], self.laout[e[1]][1], None]
            self.edge_pos['Ze'] += [self.laout[e[0]][2], self.laout[e[1]][2], None]


    def const_view_data(self):
        """
        グラフ描画のためのデータ構築を行い、構築したデータを返す関数
        """

        n_count = len(self.data['nodes'])
        coords = self.laout.coords
        scale = 100 

        nodes = []
        for i, node_info in enumerate(self.data['nodes']):
            # img_id を使って画像ファイル名を指定
            # 例: "1EZy....jpg"
            img_filename = f"img1.jpg"
            
            nodes.append({
                "id": node_info.get('name', f"Node_{i}"), # 名前をIDとして使用
                "img": img_filename,
                "fx": coords[i][0] * scale,
                "fy": coords[i][1] * scale,
                "fz": coords[i][2] * scale
            })

            # ブラウザ側(3d-force-graph)には、インデックスではなく「ID(名前)」で
            # つながりを教える必要があります。
            links = []
            for link in self.data['links']:
                src_idx = link.get('source')
                tgt_idx = link.get('target')
                
                if 0 <= src_idx < n_count and 0 <= tgt_idx < n_count:
                    links.append({
                        "source": self.data['nodes'][src_idx]['name'],
                        "target": self.data['nodes'][tgt_idx]['name']
                    })

        return {"nodes": nodes, "links": links}
    

    def add_elements(self, add_data: list):
        """
        要素の追加を行う関数
        """
