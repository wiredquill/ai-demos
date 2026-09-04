{{/*
Expand the name of the chart.
*/}}
{{- define "ai-compare-opentelemetry.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "ai-compare-opentelemetry.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- if eq .Release.Name "ai-compare" -}}
{{- printf "ai-compare" | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "ai-compare-opentelemetry.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "ai-compare-opentelemetry.labels" -}}
helm.sh/chart: {{ include "ai-compare-opentelemetry.chart" . }}
{{ include "ai-compare-opentelemetry.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
observability.opentelemetry.io/enabled: "true"
{{- end -}}

{{/*
Selector labels
*/}}
{{- define "ai-compare-opentelemetry.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ai-compare-opentelemetry.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Find the shared OpenTelemetry collector Service in the cluster at install time.

Helm's `lookup` runs against the live API server during install/upgrade (it
returns nothing during `helm template`), so an empty otlpEndpoint value
auto-discovers the collector instead of shipping a cluster-specific default
FQDN that silently black-holes telemetry on any other cluster.

Candidate namespaces, in order: "observability", "suse-observability".
A Service is a candidate when ANY of:
  - its name contains "collector" and also "otel" or "opentelemetry"
  - app.kubernetes.io/component == "opentelemetry-collector"
  - app.kubernetes.io/name == "opentelemetry-collector"
and it exposes TCP port 4318 (the OTLP/HTTP ingestion port). The 4318 filter
matters: operator-managed collectors spawn -headless, -monitoring and
-extension twins in the same namespace, and unordered lookup results used to
let a twin win the "first match" race.

Among all candidates the deterministic winner is: (1) a name that ends in
"-collector" (the operator's base service) if exactly one does, otherwise
(2) the shortest name. Output is JSON {"found":true|false,"namespace":...,
"service":...} so callers can detect a miss instead of receiving a silent
fallback.
*/}}
{{- define "ai-compare-opentelemetry.collectorService" -}}
{{- $candidates := list "observability" "suse-observability" -}}
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
Compute the OTLP HTTP endpoint (4318) for app telemetry.
Apps point at the shared cluster collector, which groups telemetry by
service.namespace (set to the release namespace by each app).

Resolution: the configured value if non-empty; otherwise the auto-discovered
collector Service; otherwise the stable convention
http://opentelemetry-collector.observability.svc.cluster.local:4318 (a wrong
name then fails loudly at probe/telemetry time instead of matching one
cluster's collector forever).
*/}}
{{- define "ai-compare-opentelemetry.otlpHttpEndpoint" -}}
{{- $endpoint := .Values.aiCompare.observability.otlpEndpoint -}}
{{- if not $endpoint -}}
  {{- $discovery := (include "ai-compare-opentelemetry.collectorService" .) | fromJson -}}
  {{- if (get $discovery "found") -}}
    {{- $endpoint = printf "http://%s.%s.svc.cluster.local:4318" (get $discovery "service") (get $discovery "namespace") -}}
  {{- else -}}
    {{- $endpoint = "http://opentelemetry-collector.observability.svc.cluster.local:4318" -}}
  {{- end -}}
{{- end -}}
{{- $endpoint -}}
{{- end -}}

{{/*
Compute the OTLP gRPC endpoint (4317) for Open WebUI telemetry.
Same discovery rules as the HTTP endpoint, on port 4317.
*/}}
{{- define "ai-compare-opentelemetry.otlpGrpcEndpoint" -}}
{{- $endpoint := .Values.openWebui.observability.otlpEndpoint -}}
{{- if not $endpoint -}}
  {{- $discovery := (include "ai-compare-opentelemetry.collectorService" .) | fromJson -}}
  {{- if (get $discovery "found") -}}
    {{- $endpoint = printf "http://%s.%s.svc.cluster.local:4317" (get $discovery "service") (get $discovery "namespace") -}}
  {{- else -}}
    {{- $endpoint = "http://opentelemetry-collector.observability.svc.cluster.local:4317" -}}
  {{- end -}}
{{- end -}}
{{- $endpoint -}}
{{- end -}}
