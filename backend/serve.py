from __future__ import annotations

from uvicorn import run

from .app import app


def main() -> None:
    run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()


