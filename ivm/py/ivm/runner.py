import ast

def f():
    a: int = 5
    a += 2
    a *= 9
    return a

print(
    ast.dump(
        ast.parse(open(__file__, "r").read()),
        indent=True
    )
)
