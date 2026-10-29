# SUSE AI Declared Topology

Lets applications declare their SUSE AI topology (components and the relations
between them) up front, instead of relying on the SUSE AI collector to infer it
from live traffic. Declared components use the SUSE AI collector's identifiers
(`urn:suse-ai:product:<type>:<name>`), so they merge with the components the
SUSE AI StackPack syncs and keep its names, types, metrics and monitors.
