import colorsys
from typing import List, Tuple, Optional
from pathlib import Path
from collections import deque
import struct

from graphviz import Digraph
from loguru import logger
from pydantic import BaseModel

DEFAULT_PALETTE = [
    "#000000",  # 黑色
    "#FF6F61",  # 鲜艳的珊瑚红
    "#6B5B95",  # 紫罗兰色
    "#88B04B",  # 青绿色调的黄绿色
    "#F7CAC9",  # 粉色调
    "#92A8D1",  # 浅蓝紫色
    "#F7786B",  # 鲜艳的粉红
    "#DE7A22",  # 鲜橙色
    "#2E8B57",  # 海洋绿
    "#FFD700",  # 金黄色
    "#4682B4",  # 钢蓝色
    "#D9534F",  # 鲜艳的红色
    "#5BC0DE",  # 浅蓝色
    "#FFB347",  # 橙黄色
    "#B39EB5",  # 淡紫色
    "#E94E77",  # 鲜亮的玫瑰红
]

class Style(BaseModel):
    shape: str = 'rect'
    style: str = 'rounded,filled'
    fill_color: str = '#FFFFFF'
    border_color: str = '#000000'
    font_color: str = '#000000'
    fontname: str = 'Arial'
    fontsize: int = 12

class TreeNode:
    def __init__(self, content: str, level: int, kind: str = '#', style: Style = None):
        self.node_id = 'node_0'
        self.content = content
        self.level = level
        self.kind = kind
        if style is None:
            self.style = Style()
        else:
            self.style = style
        self.children: List[TreeNode] = []
        self.parent: Optional[TreeNode] = None

    def add_child(self, child: 'TreeNode'):
        self.children.append(child)
        child.parent = self
    
    def dfs(self):
        stack = [self]
        while stack:
            node = stack.pop()
            yield node
            stack.extend(reversed(node.children))

    def bfs(self):
        queue = deque([self])
        while queue:
            node = queue.popleft()
            yield node
            queue.extend(node.children)
    def __str__(self) -> str:
        return f"<TreeNode>[{self.level}] {'  ' * self.level}- {self.content}"
    def __repr__(self) -> str:
        return self.__str__()

def clean_content(content: str) -> str:
    return (
        content.strip()
            .replace('**', '')
            .strip()
            .rstrip('：')
            .strip()
            .rstrip(':')
            .strip()
            .rstrip('。')
            .strip()
    )

def parse_markdown_to_tree(markdown: str) -> Optional[TreeNode]:
    lines = markdown.split('\n')
    if not lines:
        return None

    root = TreeNode("Mindmap", 0)
    stack = [root]

    for line in lines:
        if not line.strip():
            continue

        line_strip = line.strip()
        if line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            content = line.lstrip('#').strip()
            kind = '#'
            node = TreeNode(content, level, kind)
        elif len(line_strip) > 3:
            if (line_strip[0] in '-*' and line_strip[1] == ' ') or (line_strip[0].isdigit() and line_strip[1] == '.'):
                level = (len(line) - len(line.lstrip()))//2 + 1
                for i in range(len(stack) - 1, 0, -1):
                    if stack[i].kind == '#':
                        level += stack[i].level + 1
                        break
                content = clean_content(line_strip[2:])
                # 对于键值对，拆分为两个节点
                if ':' in content:
                    key, value = content.split(':')
                    key = clean_content(key)
                    value = clean_content(value)
                    key_node = TreeNode(key, level, kind='-')
                    value_node = TreeNode(value, level+1, kind='-')
                    key_node.add_child(value_node)
                    node = key_node
                else:
                    kind = '-'
                    content = clean_content(content)
                    node = TreeNode(content, level, kind)
            else:
                # 如果遇到---，则表示结束
                content = clean_content(line_strip)
                if content == '---':
                    break
                level = stack[-1].level + 1
                kind = 'T'
                node = TreeNode(content, level, kind)
                logger.debug(f"parse_markdown_to_tree(1): Text: [{level}] => {content[:20]}...")
        else:
            level = stack[-1].level + 1
            content = clean_content(line_strip)
            # 如果遇到---，则表示结束
            if content == '---':
                break
            kind = 'T'
            node = TreeNode(content, level, kind)
            logger.debug(f"parse_markdown_to_tree(2): Text: [{level}] => {content[:20]}...")

        while len(stack) > 1 and stack[-1].level >= level:
            stack.pop()

        stack[-1].add_child(node)
        stack.append(node)

    # 根据实际层级，修正节点
    ## 1. 如果根节点只有一个子节点，那么根节点就是这个子节点
    if len(root.children) == 1:
        root = root.children[0]
        root.level = 0
        root.parent = None
        root.node_id = 'node_0'
    ## 2. 从根节点开始重新计算层级、节点ID
    stack = [root]
    i = 1
    while stack:
        node = stack.pop()
        if node.parent:
            node.level = node.parent.level + 1
            node.node_id = f"node_{i}"
            i += 1
        stack.extend(reversed(node.children))
    return root

