"""
Markdownコンバータモジュール

NotionのブロックとMarkdown形式の相互変換を行うクラスを提供します。
"""

from typing import List, Dict, Any
import mistune


class MarkdownConverter:
    """
    MarkdownとNotionブロック間の変換を行うクラス

    MarkdownテキストをパースしてNotionブロック形式に変換する機能と、
    NotionブロックをパースしてMarkdown形式に変換する機能を提供します。
    """

    def __init__(self):
        """
        MarkdownConverterのコンストラクタ
        """
        self.markdown_parser = mistune.create_markdown()

    def parse_markdown_to_blocks(self, md: str) -> List[Dict[str, Any]]:
        """
        Markdownテキストをパースし、Notionブロック形式に変換します。
        ToDoとbulleted_list_itemのネスト（2スペース以上のインデント）に対応します。

        Args:
            md: 変換するMarkdownテキスト

        Returns:
            Notionブロック形式のリスト, タイトル
        """
        # Markdownを行ごとに分割
        lines = md.strip().split("\n")
        blocks = []  # 最終的なNotionブロックリスト

        # タイトル（H1）を抽出
        title = None
        content_start_idx = 0
        title_found = False  # 最初のH1検出フラグ

        # すべての行を順に処理
        i = 0
        while i < len(lines):
            line = lines[i]

            # 最初のH1をタイトルとして扱う
            if not title_found and line.startswith("# "):
                title = line[2:].strip()
                title_found = True
                content_start_idx = i + 1
                i += 1
                continue  # タイトル行はブロック化しない
            i += 1

        # タイトルがない場合は空文字を設定
        if title is None:
            title = ""

        # ネスト対応用の親ブロック参照
        last_parent = None  # 直近の親ブロック（ToDoまたはbulleted_list_item）

        i = content_start_idx
        while i < len(lines):
            line = lines[i]
            # 行頭スペース数をカウント
            indent = len(line) - len(line.lstrip(' '))
            content_line = line.lstrip(' ')

            # ToDo（チェックボックス）
            if content_line.startswith("- [ ]") or content_line.startswith("- [x]"):
                checked = content_line.startswith("- [x]")
                content = content_line[5:].strip()
                block = {
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [
                            {"type": "text", "text": {"content": content}}
                        ],
                        "checked": checked,
                        "color": "default"
                    },
                }
                # インデント2スペース以上なら直前の親のchildrenに追加
                if indent >= 2 and last_parent is not None and last_parent["type"] == "to_do":
                    if "children" not in last_parent["to_do"]:
                        last_parent["to_do"]["children"] = []
                    last_parent["to_do"]["children"].append(block)
                else:
                    blocks.append(block)
                    last_parent = block  # 新しい親として記憶
            # 箇条書き（bulleted_list_item）
            elif content_line.startswith("- "):
                content = content_line[2:].strip()
                block = {
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            {"type": "text", "text": {"content": content}}
                        ]
                    },
                }
                # インデント2スペース以上なら直前の親のchildrenに追加
                if indent >= 2 and last_parent is not None and last_parent["type"] == "bulleted_list_item":
                    if "children" not in last_parent["bulleted_list_item"]:
                        last_parent["bulleted_list_item"]["children"] = []
                    last_parent["bulleted_list_item"]["children"].append(block)
                else:
                    blocks.append(block)
                    last_parent = block  # 新しい親として記憶
            # H1（2つ目以降はheading_1ブロックとして扱う）
            elif content_line.startswith("# "):
                block = {
                    "type": "heading_1",
                    "heading_1": {"rich_text": [{"type": "text", "text": {"content": content_line[2:].strip()}}]},
                }
                blocks.append(block)
                last_parent = None  # 親リセット
            # 見出し（H2-H6）
            elif content_line.startswith("## "):
                block = {
                    "type": "heading_2",
                    "heading_2": {"rich_text": [{"type": "text", "text": {"content": content_line[3:].strip()}}]},
                }
                blocks.append(block)
                last_parent = None
            elif content_line.startswith("### "):
                block = {
                    "type": "heading_3",
                    "heading_3": {"rich_text": [{"type": "text", "text": {"content": content_line[4:].strip()}}]},
                }
                blocks.append(block)
                last_parent = None
            # 番号付きリスト
            elif content_line.strip() and content_line[0].isdigit() and ". " in content_line:
                content = content_line.split(". ", 1)[1]
                block = {
                    "type": "numbered_list_item",
                    "numbered_list_item": {"rich_text": [{"type": "text", "text": {"content": content.strip()}}]},
                }
                blocks.append(block)
                last_parent = None
            # コードブロック
            elif content_line.startswith("```"):
                code_lines = []
                language = content_line[3:].strip()
                i += 1
                while i < len(lines) and not lines[i].startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                block = {
                    "type": "code",
                    "code": {
                        "rich_text": [{"type": "text", "text": {"content": "\n".join(code_lines)}}],
                        "language": language if language else "plain text",
                    },
                }
                blocks.append(block)
                last_parent = None
            # 通常のテキスト（段落）
            elif content_line.strip():
                block = {"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": content_line.strip()}}]}}
                blocks.append(block)
                last_parent = None
            i += 1

        return blocks, title

    def convert_blocks_to_markdown(self, blocks: List[Dict[str, Any]], title: str = None) -> str:
        """
        Notionブロックをパースし、Markdown形式に変換します。

        Args:
            blocks: 変換するNotionブロックのリスト
            title: ページのタイトル（指定された場合はH1として出力）

        Returns:
            Markdown形式のテキスト
        """
        md_lines = []

        # タイトルがあればH1として追加
        if title:
            md_lines.append(f"# {title}")
            md_lines.append("")  # 空行を追加

        for block in blocks:
            block_type = block.get("type")

            if block_type == "paragraph":
                text_content = self._extract_text_content(block.get("paragraph", {}).get("rich_text", []))
                md_lines.append(text_content)
                md_lines.append("")  # 空行を追加

            elif block_type == "heading_1":
                text_content = self._extract_text_content(block.get("heading_1", {}).get("rich_text", []))
                md_lines.append(f"# {text_content}")
                md_lines.append("")

            elif block_type == "heading_2":
                text_content = self._extract_text_content(block.get("heading_2", {}).get("rich_text", []))
                md_lines.append(f"## {text_content}")
                md_lines.append("")

            elif block_type == "heading_3":
                text_content = self._extract_text_content(block.get("heading_3", {}).get("rich_text", []))
                md_lines.append(f"### {text_content}")
                md_lines.append("")

            elif block_type == "bulleted_list_item":
                text_content = self._extract_text_content(block.get("bulleted_list_item", {}).get("rich_text", []))
                md_lines.append(f"- {text_content}")

            elif block_type == "numbered_list_item":
                text_content = self._extract_text_content(block.get("numbered_list_item", {}).get("rich_text", []))
                md_lines.append(f"1. {text_content}")

            elif block_type == "code":
                code_block = block.get("code", {})
                language = code_block.get("language", "")
                text_content = self._extract_text_content(code_block.get("rich_text", []))

                md_lines.append(f"```{language}")
                md_lines.append(text_content)
                md_lines.append("```")
                md_lines.append("")

            elif block_type == "to_do":
                todo_item = block.get("to_do", {})
                checked = todo_item.get("checked", False)
                text_content = self._extract_text_content(todo_item.get("rich_text", []))

                checkbox = "[x]" if checked else "[ ]"
                md_lines.append(f"- {checkbox} {text_content}")

            elif block_type == "quote":
                text_content = self._extract_text_content(block.get("quote", {}).get("rich_text", []))
                md_lines.append(f"> {text_content}")
                md_lines.append("")

        return "\n".join(md_lines)

    def _extract_text_content(self, rich_text_list):
        """
        Notionのリッチテキスト配列からプレーンテキストを抽出します。

        Args:
            rich_text_list: Notionのリッチテキスト配列

        Returns:
            抽出されたプレーンテキスト
        """
        if not rich_text_list:
            return ""

        return "".join([rt.get("text", {}).get("content", "") for rt in rich_text_list if "text" in rt])
