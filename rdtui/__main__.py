"""Main entry point for Real-Debrid TUI."""

from rdtui.app import RDTUI


def main():
    """Run the Real-Debrid TUI application."""
    try:
        RDTUI().run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