def hex_to_rgba(hex_color: str) -> Tuple[int, int, int, int]:
    hex_color = hex_color.lstrip('#')
    if len(hex_color) < 6:
        raise ValueError("Invalid hex color")
    elif len(hex_color) == 6:
        hex_color += 'FF'

    r,g,b,a = struct.unpack('BBBB', bytes.fromhex(hex_color))
    return r,g,b,a

def lighten_color(hex_color: str, percentage: float) -> str:
    r,g,b,a = hex_to_rgba(hex_color)
    r = int(r + (255 - r) * percentage)
    g = int(g + (255 - g) * percentage)
    b = int(b + (255 - b) * percentage)
    return f"#{r:02X}{g:02X}{b:02X}{a:02X}"

def transparent_color(hex_color: str, alpha: float) -> str:
    r,g,b,a = hex_to_rgba(hex_color)
    a = int(a * alpha)
    return f"#{r:02X}{g:02X}{b:02X}{a:02X}"

def assign_background_color(node: TreeNode, color: str):
    r,g,b,a = hex_to_rgba(color)
    h,s,v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
    if v < 0.5:
        node.style.font_color = '#FFFFFF'
    else:
        node.style.font_color = '#000000'
    node.style.fill_color = color
    node.style.border_color = color

def assign_color_to_tree(tree: TreeNode, palette: List[str] = None):
    if palette is None:
        palette = DEFAULT_PALETTE
    # 对root节点着色
    assign_background_color(tree, palette[0])

    # 对第一级节点按照调色板进行着色
    for i, child in enumerate(tree.children):
        if i < len(palette):
            c = transparent_color(palette[i+1], 0.5)
            assign_background_color(child, c)
    # 对于其次的每个节点，根据其父节点的颜色调淡（增加透明度）
    for node in tree.dfs():
        if node.level > 1:
            # 相比于父节点，透明度增加
            c = transparent_color(node.parent.style.fill_color, 0.5)
            assign_background_color(node, c)

def markdown_to_mindmap(markdown: str, output: str):
    tree = parse_markdown_to_tree(markdown)
    assign_color_to_tree(tree)
    for node in tree.dfs():
        logger.debug(node)

    dot = Digraph(comment='Mindmap')
    dot.attr(rankdir='LR', layout='dot')
    dot.node_attr.update(shape='rect', style='rounded,filled', color='white', fontname='Arial', fontsize='12')
    dot.edge_attr.update(dir='none', color='#000000', penwidth='2', headport='w', tailport='e')

    for node in tree.dfs():
        if node.style:
            dot.node(node.node_id, node.content, fillcolor=node.style.fill_color, fontcolor=node.style.font_color, color=node.style.border_color)
        else:
            dot.node(node.node_id, node.content)
        if node.parent:
            dot.edge(node.parent.node_id, node.node_id, color=node.style.fill_color)

    po = Path(output)
    src = po.parent / f"{po.stem}.gv"
    pdf = po.parent / f"{po.stem}.pdf"
    logger.debug(f"markdown_to_mindmap(): output: {output}, src: {src}, pdf: {pdf}")
    dot.render(filename=src, format='pdf', outfile=pdf)
