from __future__ import annotations


class TLSDetector:
    """Placeholder for a future Transit Least Squares implementation."""

    enabled = False

    def run(self, *_args, **_kwargs) -> dict:
        return {
            "enabled": False,
            "notes": "Transit Least Squares is reserved for a future validation pass; BLS is used for the first release.",
        }
