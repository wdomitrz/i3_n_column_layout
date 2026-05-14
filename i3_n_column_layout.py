#!/usr/bin/env python3
################################################################
# Copyright (c) 2024 Witalis Domitrz <witekdomitrz@gmail.com>
# AGPL License
################################################################
#
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "i3ipc",
#   "typing_extensions",
# ]
# ///

import argparse
from dataclasses import dataclass
from typing import Literal, cast

import i3ipc  # pyright: ignore[reportMissingTypeStubs]
from typing_extensions import Self


def container_to_ignore(container: i3ipc.Con) -> bool:
    return (
        "_on" in container.floating  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
        or getattr(container, "fullscreen_mode", 0) == 1
        or container.parent.layout in ["stacked", "tabbed"]  # pyright: ignore[reportUnknownMemberType]
    )


def get_container_width(container: i3ipc.Con) -> int:
    return cast(int, container.rect.width)


def get_workspace_width(container: i3ipc.Con) -> int:
    workspace = container.workspace()
    assert workspace is not None
    return cast(int, workspace.rect.width)


def n_column_layout(i3: i3ipc.Connection, *, n: float) -> None:
    def resize_to_nth(i3: i3ipc.Connection, event: i3ipc.events.IpcBaseEvent) -> None:
        del event
        container = i3.get_tree().find_focused()
        if (
            container is None
            or container_to_ignore(container)
            or (
                container.parent is not None
                and (
                    cast(i3ipc.Con, container.parent).ipc_data["rect"]["y"]
                    != container.ipc_data["rect"]["y"]
                )
            )
        ):
            return

        workspace_width = get_workspace_width(container)
        container_width = get_container_width(container)
        size_delta = container_width % (workspace_width // n)
        if -n <= (size_delta - workspace_width // n):
            size_delta -= workspace_width // n

        _ = i3.command(f"resize set width {container_width - int(size_delta)}")

    def up_to_n_colums(i3: i3ipc.Connection, event: i3ipc.events.IpcBaseEvent) -> None:
        del event
        container = i3.get_tree().find_focused()
        if container is None or container_to_ignore(container):
            return

        if get_container_width(container) > 2 * get_workspace_width(container) // n - n:
            how_to_split: Literal["horizontal", "vertical"] = "horizontal"
        else:
            how_to_split = "vertical"

        _ = i3.command(f"split {how_to_split}")

    i3.on(event=i3ipc.Event.WINDOW_CLOSE, handler=resize_to_nth)
    i3.on(event=i3ipc.Event.WINDOW_FOCUS, handler=up_to_n_colums)
    i3.on(event=i3ipc.Event.WINDOW_FULLSCREEN_MODE, handler=resize_to_nth)
    i3.on(event=i3ipc.Event.WINDOW_MOVE, handler=resize_to_nth)
    i3.on(event=i3ipc.Event.WINDOW_NEW, handler=resize_to_nth)


@dataclass(kw_only=True, frozen=True)
class Args:
    number_of_columns: float

    @classmethod
    def from_args(cls, argv: list[str] | None = None) -> Self:
        parser = argparse.ArgumentParser()
        _ = parser.add_argument("--number-of-columns", type=float, default=2.0)
        args = parser.parse_args(argv)
        return cls(number_of_columns=cast(float, args.number_of_columns))

    def run(self) -> int:
        i3 = i3ipc.Connection()
        n_column_layout(i3, n=self.number_of_columns)
        i3.main()
        return 0


if __name__ == "__main__":
    raise SystemExit(Args.from_args().run())
