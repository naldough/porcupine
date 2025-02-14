from __future__ import annotations

import dataclasses
import logging
import re
import tkinter
from pathlib import Path
from typing import Dict, Iterator, List, Union

import dacite
import tree_sitter
import tree_sitter_languages
import yaml

from porcupine import textutils

from .base_highlighter import BaseHighlighter

log = logging.getLogger(__name__)

# setup() can show an error message, and the ttk theme affects that
setup_after = ["ttk_themes"]

TOKEN_MAPPING_DIR = Path(__file__).absolute().with_name("tree-sitter-token-mappings")


@dataclasses.dataclass
class YmlConfig:
    token_mapping: Dict[str, Union[str, Dict[str, str]]]
    dont_recurse_inside: List[str] = dataclasses.field(default_factory=list)
    queries: Dict[str, str] = dataclasses.field(default_factory=dict)


def _strip_comments(query: str) -> str:
    # Ignore '#' between double quotes.
    # Otherwise ignore everything after '#' on the same line.
    # If the query contains an odd number of " (excluding comments), don't remove the last one.
    parts = re.findall(r'"[^"]*"|"|#.*|[^#"]+', query)
    return "".join(p for p in parts if not p.startswith("#"))


class TreeSitterHighlighter(BaseHighlighter):
    def __init__(self, textwidget: tkinter.Text, language_name: str) -> None:
        super().__init__(textwidget)
        self._language = tree_sitter_languages.get_language(language_name)

        self._parser = tree_sitter.Parser()
        self._parser.set_language(self._language)
        self._tree = self._parser.parse(self._get_file_content_for_tree_sitter())

        token_mapping_path = TOKEN_MAPPING_DIR / (language_name + ".yml")
        with token_mapping_path.open("r", encoding="utf-8") as file:
            self._config = dacite.from_dict(YmlConfig, yaml.safe_load(file))

        # Pseudo-optimization: "pre-compile" queries when the highlighter starts.
        # Also makes the highlighter fail noticably if any query contain syntax errors.
        self._queries = {
            node_type_name: self._language.query(_strip_comments(text))
            for node_type_name, text in self._config.queries.items()
        }

    def _get_file_content_for_tree_sitter(self) -> bytes:
        # tk indexes are in chars, tree_sitter is in utf-8 bytes
        # here's my hack to get them compatible:
        #
        # bad:  "örkki" (5 chars) --> b"\xc3\xb6rkki" (6 bytes)
        # good: "örkki" (5 chars) --> b"?rkki" (5 bytes)
        #
        # should be ok as long as all your non-ascii chars are e.g. inside strings
        return self.textwidget.get("1.0", "end - 1 char").encode("ascii", errors="replace")

    def _decide_tag(self, node: tree_sitter.Node) -> str:
        if set(node.type) <= set("+-*/%~&|^!?<>=@.,:;()[]{}"):
            default = "Token.Operator"
        else:
            default = "Token.Text"

        config_value = self._config.token_mapping.get(node.type, default)
        if isinstance(config_value, dict):
            # Specifying empty string can be used to set a custom fallback when
            # the text of the node isn't found in the config.
            default = config_value.get("", default)
            return config_value.get(node.text.decode("utf-8"), default)
        return config_value

    # only returns nodes that overlap the start,end range
    def _get_nodes_and_tags(
        self,
        cursor: tree_sitter.TreeCursor,
        start_point: tuple[int, int],
        end_point: tuple[int, int],
    ) -> Iterator[tuple[tree_sitter.Node, str]]:
        assert self._config is not None
        overlap_start = max(cursor.node.start_point, start_point)
        overlap_end = min(cursor.node.end_point, end_point)
        if overlap_start >= overlap_end:
            # No overlap with the range we care about. Skip subnodes.
            return

        query = self._queries.get(cursor.node.type)
        if query is not None:
            captures = query.captures(cursor.node)
            # Ignore the query if it doesn't match at all. Queries are usually
            # written to handle some specific situation, and we want a reasonable
            # fallback. For example, in a C function definition "int asdf() {}"
            # the function name "asdf" is highlighted with a query, but a function
            # pointer like "int (*foo)() = asdf;" should be just recursed into as
            # it would be without the query.
            if captures:
                to_recurse = []
                for subnode, tag_or_recurse in captures:
                    if tag_or_recurse == "recurse":
                        to_recurse.append(subnode)
                    else:
                        yield (subnode, tag_or_recurse)

                for subnode in to_recurse:
                    # Tell the tagging code that we're about to recurse.
                    # This lets it wipe tags that were previously added on the area.
                    # That's also why recursing is done last.
                    yield (subnode, "recurse")
                    yield from self._get_nodes_and_tags(subnode.walk(), start_point, end_point)
                return

        if cursor.node.type not in self._config.dont_recurse_inside and cursor.goto_first_child():
            yield from self._get_nodes_and_tags(cursor, start_point, end_point)
            while cursor.goto_next_sibling():
                yield from self._get_nodes_and_tags(cursor, start_point, end_point)
            cursor.goto_parent()
        else:
            yield (cursor.node, self._decide_tag(cursor.node))

    # tree-sitter has get_changed_ranges() method, but it has a couple problems:
    #   - It returns empty list if you append text to end of a line. But text like that may need to
    #     get highlighted.
    #   - Release version from pypi doesn't have the method.
    def update_tags_of_visible_area_from_tree(self) -> None:
        start, end = self.get_visible_part()
        start_row, start_col = map(int, start.split("."))
        end_row, end_col = map(int, end.split("."))
        start_point = (start_row - 1, start_col)
        end_point = (end_row - 1, end_col)

        self.delete_tags(start, end)

        for node, tag in self._get_nodes_and_tags(self._tree.walk(), start_point, end_point):
            start_row, start_col = node.start_point
            end_row, end_col = node.end_point
            start = f"{start_row+1}.{start_col}"
            end = f"{end_row+1}.{end_col}"

            if tag == "recurse":
                self.delete_tags(start, end)
            else:
                self.textwidget.tag_add(tag, start, end)

    def on_scroll(self) -> None:
        # TODO: This could be optimized. Often most of the new visible part was already visible before.
        self.update_tags_of_visible_area_from_tree()

    def on_change(self, changes: textutils.Changes) -> None:
        if not changes.change_list:
            return

        if len(changes.change_list) >= 2:
            # slow, but doesn't happen very often in normal editing
            self._tree = self._parser.parse(self._get_file_content_for_tree_sitter())
        else:
            [change] = changes.change_list
            start_row, start_col = change.start
            old_end_row, old_end_col = change.old_end
            new_end_row, new_end_col = change.new_end

            start_byte = self.textwidget.tk.call(
                str(self.textwidget), "count", "-chars", "1.0", f"{start_row}.{start_col}"
            )
            self._tree.edit(
                start_byte=start_byte,
                old_end_byte=start_byte + len(change.old_text),
                new_end_byte=start_byte + len(change.new_text),
                start_point=(start_row - 1, start_col),
                old_end_point=(old_end_row - 1, old_end_col),
                new_end_point=(new_end_row - 1, new_end_col),
            )
            self._tree = self._parser.parse(self._get_file_content_for_tree_sitter(), self._tree)

        self.update_tags_of_visible_area_from_tree()
