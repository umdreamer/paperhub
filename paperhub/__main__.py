"""Run the PaperHub Qt desktop application."""

import argparse


def main():
    parser = argparse.ArgumentParser(description="PaperHub 本地科研资料索引；手动扫描，不移动原文件。")
    parser.add_argument("--library", help="预填的资料目录")
    parser.add_argument("--database", help="预填的 SQLite 索引文件")
    args = parser.parse_args()
    from paperhub.gui import launch_gui

    return launch_gui(args.library, args.database)


if __name__ == "__main__":
    raise SystemExit(main())
