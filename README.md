# Hearth wallet

Hearth lets customers spend the credit in a marketplace wallet. The local lab has a wallet API, Postgres, and a fake payment service provider with controllable latency and failure.

## Run

You need Docker with Compose. Run `make up`, then `make test`. The API is at `http://localhost:58004`; the PSP control API is at `http://localhost:58003`.

`make load` sends two concurrent purchases for Cora-17 and prints wallet and lock metrics. `make psp-slow` changes the fake PSP latency to 500ms. `/evidence` returns the request events the service logs, and `/metrics` reports negative balances, purchase count, p99 lock wait, and PSP latency.

`make down` removes the local database volume.

## License

MIT. See `LICENSE`.

