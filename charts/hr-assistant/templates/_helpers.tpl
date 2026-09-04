{{/*
Expand the name of the chart.
*/}}
{{- define "hr-assistant.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "hr-assistant.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "hr-assistant.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "hr-assistant.labels" -}}
helm.sh/chart: {{ include "hr-assistant.chart" . }}
{{ include "hr-assistant.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "hr-assistant.selectorLabels" -}}
app.kubernetes.io/name: {{ include "hr-assistant.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "hr-assistant.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "hr-assistant.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the ollama endpoint URL based on release name
*/}}
{{- define "hr-assistant.ollamaEndpoint" -}}
http://{{ .Release.Name }}-ollama:11434
{{- end }}

{{/*
Whether this release provisions its own collector. Driven by observability.mode;
opentelemetry.operator.enabled is still honoured for callers that set it directly.
*/}}
{{- define "hr-assistant.collectorEnabled" -}}
{{- if or (eq .Values.observability.mode "operator") .Values.opentelemetry.operator.enabled -}}
true
{{- end -}}
{{- end }}

{{/*
Name of the OpenTelemetryCollector CR managed by the OpenTelemetry Operator.
*/}}
{{- define "hr-assistant.collectorName" -}}
{{- printf "%s-otel" (include "hr-assistant.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Cluster name stamped on the telemetry. Rancher injects global.cattle.clusterName
on catalog installs, so this is almost never set by hand.
*/}}
{{- define "hr-assistant.clusterName" -}}
{{- $global := .Values.global | default dict -}}
{{- $cattle := $global.cattle | default dict -}}
{{- .Values.opentelemetry.operator.clusterName | default $cattle.clusterName | default "unknown" }}
{{- end }}

{{/*
Name of the secret holding the SUSE Observability API key, resolving the three
supported sources in priority order.
*/}}
{{- define "hr-assistant.apiKeySecretName" -}}
{{- $so := .Values.opentelemetry.operator.suseObservability -}}
{{- if $so.existingSecret -}}
{{ $so.existingSecret }}
{{- else if $so.apiKey -}}
{{ include "hr-assistant.collectorName" . }}
{{- else -}}
{{ $so.copySecret.name }}
{{- end -}}
{{- end }}

{{/*
Namespace SUSE AI components are attributed to. Defaults to the release namespace
so each install shows up as its own SUSE AI namespace in the topology.
*/}}
{{- define "hr-assistant.suseAiNamespace" -}}
{{- default .Release.Namespace .Values.opentelemetry.operator.suseAiNamespace }}
{{- end }}

{{/*
Find the shared OpenTelemetry collector Service in the cluster at install time.

Helm's `lookup` runs against the live API server during install/upgrade (it
returns nothing during `helm template`), so this auto-discovers the collector
instead of asking the user to type it.

Candidate namespaces, in order: observability.collectorNamespace (if set),
"observability", "suse-observability". A Service is a candidate when ANY of:
  - its name contains "collector" and also "otel" or "opentelemetry"
  - app.kubernetes.io/component == "opentelemetry-collector"
  - app.kubernetes.io/name == "opentelemetry-collector"
and it exposes TCP port 4318 (the OTLP/HTTP ingestion port). The 4318 filter
matters: operator-managed collectors spawn -headless, -monitoring and
-extension twins in the same namespace, and unordered lookup results used to
let a twin win the "first match" race.

Among all candidates the deterministic winner is: (1) a name that ends in
"-collector" (the operator's base service) if exactly one does, otherwise
(2) the shortest name. Output is JSON {"found":true|false,"namespace":...,"service":...}
so callers can detect a miss instead of receiving a silent fallback.
*/}}
{{- define "hr-assistant.collectorService" -}}
{{- $explicit := .Values.observability.collectorNamespace | default "" -}}
{{- $candidates := list -}}
{{- if $explicit -}}
  {{- $candidates = append $candidates $explicit -}}
{{- end -}}
{{- $candidates = append $candidates "observability" -}}
{{- $candidates = append $candidates "suse-observability" -}}
{{- $seen := dict -}}
{{- $hits := list -}}
{{- range $ns := $candidates -}}
  {{- $lookup := lookup "v1" "Service" $ns "" -}}
  {{- if $lookup -}}
    {{- range $item := $lookup.items | default list -}}
      {{- $labels := $item.metadata.labels | default dict -}}
      {{- $comp := dig "app.kubernetes.io/component" "" $labels -}}
      {{- $nameLbl := dig "app.kubernetes.io/name" "" $labels -}}
      {{- $nameMatch := and (contains "collector" $item.metadata.name) (or (contains "otel" $item.metadata.name) (contains "opentelemetry" $item.metadata.name)) -}}
      {{- $matches := or $nameMatch (eq $comp "opentelemetry-collector") (eq $nameLbl "opentelemetry-collector") -}}
      {{- $has4318 := false -}}
      {{- range $item.spec.ports | default list -}}
        {{- if eq (toString .port) "4318" -}}
          {{- $has4318 = true -}}
        {{- end -}}
      {{- end -}}
      {{- if and $matches $has4318 -}}
        {{- $key := printf "%s/%s" $ns $item.metadata.name -}}
        {{- if not (hasKey $seen $key) -}}
          {{- $seen = set $seen $key true -}}
          {{- $hits = append $hits (dict "namespace" $ns "service" $item.metadata.name) -}}
        {{- end -}}
      {{- end -}}
    {{- end -}}
  {{- end -}}
{{- end -}}
{{- $best := dict "found" false "namespace" "" "service" "" -}}
{{- if $hits -}}
  {{- $base := list -}}
  {{- range $h := $hits -}}
    {{- if hasSuffix "-collector" (get $h "service") -}}
      {{- $base = append $base $h -}}
    {{- end -}}
  {{- end -}}
  {{- if eq (len $base) 1 -}}
    {{- $h := first $base -}}
    {{- $best = merge $best (dict "found" true "namespace" (get $h "namespace") "service" (get $h "service")) -}}
  {{- else -}}
    {{- $shortest := list -}}
    {{- range $h := $hits -}}
      {{- if or (not $shortest) (lt (len (get $h "service")) (len (get (first $shortest) "service"))) -}}
        {{- $shortest = list $h -}}
      {{- end -}}
    {{- end -}}
    {{- $h := first $shortest -}}
    {{- $best = merge $best (dict "found" true "namespace" (get $h "namespace") "service" (get $h "service")) -}}
  {{- end -}}
{{- end -}}
{{- $best | toJson -}}
{{- end }}

{{/*
The namespace of the auto-discovered collector (or the explicitly configured
one). Resolved by the same lookup as hr-assistant.collectorService, so the two
can never disagree. Returns the candidate namespace only when no service was
found - callers use it to build the stable-convention endpoint in that case.
*/}}
{{- define "hr-assistant.collectorNamespace" -}}
{{- $discovery := (include "hr-assistant.collectorService" .) | fromJson -}}
{{- if (get $discovery "found") -}}
  {{- get $discovery "namespace" -}}
{{- else -}}
  {{- .Values.observability.collectorNamespace | default "observability" -}}
{{- end -}}
{{- end }}

{{/*
OTLP endpoint the applications export to. When the OpenTelemetry Operator option
is enabled the apps talk to the collector this chart provisions in its own
namespace; otherwise the endpoint resolves as follows:

1. .Values.otlpEndpoint if explicitly set (used verbatim; the pre-install hook
   validates connectivity and fails the install with the discovered URL if
   wrong).
2. Auto-discovered collector Service (Helm lookup at install/upgrade time) in
   observability.collectorNamespace or one of the well-known namespaces - the
   "right collector" without typing anything.
3. If discovery finds nothing: the stable SUSE convention FQDN
   http://opentelemetry-collector.<namespace>.svc.cluster.local:4318 in the
   configured Collector Namespace. This used to be a hardcoded dev-ai FQDN that
   silently black-holed telemetry on any cluster whose collector had a
   different name. The pre-install connectivity hook still gates the install,
   so a wrong convention endpoint fails loudly instead of silently.
*/}}
{{- define "hr-assistant.otlpEndpoint" -}}
{{- if include "hr-assistant.collectorEnabled" . -}}
http://{{ include "hr-assistant.collectorName" . }}-collector.{{ .Release.Namespace }}.svc.cluster.local:4318
{{- else -}}
{{- $endpoint := .Values.otlpEndpoint -}}
{{- $discovery := (include "hr-assistant.collectorService" .) | fromJson -}}
{{- if not $endpoint -}}
  {{- if (get $discovery "found") -}}
    {{- $endpoint = printf "http://%s.%s.svc.cluster.local:4318" (get $discovery "service") (get $discovery "namespace") -}}
  {{- else -}}
    {{- $endpoint = printf "http://opentelemetry-collector.%s.svc.cluster.local:4318" (include "hr-assistant.collectorNamespace" .) -}}
  {{- end -}}
{{- end -}}
{{- $endpoint -}}
{{- end -}}
{{- end }}

{{/*
The auto-discovered collector endpoint, used by the connectivity-check hook to
suggest the correct URL when the user-supplied one is unreachable. Empty when
nothing was discovered (in which case the hook falls back to its generic
"look in observability.collectorNamespace" guidance).
*/}}
{{- define "hr-assistant.discoveredCollectorEndpoint" -}}
{{- $discovery := (include "hr-assistant.collectorService" .) | fromJson -}}
{{- if (get $discovery "found") -}}
http://{{ get $discovery "service" }}.{{ get $discovery "namespace" }}.svc.cluster.local:4318
{{- end -}}
{{- end }}

{{/*
The primary model. Falls back to the first model the bundled Ollama pulls.
*/}}
{{- define "hr-assistant.model" -}}
{{- if .Values.model -}}
{{ .Values.model }}
{{- else if and .Values.ollama.models .Values.ollama.models.pull -}}
{{ get .Values.ollama.models.pull "main" | default (first (values .Values.ollama.models.pull)) }}
{{- else -}}
llama3.2:1b
{{- end -}}
{{- end }}

{{/*
OTEL_RESOURCE_ATTRIBUTES for the app containers.

SUSE Observability builds the SUSE AI topology from resource attributes: the
collector's transform/infer-providers, transform/infer-models and the trace
relation pipelines all read gen_ai.provider.name (and gen_ai.request.model) off
the *resource*. OpenLIT only ever sets gen_ai.system as a span/datapoint
attribute, so without these the app never renders as an LLM component and no
model or inference-engine relations are drawn.
*/}}
{{- define "hr-assistant.otelResourceAttributes" -}}
{{- $ctx := .ctx | default . -}}
{{- $component := .componentName | default "hr-assistant" -}}
{{- $attrs := list (printf "deployment.environment=%s" $ctx.Values.deploymentEnvironment) -}}
{{- $attrs = append $attrs (printf "gen_ai.provider.name=%s" $ctx.Values.genai.providerName) -}}
{{- $attrs = append $attrs (printf "gen_ai.request.model=%s" (include "hr-assistant.model" $ctx)) -}}
{{- $attrs = append $attrs (printf "service.namespace=%s" (include "hr-assistant.serviceNamespace" $ctx)) -}}
{{- $attrs = append $attrs "suse.ai.component.type=agent" -}}
{{- $attrs = append $attrs (printf "suse.ai.component.name=%s" $component) -}}
{{- $attrs = append $attrs "suse.ai.managed=true" -}}
{{- join "," $attrs }}
{{- end }}

{{/*
The namespace this release's SUSE AI components are grouped under.

SUSE's collector pipeline reads service.namespace off the resource first and only
falls back to its own SUSE_AI_NAMESPACE when the application did not declare one
(see integrations/otel-collector/otel-values.yaml in SUSE/suse-ai-observability-extension).
Declaring it here is what lets a single shared collector serve many namespaces and
still group each application under its own.
*/}}
{{- define "hr-assistant.serviceNamespace" -}}
{{- default .Release.Namespace .Values.observability.serviceNamespace }}
{{- end }}
