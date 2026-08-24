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
instead of asking the user to type it. Matches a Service whose name contains
"opentelemetry-collector" or that carries the app.kubernetes.io/name label.
*/}}
{{- define "hr-assistant.collectorService" -}}
{{- $ns := .Values.observability.collectorNamespace | default "observability" -}}
{{- $svc := "" -}}
{{- $found := lookup "v1" "Service" $ns "" -}}
{{- range $item := ($found.items | default list) -}}
  {{- $lbl := dig "app.kubernetes.io/name" "" ($item.metadata.labels | default dict) -}}
  {{- if or (contains "opentelemetry-collector" $item.metadata.name) (eq $lbl "opentelemetry-collector") -}}
    {{- $svc = $item.metadata.name -}}
  {{- end -}}
{{- end -}}
{{- $svc -}}
{{- end }}

{{/*
OTLP endpoint the applications export to. When the OpenTelemetry Operator option is
enabled the apps talk to the collector this chart provisions in its own namespace;
otherwise the endpoint resolves as follows:

1. .Values.otlpEndpoint if explicitly set (used verbatim; the pre-install hook
   validates connectivity and fails the install with the proper URL if wrong).
2. Auto-discovered collector Service in observability.collectorNamespace
   (Helm lookup at install time) - the "right collector" without typing anything.
3. The conventional shared-collector FQDN as a last resort.
*/}}
{{- define "hr-assistant.otlpEndpoint" -}}
{{- if include "hr-assistant.collectorEnabled" . -}}
http://{{ include "hr-assistant.collectorName" . }}-collector.{{ .Release.Namespace }}.svc.cluster.local:4318
{{- else -}}
{{- $endpoint := .Values.otlpEndpoint -}}
{{- if not $endpoint -}}
  {{- $svc := include "hr-assistant.collectorService" . -}}
  {{- if $svc -}}
    {{- $endpoint = printf "http://%s.%s.svc.cluster.local:4318" $svc (.Values.observability.collectorNamespace | default "observability") -}}
  {{- else -}}
    {{- $endpoint = "http://open-telemetry-collector-opentelemetry-collector.observability.svc.cluster.local:4318" -}}
  {{- end -}}
{{- end -}}
{{- $endpoint -}}
{{- end -}}
{{- end }}

{{/*
The auto-discovered collector endpoint, used by the connectivity-check hook to
suggest the correct URL when the user-supplied one is unreachable.
*/}}
{{- define "hr-assistant.discoveredCollectorEndpoint" -}}
{{- $svc := include "hr-assistant.collectorService" . -}}
{{- if $svc -}}
http://{{ $svc }}.{{ .Values.observability.collectorNamespace | default "observability" }}.svc.cluster.local:4318
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
