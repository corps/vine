from collections import OrderedDict
from dataclasses import dataclass
from typing import overload, Literal

from .heap import Trace, SourceInfo, SpanInfo
from .tree import (
    Net,
    Tree,
    Nets,
    N32,
    F32,
    BlackBox,
    Erase,
    BranchNode,
    ExtFnNode,
    VarNode,
    CombNode,
    GlobalNode,
    F32Node,
    N32Node,
)
from .lexer import (
    Lexer,
    global_,
    open_paren,
    open_brace,
    n32,
    f32,
    ident_,
    close_paren,
    at,
    dollar,
    question,
    hole,
    hash_,
    open_bracket,
    close_bracket,
    close_brace,
    eq,
)


class SyntaxError(Exception):
    position: tuple[int, tuple[int, int]]

    def __init__(self, message: str, position: tuple[int, tuple[int, int]]) -> None:
        self.position = position
        super().__init__(f"{message} on line {position[0]}:{position[1][0]}")


@dataclass
class IvyParserState:
    lexer: Lexer
    source_file: str
    last_token: tuple[int, str] | None = None

    def __post_init__(self) -> None:
        self.bump()

    def bump(self) -> bool:
        try:
            (
                k,
                t,
            ) = next(self.lexer.tokenize())
            self.last_token = (k, t)
        except StopIteration:
            self.last_token = None
            return False
        return True

    def expect(self, token_type: int) -> str:
        if not self.last_token:
            raise SyntaxError(f"Unexpected end of input", self.lexer.position)
        if self.last_token[0] == token_type:
            last_token = self.last_token
            self.last_token = None
            return last_token[1]
        raise SyntaxError(f"Unexpected token {self.last_token[1]}", self.lexer.position)

    @overload
    def eat(self, token_type: int, /, require: Literal[True]) -> str: ...
    @overload
    def eat(self, token_type: int, /, require: Literal[False]) -> str | None: ...
    def eat(self, token_type: int, /, require: bool) -> str | None:
        if require:
            result = self.expect(token_type)
        else:
            if not self.check(token_type):
                return None
            result = self.expect(token_type)
        self.bump()
        return result

    def check(self, token_type: int) -> bool:
        if self.last_token and self.last_token[0] == token_type:
            return True
        return False


