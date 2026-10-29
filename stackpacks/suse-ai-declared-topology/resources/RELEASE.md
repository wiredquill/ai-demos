## 1.0.0

- StackPack 2.0 (SUSE Observability 2.12+): declared topology arrives as
  OpenTelemetry metrics and is mapped by an OtelComponentMapping and an
  OtelRelationMapping. Replaces 0.1.0's Receiver API DataSource and Sync on the
  `suse-ai`/`declared` stream, so senders no longer need an API key.

## 0.1.0

- Initial release: DataSource and Sync for the `suse-ai`/`declared` topology stream.
