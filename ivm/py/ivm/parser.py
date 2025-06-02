from collections import OrderedDict
from dataclasses import dataclass

from .ast import Net, Tree, Nets, N32, F32
from .lexer import Lexer, global_, open_paren, open_brace, n32, f32, ident_, close_paren, at, dollar, question, hole, \
    hash_, open_bracket, close_bracket, close_brace, eq


class SyntaxError(Exception):
    position: tuple[int, tuple[int, int]]
    def __init__(self, message: str, position: tuple[int, tuple[int, int]]) -> None:
        self.position = position
        super().__init__(message)

@dataclass
class IvyParserState:
    lexer: Lexer
    last_token: tuple[int, str] | None = None

    def bump(self) -> bool:
        try:
            k, t, = next(self.lexer.tokenize())
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

    def eat(self, token_type: int, /, require: bool = False) -> str | None:
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

    def split(self) -> "IvyParserState":
        return IvyParserState(Lexer(self.lexer.lines, self.lexer.position))

@dataclass
class IvyParser:
    state: "IvyParserState"

    def parse_u32_like(self, token: str) -> N32 | None:
        if token.startswith('0b'):
            token = token[2:]
            radix = 2
        elif token.startswith('0o'):
            token = token[2:]
            radix = 8
        elif token.startswith('0x'):
            token = token[2:]
            radix = 16
        else:
            radix = 10

        result = 0
        for c in token:
            if c == '_':
                continue
            result *= radix
            try:
                result += int(c, radix)
            except ValueError:
                return None
        if result >= 2**32:
            return None
        return N32(result)

    def parse_f32_like(self, token: str) -> F32:
        try:
            return F32(float(token))
        except ValueError:
            return None

    @classmethod
    def parse_contents(cls, contents: str) -> Nets:
        parser = IvyParser(state=IvyParserState(lexer=Lexer(contents.splitlines())))
        parser.state.bump()
        return parser.parse_nets()

    def parse_nets(self) -> Nets:
        nets: Nets = OrderedDict()
        while name := self.state.eat(global_):
            net = self.parse_net()
            nets[name] = net
        return nets

    def parse_net(self) -> Net:
        self.state.eat(open_brace, require=True)
        root = self.parse_tree()
        pairs = []
        while not self.state.eat(close_brace):
            pairs.append(self.parse_pair())
        return Net(root, tuple(pairs))

    def parse_pair(self) -> tuple[Tree, Tree]:
        a = self.parse_tree()
        self.state.eat(eq)
        b = self.parse_tree()
        return a, b


    def parse_tree(self) -> Tree:
        if self.state.check(n32):
            return "N32", self.parse_u32_like(self.state.eat(n32))
        elif self.state.check(f32):
            return "F32", self.parse_f32_like(self.state.eat(f32))
        elif self.state.check(global_):
            return "Global", self.state.eat(global_)
        elif self.state.check(ident_):
            ident = self.state.eat(ident_, require=True)
            if self.state.eat(open_paren):
                a = self.parse_tree()
                b = self.parse_tree()
                self.state.eat(close_paren, require=True)
                return "Comb", ident, a, b
            else:
                return "Var", ident

        if self.state.eat(at):
            ident = self.state.eat(ident_, require=True)
            swapped = self.state.eat(dollar) is not None
            self.state.eat(open_paren, require=True)
            a = self.parse_tree()
            b = self.parse_tree()
            self.state.eat(close_paren, require=True)
            return "ExtFn", "$" + ident if swapped else ident, a, b

        if self.state.eat(question):
            self.state.eat(open_paren, require=True)
            a = self.parse_tree()
            b = self.parse_tree()
            c = self.parse_tree()
            self.state.eat(close_paren, require=True)
            return "Branch", a, b, c

        if self.state.eat(hole):
            return ("Erase",)

        if self.state.eat(hash_):
            self.state.eat(open_bracket, require=True)
            inner = self.parse_tree()
            self.state.eat(close_bracket, require=True)
            return "BlackBox", inner

        raise SyntaxError(f"Unexpected token {self.state.last_token}", self.state.lexer.position)



def test_parser():
    result = IvyParser.parse_contents("""
::std::numeric { /* /* hellow */ a */ fn(dup43(n0 @n32_ne(0 ?(a b c))) n1) }
    """)
    assert result == OrderedDict({
        "::std::numeric": Net(root=('Comb',
                        'fn',
                        ('Comb',
                         'dup43',
                         ('Var', 'n0'),
                         ('ExtFn',
                          'n32_ne',
                          False,
                          ('N32', N32(0)),
                          ('Branch',
                           ('Var', 'a'),
                           ('Var', 'b'),
                           ('Var', 'c')))),
                        ('Var', 'n1')),
                  pairs=())
    })
