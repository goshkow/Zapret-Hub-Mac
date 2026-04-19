from __future__ import annotations

import argparse
import sys

from zapret_hub_mac.vendor.tg_ws_proxy import tg_ws_proxy


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1443)
    parser.add_argument("--secret", default="")
    args = parser.parse_args()

    argv = ["tg-ws-proxy", "--host", args.host, "--port", str(args.port)]
    if args.secret:
        argv.extend(["--secret", args.secret])
    previous = sys.argv
    try:
        sys.argv = argv
        return int(tg_ws_proxy.main() or 0)
    finally:
        sys.argv = previous


if __name__ == "__main__":
    raise SystemExit(main())
