"""Main entry point for trae_study."""


def greet(name: str = "World") -> str:
    """Return a greeting string.

    Args:
        name: The name to greet. Defaults to "World".

    Returns:
        A greeting message.
    """
    return f"Hello, {name}!"


def main() -> None:
    """Run the main program."""
    print(greet("Trae Study"))


if __name__ == "__main__":
    main()
