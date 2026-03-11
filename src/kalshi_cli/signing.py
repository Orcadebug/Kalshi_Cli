from __future__ import annotations

import base64
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


def signature_message(timestamp: str, method: str, path: str) -> bytes:
    return f"{timestamp}{method.upper()}{path}".encode("utf-8")


@dataclass(slots=True)
class OpenSSLSigner:
    private_key_path: str | None = None
    private_key_value: str | None = None

    def sign(self, timestamp: str, method: str, path: str) -> str:
        message = signature_message(timestamp, method, path)
        key_path = self._resolve_key_path()
        signature = self._openssl_sign(key_path, message)
        return base64.b64encode(signature).decode("ascii")

    def _resolve_key_path(self) -> str:
        if self.private_key_path:
            return self.private_key_path
        if not self.private_key_value:
            raise ValueError("Kalshi private key is not configured.")

        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", prefix="kalshi-key-", suffix=".pem", delete=False
        ) as handle:
            handle.write(self.private_key_value)
            temp_path = handle.name

        os.chmod(temp_path, 0o600)
        return temp_path

    def _openssl_sign(self, key_path: str, message: bytes) -> bytes:
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(message)
            message_path = handle.name

        cleanup_key = self.private_key_value is not None and self.private_key_path is None
        try:
            result = subprocess.run(
                [
                    "openssl",
                    "dgst",
                    "-sha256",
                    "-sign",
                    key_path,
                    "-sigopt",
                    "rsa_padding_mode:pss",
                    "-sigopt",
                    "rsa_pss_saltlen:digest",
                    "-sigopt",
                    "rsa_mgf1_md:sha256",
                    message_path,
                ],
                check=True,
                capture_output=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"openssl signing failed: {stderr}") from exc
        finally:
            Path(message_path).unlink(missing_ok=True)
            if cleanup_key:
                Path(key_path).unlink(missing_ok=True)
