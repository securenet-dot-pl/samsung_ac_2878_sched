#!/usr/bin/env python3
"""Pobierz token lokalnego API Samsung AC (port 2878 / DPLUG).

Wymaga:  pip install pysamsung-dplug
Użycie:  python3 get_token.py <IP_KLIMATYZATORA>
Po uruchomieniu WŁĄCZ zasilanie klimatyzatora w ciągu ~40 s — token wypisze się na ekran.
"""
import asyncio
import sys

from samsung_dplug import SamsungAcClient, build_ssl_context, default_cert_path


async def main() -> None:
    if len(sys.argv) < 2:
        print("Użycie: python3 get_token.py <IP_KLIMATYZATORA> [sciezka_do_cert.pem]")
        raise SystemExit(1)
    host = sys.argv[1]
    cert = sys.argv[2] if len(sys.argv) > 2 else default_cert_path()
    ctx = build_ssl_context(cert)
    client = SamsungAcClient(host=host, ssl_context=ctx)
    print(f"[*] Łączę z {host}:2878 ... WŁĄCZ teraz zasilanie klimatyzatora (okno ~40 s).")
    try:
        token = await client.async_get_token(power_on_timeout=40.0)
        print(f"\n>>> TOKEN: {token}\n")
        print("Wstaw go do configuration.yaml jako 'token:'.")
    except Exception as e:
        print(f"[!] Nie udało się: {e}")
        print("    Wskazówki: urządzenie musi być w zasięgu :2878; włącz zasilanie w oknie czasowym;")
        print("    stary moduł wymaga starego TLS — build_ssl_context() to obsługuje.")
        raise SystemExit(2)


if __name__ == "__main__":
    asyncio.run(main())
