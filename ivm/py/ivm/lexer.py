import regex as re
from dataclasses import dataclass, field
from typing import Iterator

from regex import Pattern


@dataclass
class TokenFactory:
    tokens: list[str] = field(default_factory=list)

    def add_token(self, token: str) -> int:
        l = len(self.tokens)
        self.tokens.append(token)
        return l

    def add_tokens(self, tokens: str) -> list[int]:
        parts = tokens.split("|")
        l = len(self.tokens)
        self.tokens.extend(parts)
        return [l + i for i in range(len(parts))]

    def compile(self) -> Pattern[str]:
        return re.compile("|".join(f"({t})" for t in self.tokens))


top_level = TokenFactory()
skips = top_level.add_tokens(r"[ \t\r\n\f]+|//.*")
open_comment = top_level.add_token(r"/\*")
(
    open_paren,
    close_paren,
    open_brace,
    close_brace,
    open_bracket,
    close_bracket,
    at,
    dollar,
    eq,
    hole,
    question,
    hash_,
    n32,
    f32,
    global_,
    ident_,
    other,
) = top_level.add_tokens(
    "\(|\)|\{|}|\[|]|@|\$|\=|_|\?|#|\d[\d\w]*|[+-][\d\w.\+\-]+|(?:::\p{ID_Continue}+)+|\p{ID_Start}\p{ID_Continue}*|."
)
p = top_level.compile()

in_comment = TokenFactory()
in_open_comment, in_close_comment = in_comment.add_tokens(r"/\*|\*/")
p_in_comment = in_comment.compile()


class SyntaxError(Exception):
    pass


@dataclass
class Lexer:
    lines: list[str]
    position: tuple[int, tuple[int, int]] = (0, (0, 0))

    def take_source(
        self,
        start_pos: tuple[int, tuple[int, int]],
        end_pos: tuple[int, tuple[int, int]],
    ) -> list[str]:
        return [
            self.lines[line_idx][
                (0 if line_idx != start_pos[0] else start_pos[1][0]) : (
                    -1 if line_idx != end_pos[0] else end_pos[1][1]
                )
            ]
            for line_idx in range(start_pos[0], end_pos[0])
        ]

    def tokenize(self) -> Iterator[tuple[int, str]]:
        ln = self.position[0]
        while ln < len(self.lines):
            line = self.lines[ln]
            i = p.finditer(line, pos=self.position[1][1])
            for match in i:
                group_match, token = next(
                    (i, a) for i, a in enumerate(match.groups()) if a is not None
                )
                if group_match == open_comment:
                    depth = 1
                    start_ln = ln
                    while depth > 0 and ln < len(self.lines):
                        for match in p_in_comment.finditer(line, match.end()):
                            group_match, token = next(
                                (i, a)
                                for i, a in enumerate(match.groups())
                                if a is not None
                            )
                            self.position = (ln, match.span())
                            if group_match == in_open_comment:
                                depth += 1
                            elif group_match == in_close_comment:
                                depth -= 1
                            if depth == 0:
                                break
                        if depth > 0:
                            ln += 1
                    if depth > 0:
                        raise SyntaxError(
                            f"Could not find terminating close comment, starting from line {start_ln + 1}"
                        )
                    break
                elif group_match in skips:
                    continue
                elif group_match == other:
                    raise SyntaxError(
                        f"Unexpected token {token} on line {ln + 1} position {match.span()} {len(top_level.tokens)} {len(match.groups())}"
                    )
                else:
                    self.position = (ln, match.span())
                    yield group_match, token
            else:
                self.position = ((ln := ln + 1), (0, 0))


def test_tokenize():
    assert (
        list(
            t
            for t, _ in Lexer(
                """
::std::numeric { /* /* hellow */ a */ fn(dup43(n0 @n32_ne(0 ?(a b c))) n1) }
""".splitlines()
            ).tokenize()
        )
        == [
            global_,
            open_brace,
            ident_,
            open_paren,
            ident_,
            open_paren,
            ident_,
            at,
            ident_,
            open_paren,
            n32,
            question,
            open_paren,
            ident_,
            ident_,
            ident_,
            close_paren,
            close_paren,
            close_paren,
            ident_,
            close_paren,
            close_brace,
        ]
    )
