import curses
import dataclasses
import sys
from typing import Any

from ivm.heap import Port
from ivm.host import Host
from ivm.readback import Reader


@dataclasses.dataclass
class History:
    current_interaction: tuple[str, str, str]
    links: list[tuple[str, str]]
    current_pairs: list[tuple[str, str]]
    current_wires: list[tuple[str, str]]

    def render(self, screen: curses.window) -> None:
        height, width =  screen.getmaxyx()
        width = min(width, 150)

        row = 0
        port_a_desc, interaction, port_b_desc = self.current_interaction
        screen.addstr(row, 0, port_a_desc)
        screen.addstr(row, width // 2 - len(interaction), interaction)
        screen.addstr(row, width - len(port_b_desc) - 1, port_b_desc)
        row += 1

        if self.links:
            row += 1
            screen.addstr(row, 0, "links")
            row += 1
            for port_a_desc, port_b_desc in self.links:
                screen.addstr(row, 0, port_a_desc)
                screen.addstr(row, width // 2 - 8, "linked to")
                screen.addstr(row, width - len(port_b_desc) - 1, port_b_desc)
                row += 1

        row += 1
        screen.addstr(row, 0, "wires")
        row += 1
        for wire_name, wire_desc in self.current_wires:
            if row >= height:
                return
            screen.addstr(row, 0, wire_name or "")
            screen.addstr(row, width // 2 - 2, "=>")
            screen.addstr(row, width - len(wire_desc) - 1, wire_desc)
            row += 1

        if self.current_pairs:
            row += 1
            screen.addstr(row, 0, "pairs")
            row += 1
            for port_a_desc, port_b_desc in self.current_pairs:
                screen.addstr(row, 0, port_a_desc)
                screen.addstr(row, width // 2 - 1, "=")
                screen.addstr(row, width - len(port_b_desc) - 1, port_b_desc)
                row += 1


def attach_debugger_to(host: Host):
    reader = Reader(host.ivm)
    stdscreen: Any
    history: list[History] = []

    def on_interaction(a: Port, b: Port, interaction: str) -> None:
        nonlocal stdscreen

        new_history = History(
            current_interaction=(str(reader.read_port(a)), interaction, str(reader.read_port(b))),
            links=[],
            current_pairs=[
                (str(reader.read_port(a)), str(reader.read_port(b)))
                for group in (host.ivm.active_fast, host.ivm.active_slow)
                for a, b in group
            ],
            current_wires=sorted(
                (str(reader.read_wire(wire)), str(reader.read_port(port)))
                for left_wire in host.ivm.heap.wires
                for wire in (left_wire, left_wire.other_half)
                for port in (wire.load_target(),)
                if port is not None
            )
        )
        history.append(new_history)
        render_histories()

    def render_histories():
        idx = len(history) - 1
        while idx < len(history):
            stdscreen.clear()
            history[idx].render(stdscreen)
            stdscreen.refresh()
            k = stdscreen.getch()
            if k ==  curses.KEY_LEFT:
                idx = max(idx - 1, 0)
            if k == curses.KEY_RIGHT:
                idx += 1

    def on_begin():
        nonlocal stdscreen
        stdscreen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        stdscreen.keypad(True)
        try:
            curses.start_color()
        except:
            pass

    def on_end():
        nonlocal stdscreen
        assert stdscreen is not None
        stdscreen.keypad(False)
        curses.echo()
        curses.nocbreak()
        curses.endwin()

    def on_link(a: Port, b: Port) -> None:
        if not history:
            return
        last_history = history[-1]
        history.append(dataclasses.replace(last_history, links=[*last_history.links, (
            str(reader.read_port(a, shallow=False)), str(reader.read_port(b, shallow=False))
        )]))
        render_histories()


    host.ivm.on_interaction = on_interaction
    host.ivm.on_begin = on_begin
    host.ivm.on_end = on_end
    host.ivm.on_link = on_link
    # host.ivm.on_iteration = on_iteration
    # host.ivm.on_link = on_link
    # host.ivm.on_link_wire = on_link_wire