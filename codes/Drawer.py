#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
O_noderにおける、グラフ描画用のコード
"""

__author__ = 'Muto Tao'
__version__ = '1.0.0'
__date__ = '2025.12.4'


import os
import glob
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
    FILE_PATHS: str
    FILE_NAMES: dict
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


    def __init__(self, graph_data, FILE_PATHS, FILE_NAMES):
        """
        コンストラクタ
        """

        # グラフのデータを獲得
        self.data = graph_data
        self.FILE_PATHS = FILE_PATHS
        self.FILE_NAMES = FILE_NAMES
        self.N = len(graph_data['nodes'])
        self.L = len(graph_data['links'])
        self.edges = [(graph_data['links'][k]['source'], graph_data['links'][k]['target']) for k in range(self.L)]
        self.labels = []
        self.group = []
        for node in graph_data['nodes']:
            self.labels.append(node['name'])
            self.group.append(0)

        # グラフオブジェクトの生成
        self.laout = ig.Graph(n=self.N, edges=self.edges, directed=False).layout(self.LAYOUT_ALGORITHM, dim=3)  # 明示的にノード数を伝えることで、他と繋がりのないノードも表示できるようにする。

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
            tmp = glob.glob(os.path.join(self.FILE_PATHS['prof'], f"{node_info['name']}.*"))
            if tmp:  # プロフィール画像が存在する場合
                img_filename = os.path.basename(tmp[0])  # 画像ファイル名を指定
            else:
                img_filename = self.FILE_NAMES['no_image_img']

            nodes.append({
                "id": node_info.get('name', f"Node_{i}"), # 名前をIDとして使用
                "img": img_filename,
                "img_id": node_info.get('img_id'),
                "fx": coords[i][0] * scale,
                "fy": coords[i][1] * scale,
                "fz": coords[i][2] * scale
            })

        # ブラウザ側(3d-force-graph)には、インデックスではなく「ID(名前)」でつながりを教えなければならない。
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