@dataclass
class IvyParser:
    state: "IvyParserState"

    @classmethod
    def from_file(cls, filename: str) -> "IvyParser":
        with open(filename, "r") as f:
            return IvyParser(
                IvyParserState(
                    lexer=Lexer(f.readlines()),
                    source_file=filename,
                ),
            )

    def parse_u32_like(self, token: str) -> N32:
        if token.startswith("0b"):
            token = token[2:]
            radix = 2
        elif token.startswith("0o"):
            token = token[2:]
            radix = 8
        elif token.startswith("0x"):
            token = token[2:]
            radix = 16
        else:
            radix = 10

        result = 0
        for c in token:
            if c == "_":
                continue
            result *= radix
            try:
                result += int(c, radix)
            except ValueError:
                raise SyntaxError(
                    f"Character {c} could not be understood as digit with radix {radix}",
                    self.state.lexer.position,
                )
        if result >= 2**32:
            raise SyntaxError(
                f"Value {result} is too large for n32", self.state.lexer.position
            )
        return N32(result)

    def parse_f32_like(self, token: str) -> F32:
        try:
            return F32(float(token))
        except ValueError:
            raise SyntaxError(
                f"Value {token} could not be understood as float",
                self.state.lexer.position,
            )

    def parse_nets(self) -> Nets:
        nets: Nets = OrderedDict()
        start_pos = self.state.lexer.position
        while name := self.state.eat(global_, require=False):
            net = self.parse_net()
            end_pos = self.state.lexer.position
            source = self.state.lexer.take_source(start_pos, end_pos)

            for t in net:
                if not isinstance(t.trace, SpanInfo):
                    continue
                t.trace = SourceInfo(
                    head_span=(
                        t.trace.head_span[0] - start_pos[0],
                        (
                            t.trace.head_span[1][0] - start_pos[1][0],
                            t.trace.head_span[1][1] - start_pos[1][0],
                        ),
                    ),
                    row_span=(
                        t.trace.row_span[0] - start_pos[0],
                        t.trace.row_span[1] - start_pos[0],
                    ),
                    col_span=(
                        (
                            t.trace.col_span[0] - start_pos[1][0]
                            if t.trace.row_span[0] == start_pos[0]
                            else t.trace.col_span[0]
                        ),
                        t.trace.col_span[1],
                    ),
                    containing_net_name=name,
                    containing_net_source=source,
                )

            nets[name] = net
            start_pos = end_pos
        return nets

    def parse_net(self) -> Net:
        self.state.eat(open_brace, require=True)
        root = self.parse_tree()
        pairs = []
        while not self.state.eat(close_brace, require=False):
            pairs.append(self.parse_pair())
        return Net(root, tuple(pairs))

    def parse_pair(self) -> tuple[Tree, Tree]:
        a = self.parse_tree()
        self.state.eat(eq, require=True)
        b = self.parse_tree()
        return a, b

    def parse_tree(self) -> Tree:
        start_pos = self.state.lexer.position
        if self.state.check(n32):
            return N32Node(
                self.parse_u32_like(self.state.eat(n32, require=True)),
                SpanInfo(
                    head_span=start_pos,
                    row_span=(start_pos[0], start_pos[0]),
                    col_span=start_pos[1],
                ),
            )
        elif self.state.check(f32):
            return F32Node(
                self.parse_f32_like(self.state.eat(f32, require=True)),
                SpanInfo(
                    head_span=start_pos,
                    row_span=(start_pos[0], start_pos[0]),
                    col_span=start_pos[1],
                ),
            )
        elif self.state.check(global_):
            global_name = self.state.eat(global_, require=True)
            return GlobalNode(
                global_name,
                SpanInfo(
                    head_span=start_pos,
                    row_span=(start_pos[0], start_pos[0]),
                    col_span=start_pos[1],
                ),
            )
        elif self.state.check(ident_):
            ident = self.state.eat(ident_, require=True)
            if self.state.eat(open_paren, require=False):
                a = self.parse_tree()
                b = self.parse_tree()
                self.state.eat(close_paren, require=True)
                end_pos = self.state.lexer.position
                return CombNode(
                    ident,
                    a,
                    b,
                    SpanInfo(
                        head_span=start_pos,
                        row_span=(start_pos[0], end_pos[0]),
                        col_span=(start_pos[1][0], end_pos[1][1]),
                    ),
                )
            else:
                return VarNode(
                    ident,
                    SpanInfo(
                        head_span=start_pos,
                        row_span=(start_pos[0], start_pos[0]),
                        col_span=start_pos[1],
                    ),
                )

        if self.state.eat(at, require=False):
            ident = self.state.eat(ident_, require=True)
            swapped = self.state.eat(dollar, require=False) is not None
            self.state.eat(open_paren, require=True)
            a = self.parse_tree()
            b = self.parse_tree()
            self.state.eat(close_paren, require=True)
            end_pos = self.state.lexer.position
            return ExtFnNode(
                ident + ("$" if swapped else ""),
                a,
                b,
                SpanInfo(
                    head_span=start_pos,
                    row_span=(start_pos[0], end_pos[0]),
                    col_span=(start_pos[1][0], end_pos[1][1]),
                ),
            )

        if self.state.eat(question, require=False):
            self.state.eat(open_paren, require=True)
            a = self.parse_tree()
            b = self.parse_tree()
            c = self.parse_tree()
            self.state.eat(close_paren, require=True)
            end_pos = self.state.lexer.position
            return BranchNode(
                a,
                b,
                c,
                SpanInfo(
                    head_span=start_pos,
                    row_span=(start_pos[0], end_pos[0]),
                    col_span=(start_pos[1][0], end_pos[1][1]),
                ),
            )

        if self.state.eat(hole, require=False):
            return Erase(
                SpanInfo(
                    head_span=start_pos,
                    row_span=(start_pos[0], start_pos[0]),
                    col_span=start_pos[1],
                )
            )

        if self.state.eat(hash_, require=False):
            self.state.eat(open_bracket, require=True)
            inner = self.parse_tree()
            self.state.eat(close_bracket, require=True)
            return BlackBox(inner, None)

        raise SyntaxError(
            f"Unexpected token {self.state.last_token}", self.state.lexer.position
        )
