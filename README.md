# Hearth wallet

Hearth customers spend marketplace credit from a wallet. The lab has the wallet API, Postgres, and a fake payment service provider (PSP) whose latency and failures you control.

## Run

You need Docker with Compose. Run `make up`, then `make test`. The API is on `http://localhost:58004`, and the PSP's control API on `http://localhost:58003`.

`make load` resets Cora-17's wallet, sends two concurrent purchases for it, and prints the response statuses along with the wallet and lock metrics. `make psp-slow` sets the fake PSP's latency to 500ms. `make evidence` (`/evidence`) returns the request events the service logged, and `make metrics` (`/metrics`) reports negative balances, the purchase count, p99 lock wait and PSP latency.

`make down` removes the local database volume.

## License

MIT. See `LICENSE`.
